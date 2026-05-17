# =============================================================================
# ULTRA MODERN AI ASSISTANT GUI
# Auto Listening + Animated Circular Voice Assistant
# =============================================================================

import os
import sys
import random
import math
import queue
import threading
import logging
import tkinter as tk
from datetime import datetime

try:
    import customtkinter as ctk
except:
    print("Install customtkinter:")
    print("pip install customtkinter")
    sys.exit()

# =============================================================================
# PROJECT IMPORTS
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from assistant import VoiceAssistant
from utils.speech import SpeechRecognizer
from utils.tts import TextToSpeech

# =============================================================================
# THEME
# =============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#09090d"
CARD = "#141824"
CARD2 = "#1c2333"

COLORS = [
    "#ff006e",
    "#8338ec",
    "#3a86ff",
    "#00f5d4",
    "#ffbe0b",
    "#fb5607",
    "#00ff99",
    "#f72585",
]

logger = logging.getLogger(__name__)

# =============================================================================
# MAIN GUI
# =============================================================================
class VoiceAssistantGUI:

    def __init__(self):

        # ============================================================
        # WINDOW
        # ============================================================
        self.root = ctk.CTk()

        self.root.title("AIRA AI")
        self.root.geometry("1040x620")
        self.root.configure(fg_color=BG)
        self.root.minsize(960, 560)

        # ============================================================
        # ASSISTANT
        # ============================================================
        self.assistant = VoiceAssistant()

        self.recognizer = SpeechRecognizer(
            timeout=8,
            phrase_time_limit=15
        )

        self.tts = TextToSpeech(
            rate=175,
            volume=1.0,
            voice_gender='female'
        )

        # ============================================================
        # STATES
        # ============================================================
        self.is_listening = False
        self.is_speaking = False

        self.message_queue = queue.Queue()

        self.orb_phase = 0
        self.ring_phase = 0

        # ============================================================
        # BUILD UI
        # ============================================================
        self.build_ui()

        # ============================================================
        # ANIMATIONS
        # ============================================================
        self.animate_orb()
        self.animate_rings()
        self.animate_wave()
        self.animate_header()

        # ============================================================
        # QUEUE
        # ============================================================
        self.process_queue()

        # ============================================================
        # GREETING
        # ============================================================
        greeting = self.assistant.get_greeting()

        self.add_message(
            "AIRA",
            greeting,
            False
        )

        self.root.after(
            1000,
            lambda: self.speak_response(greeting)
        )

        # ============================================================
        # AUTO START LISTENING
        # ============================================================
        self.root.after(
            2500,
            self.start_listening
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.exit_app
        )

    # =============================================================================
    # BUILD UI
    # =============================================================================
    def build_ui(self):

        # ============================================================
        # HEADER
        # ============================================================
        self.header = ctk.CTkFrame(
            self.root,
            height=65,
            fg_color="#6a00f4",
            corner_radius=0,
            border_width=2,
            border_color="#00f5ff"
        )

        self.header.pack(fill="x")

        self.title = ctk.CTkLabel(
            self.header,
            text="AIRA • ARTIFICAL INTELLIGENT RESPONSE AGENT",
            font=("Segoe UI", 24, "bold"),
            text_color="white"
        )

        self.title.pack(pady=15)

        # ============================================================
        # MAIN AREA
        # ============================================================
        self.main = ctk.CTkFrame(
            self.root,
            fg_color="transparent"
        )

        self.main.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # ============================================================
        # LEFT PANEL
        # ============================================================
        self.left = ctk.CTkFrame(
            self.main,
            width=320,
            fg_color=CARD,
            corner_radius=25,
            border_width=2,
            border_color="#00d4ff"
        )

        self.left.pack(
            side="left",
            fill="y",
            padx=(0, 10)
        )

        # ============================================================
        # STATUS
        # ============================================================
        self.status = ctk.CTkLabel(
            self.left,
            text="INITIALIZING...",
            font=("Segoe UI", 16, "bold"),
            text_color="#00ff99"
        )

        self.status.pack(pady=(15, 5))

        # ============================================================
        # VOICE ORB
        # ============================================================
        self.canvas = tk.Canvas(
            self.left,
            width=240,
            height=240,
            bg=CARD,
            highlightthickness=0
        )

        self.canvas.pack(pady=5)

        # RINGS
        self.ring1 = self.canvas.create_oval(
            35, 35, 205, 205,
            outline="#00f5ff",
            width=2
        )

        self.ring2 = self.canvas.create_oval(
            50, 50, 190, 190,
            outline="#ff00ff",
            width=2
        )

        self.ring3 = self.canvas.create_oval(
            65, 65, 175, 175,
            outline="#00ff99",
            width=2
        )

        # MAIN ORB
        self.orb = self.canvas.create_oval(
            80, 80, 160, 160,
            fill="#00d4ff",
            outline=""
        )

        # GLOW
        self.glow = self.canvas.create_oval(
            100, 100, 140, 140,
            fill="#ffffff",
            outline=""
        )

        # ============================================================
        # AUDIO WAVES
        # ============================================================
        self.wave_canvas = tk.Canvas(
            self.left,
            width=240,
            height=80,
            bg=CARD,
            highlightthickness=0
        )

        self.wave_canvas.pack()

        self.wave_bars = []

        for i in range(26):

            x = 10 + i * 8

            bar = self.wave_canvas.create_rectangle(
                x,
                40,
                x + 5,
                40,
                fill=random.choice(COLORS),
                outline=""
            )

            self.wave_bars.append(bar)

        # ============================================================
        # BUTTONS
        # ============================================================
        self.listen_btn = ctk.CTkButton(
            self.left,
            text="START LISTENING",
            height=48,
            corner_radius=18,
            fg_color="#00c853",
            hover_color="#00e676",
            border_width=2,
            border_color="#ffffff",
            font=("Segoe UI", 14, "bold"),
            command=self.start_listening
        )

        self.listen_btn.pack(
            fill="x",
            padx=18,
            pady=(15, 8)
        )

        self.stop_btn = ctk.CTkButton(
            self.left,
            text="STOP",
            height=48,
            corner_radius=18,
            fg_color="#ff1744",
            hover_color="#ff4569",
            border_width=2,
            border_color="#ffffff",
            font=("Segoe UI", 14, "bold"),
            state="disabled",
            command=self.stop_listening
        )

        self.stop_btn.pack(
            fill="x",
            padx=18
        )

        # ============================================================
        # LAST INPUT
        # ============================================================
        label = ctk.CTkLabel(
            self.left,
            text="LAST INPUT",
            font=("Segoe UI", 13, "bold"),
            text_color="#00f5ff"
        )

        label.pack(
            anchor="w",
            padx=18,
            pady=(15, 4)
        )

        self.input_box = ctk.CTkTextbox(
            self.left,
            height=65,
            fg_color=CARD2,
            corner_radius=15,
            border_width=2,
            border_color="#8338ec",
            font=("Segoe UI", 12)
        )

        self.input_box.pack(
            fill="x",
            padx=18
        )

        # ============================================================
        # INTENT PANEL
        # ============================================================
        self.intent_frame = ctk.CTkFrame(
            self.left,
            fg_color=CARD2,
            corner_radius=15,
            border_width=2,
            border_color="#ff006e"
        )

        self.intent_frame.pack(
            fill="x",
            padx=18,
            pady=12
        )

        self.intent_label = ctk.CTkLabel(
            self.intent_frame,
            text="Intent: ---",
            font=("Segoe UI", 13, "bold"),
            text_color="#00d4ff"
        )

        self.intent_label.pack(pady=(10, 4))

        self.confidence_label = ctk.CTkLabel(
            self.intent_frame,
            text="Confidence: 0%",
            font=("Segoe UI", 12),
            text_color="#00ff99"
        )

        self.confidence_label.pack()

        self.progress = ctk.CTkProgressBar(
            self.intent_frame,
            progress_color="#00d4ff",
            height=12,
            corner_radius=20
        )

        self.progress.pack(
            fill="x",
            padx=15,
            pady=10
        )

        self.progress.set(0)

        # ============================================================
        # ENTRY
        # ============================================================
        self.entry = ctk.CTkEntry(
            self.left,
            height=45,
            corner_radius=18,
            placeholder_text="Type command...",
            font=("Segoe UI", 13),
            border_width=2,
            border_color="#00f5ff"
        )

        self.entry.pack(
            fill="x",
            padx=18
        )

        self.entry.bind(
            "<Return>",
            lambda e: self.send_text()
        )

        self.send_btn = ctk.CTkButton(
            self.left,
            text="SEND",
            height=45,
            corner_radius=18,
            fg_color="#8338ec",
            hover_color="#9d4edd",
            border_width=2,
            border_color="#ffffff",
            font=("Segoe UI", 14, "bold"),
            command=self.send_text
        )

        self.send_btn.pack(
            fill="x",
            padx=18,
            pady=12
        )

        # ============================================================
        # RIGHT PANEL
        # ============================================================
        self.right = ctk.CTkFrame(
            self.main,
            fg_color=CARD,
            corner_radius=25,
            border_width=2,
            border_color="#8338ec"
        )

        self.right.pack(
            side="right",
            fill="both",
            expand=True
        )

        chat_label = ctk.CTkLabel(
            self.right,
            text="CONVERSATION",
            font=("Segoe UI", 20, "bold"),
            text_color="#00f5ff"
        )

        chat_label.pack(
            anchor="w",
            padx=18,
            pady=15
        )

        self.chat = ctk.CTkScrollableFrame(
            self.right,
            fg_color="#0e1320",
            corner_radius=18,
            border_width=2,
            border_color="#2f3f61"
        )

        self.chat.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

    # =============================================================================
    # ORB ANIMATION
    # =============================================================================
    def animate_orb(self):

        self.orb_phase += 0.15

        if self.is_listening or self.is_speaking:

            scale = math.sin(self.orb_phase) * 12

            self.canvas.coords(
                self.orb,
                80 - scale,
                80 - scale,
                160 + scale,
                160 + scale
            )

            glow_size = abs(math.sin(self.orb_phase)) * 8

            self.canvas.coords(
                self.glow,
                100 - glow_size,
                100 - glow_size,
                140 + glow_size,
                140 + glow_size
            )

            self.canvas.itemconfig(
                self.orb,
                fill=random.choice(COLORS)
            )

        else:

            self.canvas.coords(
                self.orb,
                80, 80, 160, 160
            )

        self.root.after(
            40,
            self.animate_orb
        )

    # =============================================================================
    # RING ANIMATION
    # =============================================================================
    def animate_rings(self):

        self.ring_phase += 0.08

        if self.is_listening or self.is_speaking:

            offset = math.sin(self.ring_phase) * 8

            self.canvas.coords(
                self.ring1,
                35 - offset,
                35 - offset,
                205 + offset,
                205 + offset
            )

            self.canvas.coords(
                self.ring2,
                50 - offset/2,
                50 - offset/2,
                190 + offset/2,
                190 + offset/2
            )

            self.canvas.itemconfig(
                self.ring1,
                outline=random.choice(COLORS)
            )

            self.canvas.itemconfig(
                self.ring2,
                outline=random.choice(COLORS)
            )

        self.root.after(
            50,
            self.animate_rings
        )

    # =============================================================================
    # WAVE ANIMATION
    # =============================================================================
    def animate_wave(self):

        for i, bar in enumerate(self.wave_bars):

            if self.is_listening or self.is_speaking:
                height = random.randint(20, 75)
            else:
                height = random.randint(5, 15)

            self.wave_canvas.coords(
                bar,
                10 + i * 8,
                80 - height,
                15 + i * 8,
                80
            )

        self.root.after(
            65,
            self.animate_wave
        )

    # =============================================================================
    # HEADER ANIMATION
    # =============================================================================
    def animate_header(self):

        self.header.configure(
            fg_color=random.choice(COLORS)
        )

        self.root.after(
            2500,
            self.animate_header
        )

    # =============================================================================
    # LISTENING
    # =============================================================================
    def start_listening(self):

        if self.is_listening:
            return

        self.is_listening = True

        self.listen_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.status.configure(
            text="LISTENING...",
            text_color="#00ff99"
        )

        threading.Thread(
            target=self.listen_worker,
            daemon=True
        ).start()

    def stop_listening(self):

        self.is_listening = False

        self.status.configure(
            text="STOPPED",
            text_color="#ff1744"
        )

        self.listen_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def listen_worker(self):

        while self.is_listening:

            try:

                text = self.recognizer.listen()

                if text and text.strip():

                    self.message_queue.put(
                        ("text", text)
                    )

            except:
                continue

    # =============================================================================
    # SPEAKING
    # =============================================================================
    def speak_response(self, response):

        self.is_speaking = True

        self.status.configure(
            text="SPEAKING...",
            text_color="#ffbe0b"
        )

        threading.Thread(
            target=self.tts_worker,
            args=(response,),
            daemon=True
        ).start()

    def tts_worker(self, response):

        self.tts.speak(response)

        self.is_speaking = False

        if self.is_listening:

            self.status.configure(
                text="LISTENING...",
                text_color="#00ff99"
            )

    # =============================================================================
    # TEXT
    # =============================================================================
    def send_text(self):

        text = self.entry.get().strip()

        if not text:
            return

        self.entry.delete(0, "end")

        self.handle_input(text)

    def handle_input(self, text):

        self.input_box.delete("1.0", "end")
        self.input_box.insert("1.0", text)

        self.add_message(
            "YOU",
            text,
            True
        )

        self.status.configure(
            text="THINKING...",
            text_color="#00d4ff"
        )

        response, intent, confidence = self.assistant.process(text)

        self.intent_label.configure(
            text=f"Intent: {intent.replace('_', ' ').title()}"
        )

        self.confidence_label.configure(
            text=f"Confidence: {confidence * 100:.1f}%"
        )

        self.progress.set(confidence)

        self.add_message(
            "AIRA",
            response,
            False
        )

        self.speak_response(response)

    # =============================================================================
    # CHAT
    # =============================================================================
    def add_message(self, sender, text, user=False):

        outer = ctk.CTkFrame(
            self.chat,
            fg_color="transparent"
        )

        outer.pack(
            fill="x",
            pady=8,
            padx=8
        )

        bubble_color = (
            random.choice(COLORS)
            if user else "#232b3d"
        )

        bubble = ctk.CTkFrame(
            outer,
            fg_color=bubble_color,
            corner_radius=18,
            border_width=2,
            border_color="#ffffff"
        )

        bubble.pack(
            side="right" if user else "left",
            padx=8
        )

        current_time = datetime.now().strftime("%H:%M")

        label = ctk.CTkLabel(
            bubble,
            text=f"{sender}\n\n{text}\n\n{current_time}",
            justify="left",
            wraplength=420,
            font=("Segoe UI", 13),
            padx=15,
            pady=12
        )

        label.pack()

    # =============================================================================
    # QUEUE
    # =============================================================================
    def process_queue(self):

        try:

            while True:

                msg = self.message_queue.get_nowait()

                if msg[0] == "text":

                    self.handle_input(msg[1])

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.process_queue
        )

    # =============================================================================
    # EXIT
    # =============================================================================
    def exit_app(self):

        self.is_listening = False

        try:
            self.tts.stop()
        except:
            pass

        self.root.destroy()

    # =============================================================================
    # RUN
    # =============================================================================
    def run(self):

        self.root.mainloop()

# =============================================================================
# MAIN
# =============================================================================
def main():

    logging.basicConfig(level=logging.INFO)

    app = VoiceAssistantGUI()

    app.run()

if __name__ == "__main__":
    main()
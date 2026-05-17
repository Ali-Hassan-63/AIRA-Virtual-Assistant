# =============================================================================
# utils/tts.py — Text-to-Speech (Windows-safe, GUI-friendly)
#
# Each utterance runs on its own short-lived thread with its own pyttsx3
# engine (COM initialized on that thread). Falls back to Windows SAPI via
# PowerShell if pyttsx3 fails. Overlapping speech is serialized with a lock.
# =============================================================================

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
import threading

logger = logging.getLogger(__name__)

_speak_lock = threading.Lock()


def _speak_powershell_sapi(text: str) -> None:
    """Last-resort TTS on Windows using System.Speech (reads text from a temp file)."""
    text = (text or "").strip()
    if not text:
        return
    path = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(text[:8000])
            path = f.name.replace("\\", "\\\\")
        ps = (
            f'$p = "{path}"; '
            r"$t = Get-Content -Raw -LiteralPath $p -Encoding UTF8; "
            r"Add-Type -AssemblyName System.Speech; "
            r"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            r"$s.Speak($t); "
            r"Remove-Item -LiteralPath $p -ErrorAction SilentlyContinue"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as e:
        logger.error("PowerShell TTS failed: %s", e)


def _speak_pyttsx3_on_thread(text: str, rate: int, volume: float, voice_gender: str) -> bool:
    """Return True if pyttsx3 spoke successfully."""
    try:
        import pyttsx3
    except ImportError:
        return False

    if sys.platform == "win32":
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except ImportError:
            pass
    ok = False
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        voices = engine.getProperty("voices") or []
        g = voice_gender.lower()
        for v in voices:
            nid = v.id.lower()
            nn = v.name.lower()
            if g == "female" and (
                "female" in nid
                or "zira" in nn
                or "hazel" in nn
                or "victoria" in nn
            ):
                engine.setProperty("voice", v.id)
                break
            if g == "male" and (
                "male" in nid or "david" in nn or "mark" in nn
            ):
                engine.setProperty("voice", v.id)
                break
        else:
            if voices:
                engine.setProperty("voice", voices[0].id)
        engine.say(text)
        engine.runAndWait()
        ok = True
    except Exception as e:
        logger.warning("pyttsx3 TTS failed: %s", e)
    finally:
        if sys.platform == "win32":
            try:
                import pythoncom

                pythoncom.CoUninitialize()
            except ImportError:
                pass
    return ok


def _utterance_worker(text: str, rate: int, volume: float, voice_gender: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    text = text[:8000]
    with _speak_lock:
        if not _speak_pyttsx3_on_thread(text, rate, volume, voice_gender):
            if sys.platform == "win32":
                _speak_powershell_sapi(text)
            else:
                logger.error("[TTS unavailable] Would say: %s", text[:200])


class TextToSpeech:
    def __init__(
        self,
        rate: int = 175,
        volume: float = 1.0,
        voice_gender: str = "female",
    ):
        self.rate = rate
        self.volume = float(volume)
        self.voice_gender = voice_gender.lower()
        self._speaking = False
        self._last_thread: threading.Thread | None = None

    def speak(self, text: str, blocking: bool = False) -> None:
        if not text or not str(text).strip():
            return
        t = threading.Thread(
            target=self._run,
            args=(str(text).strip(),),
            name="tts-utterance",
            daemon=True,
        )
        self._last_thread = t
        t.start()
        if blocking:
            t.join(timeout=180)

    def _run(self, text: str) -> None:
        self._speaking = True
        try:
            _utterance_worker(text, self.rate, self.volume, self.voice_gender)
        finally:
            self._speaking = False

    def stop(self) -> None:
        """Best-effort: cannot always cancel mid-utterance without native hooks."""
        self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def list_voices(self) -> list[str]:
        try:
            import pyttsx3

            eng = pyttsx3.init()
            voices = eng.getProperty("voices")
            return [v.name for v in voices] if voices else []
        except Exception:
            return []

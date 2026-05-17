# =============================================================================
# utils/speech.py
# Speech Recognition (Speech-to-Text) Module
#
# Handles capturing audio from the microphone and converting it to text
# using the Google Speech Recognition API via the SpeechRecognition library.
#
# Key responsibilities:
#   - Initialize and configure the recognizer
#   - Capture audio from the default microphone
#   - Convert captured audio to a text string
#   - Handle recognition errors gracefully
#
# Author: AI Voice Assistant Project
# =============================================================================

import speech_recognition as sr
import logging

# Set up module-level logger
logger = logging.getLogger(__name__)


class SpeechRecognizer:
    """
    Wraps the SpeechRecognition library to provide a simple listen() method.

    Usage
    -----
        recognizer = SpeechRecognizer()
        text = recognizer.listen()
        if text:
            print("Heard:", text)
    """

    def __init__(self,
                 energy_threshold: int = 300,
                 pause_threshold: float = 0.8,
                 timeout: int = 5,
                 phrase_time_limit: int = 10):
        """
        Initialize the speech recognizer with tunable parameters.

        Parameters
        ----------
        energy_threshold : int
            Minimum audio energy to consider for recording.
            Lower = more sensitive to quiet sounds.
        pause_threshold : float
            Seconds of silence before the phrase is considered complete.
        timeout : int
            Maximum seconds to wait for speech to start.
        phrase_time_limit : int
            Maximum seconds allowed for a single phrase.
        """
        # Create SpeechRecognition Recognizer instance
        self.recognizer = sr.Recognizer()

        # Configure recognizer parameters for better accuracy
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.dynamic_energy_threshold = True  # Auto-adjust noise

        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit

        logger.info("SpeechRecognizer initialized.")

    def calibrate(self, duration: float = 0.4) -> None:
        """
        One-time ambient noise calibration for the current session.

        Call once when the user starts listening — not before every phrase.
        Doing adjust_for_ambient_noise on every listen() often raises the
        energy threshold and makes the mic appear unresponsive on Windows laptops.
        """
        with sr.Microphone() as source:
            logger.info("Calibrating microphone (%.1fs)...", duration)
            self.recognizer.adjust_for_ambient_noise(source, duration=duration)

    def listen(self) -> str:
        """
        Listen to the microphone and return transcribed text.

        The method:
          1. Opens the default microphone
          2. Waits for the user to speak (call :meth:`calibrate` once before
             looping if you want ambient noise adjustment)
          3. Converts speech to text via Google Web Speech API

        Returns
        -------
        str
            The recognised text in lowercase, or an empty string on failure.
        """
        try:
            with sr.Microphone() as source:
                logger.info("Listening for speech...")

                audio = self.recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_time_limit
                )

            logger.info("Recognising speech via Google API...")

            # Use Google's free Web Speech API for transcription
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Recognised: '{text}'")

            # Return lowercase for consistent downstream processing
            return text.lower()

        except sr.WaitTimeoutError:
            # User didn't speak within the timeout window
            logger.warning("No speech detected within timeout.")
            return ""

        except sr.UnknownValueError:
            # Audio was captured but could not be understood
            logger.warning("Speech was unintelligible.")
            return "Could not understand audio"

        except sr.RequestError as e:
            # Network error or API failure
            logger.error(f"Google Speech API error: {e}")
            return "Speech service unavailable"

        except OSError as e:
            # Microphone hardware not available
            logger.error(f"Microphone not available: {e}")
            return "Microphone not found"

        except Exception as e:
            logger.error(f"Unexpected speech recognition error: {e}")
            return ""

    def is_microphone_available(self) -> bool:
        """
        Check whether a microphone is connected and accessible.

        Returns
        -------
        bool
            True if at least one microphone is available.
        """
        try:
            mics = sr.Microphone.list_microphone_names()
            return len(mics) > 0
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Quick self-test when running this file directly
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    rec = SpeechRecognizer()
    print("Microphone available:", rec.is_microphone_available())
    print("Say something...")
    result = rec.listen()
    print(f"You said: '{result}'")

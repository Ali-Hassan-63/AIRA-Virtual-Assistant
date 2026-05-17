# =============================================================================
# assistant.py
# Core AI Voice Assistant Logic
#
# This module is the brain of the assistant. It:
#   1. Loads the trained ML model
#   2. Accepts text input (from speech or keyboard)
#   3. Preprocesses the text via NLP pipeline
#   4. Predicts the user's intent using TF-IDF + Logistic Regression
#   5. Executes the corresponding action
#   6. Returns the response text and intent for display & TTS
#
# The Assistant class is used by the desktop app (interface.py). Run
#   python assistant.py
# to start the virtual assistant (GUI). Use --cli for keyboard-only testing.
#
# Author: AI Voice Assistant Project
# =============================================================================

import os
import sys
import logging
import pickle
from typing import Tuple, Optional

# ---------------------------------------------------------------------------
# Ensure project root is in sys.path so relative imports work
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.preprocessing import clean_text
from utils.actions import execute_action

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model file locations (relative to project root)
# ---------------------------------------------------------------------------
MODEL_PATH      = os.path.join(BASE_DIR, 'models', 'model.pkl')
VECTORIZER_PATH = os.path.join(BASE_DIR, 'models', 'vectorizer.pkl')

# ---------------------------------------------------------------------------
# Confidence threshold for intent classification
# If the top-predicted probability is below this, we treat it as unknown
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.25


class VoiceAssistant:
    """
    Virtual assistant core: intent classification and action execution.

    Pipeline:
        user text
        → NLP preprocessing (clean_text)
        → TF-IDF vectorization (inside the sklearn Pipeline)
        → Logistic Regression intent classification
        → Action execution
        → Response string

    Usage
    -----
        assistant = VoiceAssistant()
        response, intent = assistant.process("what time is it")
        print(response)
    """

    NAME = "AIRA"  # Artificial Reasoning Intelligence Assistant

    def __init__(self):
        """Load the trained model pipeline. Raises if model file is missing."""
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """
        Load the pickled sklearn Pipeline from models/model.pkl.

        The Pipeline contains both the TF-IDF vectorizer and the classifier,
        so a single predict() call handles the full feature extraction + inference.
        """
        if not os.path.exists(MODEL_PATH):
            logger.error(
                f"Model file not found: {MODEL_PATH}\n"
                "Please run 'python train_model.py' first to train the model."
            )
            self.model_loaded = False
            return

        try:
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            self.model_loaded = True
            logger.info(f"Model loaded successfully from: {MODEL_PATH}")

            # Log available intent classes for reference
            if hasattr(self.model, 'classes_'):
                logger.info(f"Known intents: {list(self.model.classes_)}")
            elif hasattr(self.model, 'named_steps'):
                clf = self.model.named_steps.get('clf')
                if clf and hasattr(clf, 'classes_'):
                    logger.info(f"Known intents: {list(clf.classes_)}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model_loaded = False

    def predict_intent(self, cleaned_text: str) -> Tuple[str, float]:
        """
        Predict the intent for preprocessed text.

        Parameters
        ----------
        cleaned_text : str
            Text that has already been through clean_text().

        Returns
        -------
        Tuple[str, float]
            (predicted_intent, confidence_probability)
        """
        if not self.model_loaded or self.model is None:
            return 'unknown', 0.0

        if not cleaned_text.strip():
            return 'unknown', 0.0

        try:
            # The pipeline vectorizes and classifies in one step
            probabilities = self.model.predict_proba([cleaned_text])[0]
            predicted_idx = probabilities.argmax()

            # Access class labels from the classifier step
            clf = self.model.named_steps.get('clf', self.model)
            classes = clf.classes_ if hasattr(clf, 'classes_') else []

            intent = classes[predicted_idx] if len(classes) > predicted_idx else 'unknown'
            confidence = float(probabilities[predicted_idx])

            return intent, confidence

        except Exception as e:
            logger.error(f"Intent prediction error: {e}")
            return 'unknown', 0.0

    def process(self, user_text: str) -> Tuple[str, str, float]:
        """
        Full processing pipeline for a user utterance.

        Steps:
          1. NLP preprocessing (lowercase, remove stopwords, etc.)
          2. Intent prediction via ML model
          3. Confidence check (fallback to 'unknown' if below threshold)
          4. Action execution

        Parameters
        ----------
        user_text : str
            Raw text from speech recognition or keyboard input.

        Returns
        -------
        Tuple[str, str, float]
            (response_text, predicted_intent, confidence)
        """
        if not user_text or not user_text.strip():
            return "I didn't catch that. Could you try again?", 'unknown', 0.0

        logger.info(f"Processing: '{user_text}'")

        # Step 1: NLP preprocessing
        cleaned = clean_text(user_text)
        logger.debug(f"Cleaned text: '{cleaned}'")

        # Step 2: Intent prediction
        intent, confidence = self.predict_intent(cleaned)
        logger.info(f"Predicted intent: '{intent}' (confidence: {confidence:.2%})")

        # Step 3: Confidence threshold check
        if confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"Low confidence ({confidence:.2%}), falling back to unknown.")
            intent = 'unknown'

        # Step 4: Execute the appropriate action
        response = execute_action(intent, user_text)
        logger.info(f"Response: '{response}'")

        return response, intent, confidence

    def get_greeting(self) -> str:
        """Return the assistant's startup greeting."""
        return (
            f"I'm {self.NAME}, your virtual assistant. "
            "How can i help you. "
        )

    def is_exit_intent(self, intent: str) -> bool:
        """Return True if the user wants to quit."""
        return intent == 'exit'


# =============================================================================
# CLI / standalone test mode
# =============================================================================

def _run_cli_test_mode() -> None:
    """Keyboard-only loop for quick testing (no GUI, no voice)."""
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s: %(message)s')

    assistant = VoiceAssistant()

    if not assistant.model_loaded:
        print("\nERROR: Model not loaded.")
        print("Run: python train_model.py\n")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"  {VoiceAssistant.NAME} — CLI test mode (--cli)")
    print(f"{'='*50}")
    print(assistant.get_greeting())
    print("\nType commands (or 'quit' to exit):\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input or user_input.lower() in ('quit', 'exit', 'bye'):
                print("Assistant: Goodbye!")
                break

            response, intent, conf = assistant.process(user_input)
            print(f"Intent    : {intent} ({conf:.1%})")
            print(f"Assistant : {response}\n")

        except KeyboardInterrupt:
            print("\nAssistant: Goodbye!")
            break


def _run_virtual_assistant_app() -> None:
    """Launch the full desktop virtual assistant (voice + chat + TTS)."""
    import interface  # deferred import avoids circular init issues

    interface.main()


if __name__ == '__main__':
    if '--cli' in sys.argv or '-t' in sys.argv:
        _run_cli_test_mode()
    else:
        _run_virtual_assistant_app()

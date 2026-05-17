# =============================================================================
# utils/preprocessing.py
# NLP Text Preprocessing Module
#
# This module handles all text preprocessing steps required before passing
# text through the ML pipeline. Steps include:
#   1. Lowercasing
#   2. Punctuation & special character removal
#   3. Tokenization
#   4. Stopword removal
#   5. Joining cleaned tokens back into a string
#
# Author: AI Voice Assistant Project
# =============================================================================

import re
import string
import nltk

# ---------------------------------------------------------------------------
# Download required NLTK resources (only needed once)
# These are downloaded silently to avoid cluttering the console output.
# ---------------------------------------------------------------------------
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab', quiet=True)

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords


# ---------------------------------------------------------------------------
# Load English stopwords once at module level for performance
# ---------------------------------------------------------------------------
ENGLISH_STOPWORDS = set(stopwords.words('english'))


def clean_text(text: str) -> str:
    """
    Perform full NLP preprocessing on a raw input string.

    Pipeline:
        raw text
        → lowercase
        → remove punctuation & digits
        → tokenize
        → remove stopwords
        → rejoin

    Parameters
    ----------
    text : str
        Raw input string (e.g. "What's the Weather like TODAY?")

    Returns
    -------
    str
        Cleaned, lowercase, stopword-free string suitable for TF-IDF.
    """

    if not isinstance(text, str):
        # Safely handle non-string input (e.g. NaN from CSV)
        text = str(text)

    # Step 1: Convert everything to lowercase
    # Rationale: "Hello" and "hello" should be treated identically
    text = text.lower()

    # Step 2: Remove punctuation and special characters
    # We keep only alphabetic characters and spaces
    text = re.sub(r'[^a-z\s]', '', text)

    # Step 3: Remove extra whitespace created by the replacements above
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)

    # Step 4: Tokenize — split string into individual word tokens
    tokens = word_tokenize(text)

    # Step 5: Remove stopwords (common words like "the", "is", "at", etc.)
    # Stopwords carry little semantic information for intent classification
    tokens = [token for token in tokens if token not in ENGLISH_STOPWORDS]

    # Step 6: Rejoin tokens into a single cleaned string for TF-IDF input
    cleaned = ' '.join(tokens)

    return cleaned


def preprocess_series(series):
    """
    Apply clean_text() to every element of a pandas Series.

    Parameters
    ----------
    series : pd.Series
        A series of raw text strings (e.g. the 'text' column of the dataset).

    Returns
    -------
    pd.Series
        Series with each element replaced by its cleaned version.
    """
    return series.apply(clean_text)


# ---------------------------------------------------------------------------
# Quick self-test when running this file directly
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    samples = [
        "What's the Weather like TODAY?",
        "OPEN YouTube please!!!",
        "Hello there, how are you doing?",
        "Calculate 25 + 7 for me",
    ]
    print("Preprocessing self-test:")
    print("-" * 40)
    for s in samples:
        print(f"  Input : {s}")
        print(f"  Output: {clean_text(s)}")
        print()

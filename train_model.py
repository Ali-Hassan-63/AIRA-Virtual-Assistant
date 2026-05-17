# =============================================================================
# train_model.py
# ML Model Training Script
#
# This script:
#   1. Loads the intent dataset from intents.csv
#   2. Preprocesses text using NLP pipeline
#   3. Trains TF-IDF + Logistic Regression classifier
#   4. Evaluates with accuracy, precision, recall, F1, confusion matrix
#   5. Runs training N times and reports mean ± std deviation
#   6. Saves the best model and vectorizer to models/
#
# Run this script before starting the assistant:
#   python train_model.py
#
# Author: AI Voice Assistant Project
# =============================================================================

import os
import sys
import logging
import warnings
import pickle

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)
from sklearn.pipeline import Pipeline

warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Configure logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATASET_PATH = os.path.join(BASE_DIR, 'intents.csv')

MODELS_DIR = os.path.join(BASE_DIR, 'models')

MODEL_PATH = os.path.join(MODELS_DIR, 'model.pkl')
VECTORIZER_PATH = os.path.join(MODELS_DIR, 'vectorizer.pkl')

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
N_RUNS = 5
TEST_SIZE = 0.2
RANDOM_SEED_BASE = 42

# TF-IDF
TFIDF_MAX_FEATURES = 5000
TFIDF_NGRAM_RANGE = (1, 2)
TFIDF_SUBLINEAR_TF = True

# Logistic Regression
LR_C = 5.0
LR_MAX_ITER = 1000
LR_SOLVER = 'lbfgs'


# =============================================================================
# Dataset Loading
# =============================================================================

def load_dataset(dataset_path: str) -> pd.DataFrame:
    """
    Load dataset from intents.csv
    """

    logger.info(f"Loading dataset: {dataset_path}")

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(
            f"Dataset file not found: {dataset_path}"
        )

    df = pd.read_csv(dataset_path)

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Alternate names for intent column
    if 'intent' not in df.columns:
        for alt in ('label', 'category', 'class', 'tag'):
            if alt in df.columns:
                df.rename(columns={alt: 'intent'}, inplace=True)
                break

    # Alternate names for text column
    if 'text' not in df.columns:
        for alt in ('sentence', 'utterance', 'query', 'input', 'speech'):
            if alt in df.columns:
                df.rename(columns={alt: 'text'}, inplace=True)
                break

    # Validate columns
    if 'text' not in df.columns or 'intent' not in df.columns:
        raise ValueError(
            "CSV must contain 'text' and 'intent' columns."
        )

    df = df[['text', 'intent']]

    logger.info(f"Total samples loaded: {len(df)}")

    return df


# =============================================================================
# Preprocessing
# =============================================================================

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and preprocess dataset
    """

    from utils.preprocessing import preprocess_series

    initial_count = len(df)

    # Remove missing values
    df = df.dropna(subset=['text', 'intent'])

    # Clean columns
    df['text'] = df['text'].astype(str).str.strip()
    df['intent'] = df['intent'].astype(str).str.strip().str.lower()

    # Remove empty rows
    df = df[df['text'] != '']
    df = df[df['intent'] != '']

    # Remove duplicates
    df = df.drop_duplicates(subset=['text', 'intent'])

    logger.info(
        f"After cleaning: {len(df)} samples "
        f"(removed {initial_count - len(df)} rows)"
    )

    # NLP preprocessing
    logger.info("Applying NLP preprocessing...")

    df['text_clean'] = preprocess_series(df['text'])

    # Remove empty processed text
    df = df[df['text_clean'].str.strip() != '']

    # Show intent distribution
    class_counts = df['intent'].value_counts()

    logger.info(
        f"Intent distribution:\n{class_counts.to_string()}"
    )

    return df.reset_index(drop=True)


# =============================================================================
# Model Pipeline
# =============================================================================

def build_pipeline() -> Pipeline:
    """
    Build TF-IDF + Logistic Regression pipeline
    """

    tfidf = TfidfVectorizer(
        max_features=TFIDF_MAX_FEATURES,
        ngram_range=TFIDF_NGRAM_RANGE,
        sublinear_tf=TFIDF_SUBLINEAR_TF,
        analyzer='word',
        token_pattern=r'\b[a-z]{2,}\b',
    )

    classifier = LogisticRegression(
        C=LR_C,
        max_iter=LR_MAX_ITER,
        solver=LR_SOLVER,
        random_state=RANDOM_SEED_BASE,
    )

    pipeline = Pipeline([
        ('tfidf', tfidf),
        ('clf', classifier)
    ])

    return pipeline


# =============================================================================
# Evaluation
# =============================================================================

def evaluate_model(model, X_test, y_test, run_idx: int) -> dict:

    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)

    prec = precision_score(
        y_test,
        y_pred,
        average='weighted',
        zero_division=0
    )

    rec = recall_score(
        y_test,
        y_pred,
        average='weighted',
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_pred,
        average='weighted',
        zero_division=0
    )

    logger.info(
        f"Run {run_idx + 1}: "
        f"Acc={acc:.4f}  "
        f"Prec={prec:.4f}  "
        f"Rec={rec:.4f}  "
        f"F1={f1:.4f}"
    )

    return {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1
    }


def print_detailed_report(model, X_test, y_test, label_names):

    y_pred = model.predict(X_test)

    print("\n" + "=" * 60)
    print("DETAILED CLASSIFICATION REPORT")
    print("=" * 60)

    print(
        classification_report(
            y_test,
            y_pred,
            target_names=sorted(label_names),
            zero_division=0
        )
    )

    print("CONFUSION MATRIX")
    print("-" * 60)

    cm = confusion_matrix(
        y_test,
        y_pred,
        labels=sorted(label_names)
    )

    labels_sorted = sorted(label_names)

    header = f"{'':>15}" + "".join(
        f"{l:>12}" for l in labels_sorted
    )

    print(header)

    for i, row_label in enumerate(labels_sorted):

        row = f"{row_label:>15}" + "".join(
            f"{v:>12}" for v in cm[i]
        )

        print(row)

    print("=" * 60)


def print_summary(results):

    metrics = ['accuracy', 'precision', 'recall', 'f1']

    print("\n" + "=" * 60)
    print(f"EVALUATION SUMMARY — {len(results)} RUNS")
    print("=" * 60)

    for metric in metrics:

        values = [r[metric] for r in results]

        mean_val = np.mean(values) * 100
        std_val = np.std(values) * 100

        print(
            f"{metric.capitalize():>12} = "
            f"{mean_val:.1f} ± {std_val:.1f}%"
        )

    print("=" * 60)


# =============================================================================
# Save / Load Model
# =============================================================================

def save_model(model):

    os.makedirs(MODELS_DIR, exist_ok=True)

    # Save complete pipeline
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

    logger.info(f"Model saved → {MODEL_PATH}")

    # Save vectorizer separately
    vectorizer_obj = model.named_steps['tfidf']

    with open(VECTORIZER_PATH, 'wb') as f:
        pickle.dump(vectorizer_obj, f)

    logger.info(f"Vectorizer saved → {VECTORIZER_PATH}")


def load_model():

    if not os.path.exists(MODEL_PATH):

        logger.error(
            f"Model not found at {MODEL_PATH}"
        )

        return None

    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    logger.info("Model loaded successfully.")

    return model


# =============================================================================
# Training Function
# =============================================================================

def train(n_runs: int = N_RUNS) -> bool:

    logger.info("=" * 60)
    logger.info("AI VOICE ASSISTANT — MODEL TRAINING")
    logger.info("=" * 60)

    # ----------------------------------------------------------------
    # Load dataset
    # ----------------------------------------------------------------
    try:
        df = load_dataset(DATASET_PATH)

    except (FileNotFoundError, ValueError) as e:

        logger.error(str(e))
        return False

    # ----------------------------------------------------------------
    # Preprocess
    # ----------------------------------------------------------------
    df = preprocess_dataframe(df)

    if len(df) < 10:

        logger.error(
            "Dataset has fewer than 10 usable samples."
        )

        return False

    X = df['text_clean'].values
    y = df['intent'].values

    class_labels = sorted(
        df['intent'].unique().tolist()
    )

    logger.info(f"Feature samples: {len(X)}")

    logger.info(
        f"Classes ({len(class_labels)}): {class_labels}"
    )

    # ----------------------------------------------------------------
    # Multiple runs
    # ----------------------------------------------------------------
    logger.info(
        f"\nRunning {n_runs} independent training runs..."
    )

    all_results = []

    best_accuracy = 0.0
    best_model = None
    best_X_test = None
    best_y_test = None

    for i in range(n_runs):

        seed = RANDOM_SEED_BASE + i

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=seed,
            stratify=y if len(np.unique(y)) > 1 else None
        )

        # Build model
        model = build_pipeline()

        # Train
        model.fit(X_train, y_train)

        # Evaluate
        run_metrics = evaluate_model(
            model,
            X_test,
            y_test,
            run_idx=i
        )

        all_results.append(run_metrics)

        # Save best
        if run_metrics['accuracy'] > best_accuracy:

            best_accuracy = run_metrics['accuracy']

            best_model = model
            best_X_test = X_test
            best_y_test = y_test

    # ----------------------------------------------------------------
    # Detailed report
    # ----------------------------------------------------------------
    print_detailed_report(
        best_model,
        best_X_test,
        best_y_test,
        class_labels
    )

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print_summary(all_results)

    # ----------------------------------------------------------------
    # Save model
    # ----------------------------------------------------------------
    save_model(best_model)

    logger.info(
        "\nTraining complete! "
        "Model is ready for the assistant."
    )

    return True


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == '__main__':

    success = train()

    sys.exit(0 if success else 1)
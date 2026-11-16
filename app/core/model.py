"""TF-IDF content model. Similarity is computed per query, never as a full N x N matrix
(36k papers would need ~10.5 GB dense)."""

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from core.data import DATA_PATH, ROOT

MODEL_DIR = ROOT / "models"


@st.cache_resource(show_spinner="Building similarity model (first run only, ~20 s)...")
def _build(fingerprint: str, _texts: pd.Series):
    path = MODEL_DIR / f"tfidf_{fingerprint}.joblib"
    if path.exists():
        try:
            return joblib.load(path)
        except Exception:
            path.unlink(missing_ok=True)

    vectorizer = TfidfVectorizer(stop_words="english", min_df=2)
    matrix = vectorizer.fit_transform(_texts)  # rows are L2-normalised, so dot product = cosine

    MODEL_DIR.mkdir(exist_ok=True)
    for old in MODEL_DIR.glob("tfidf_*.joblib"):  # drop caches built from older data
        old.unlink()
    joblib.dump((vectorizer, matrix), path)
    return vectorizer, matrix


def get_model(df: pd.DataFrame):
    # cache is keyed on the data file, so a new info.csv rebuilds the model automatically
    fingerprint = f"{len(df)}_{int(DATA_PATH.stat().st_mtime)}"
    return _build(fingerprint, df["full_text"])


def scores_for_paper(matrix, idx: int) -> np.ndarray:
    return linear_kernel(matrix[idx], matrix).ravel()


def scores_for_text(vectorizer, matrix, text: str) -> np.ndarray:
    return linear_kernel(vectorizer.transform([text]), matrix).ravel()


def top_matches(
    df: pd.DataFrame, scores: np.ndarray, mask: pd.Series, n: int, exclude: int | None = None
) -> pd.DataFrame:
    scores = np.where(mask.to_numpy(), scores, -1.0)
    if exclude is not None:
        scores[exclude] = -1.0
    order = np.argsort(-scores)[:n]
    order = order[scores[order] > 0]
    return df.iloc[order].assign(Score=scores[order])

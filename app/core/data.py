"""Load and clean the paper dataset (data/processed/info.csv)."""

import ast
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "info.csv"

TEXT_COLS = ["Title", "Abstract", "Keywords", "Publication_name", "Authors", "Link", "Date"]


def _parse_subjects(value) -> list[str]:
    """Subject_Fields is stored as "['Chemistry', 'Energy']" or "Chemistry, Energy"."""
    if not isinstance(value, str) or not value.strip():
        return []
    if value.lstrip().startswith("["):
        try:
            return [str(s).strip() for s in ast.literal_eval(value) if str(s).strip()]
        except (ValueError, SyntaxError):
            pass
    return [p.strip(" '\"[]") for p in value.split(",") if p.strip(" '\"[]")]


def _clean_link(link: str) -> str:
    link = link.strip()
    if not link or link == "No Link":
        return ""
    return link if link.startswith("http") else f"https://{link}"


# cache_resource (not cache_data): one shared, read-only frame instead of an 86 MB copy per rerun.
# Callers must not mutate it in place.
@st.cache_resource(show_spinner="Loading papers...")
def _load(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Drive's info.csv uses spaced/capitalised names; normalise once here
    df = df.rename(columns={"Publication Name": "Publication_name", "Author_Count": "Author_count"})

    for col in TEXT_COLS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    df["Abstract"] = df["Abstract"].replace("No Abstract", "")
    df["Keywords"] = df["Keywords"].replace("-", "")  # extraction notebook's "missing" marker
    df["Link"] = df["Link"].map(_clean_link)
    df["Year"] = pd.to_numeric(df.get("Year"), errors="coerce").fillna(0).astype(int)
    df["Author_count"] = pd.to_numeric(df.get("Author_count"), errors="coerce").fillna(0).astype(int)
    df["Subjects"] = df.get("Subject_Fields", pd.Series("", index=df.index)).map(_parse_subjects)
    df["Subject_Fields"] = df["Subjects"].map(", ".join)

    df["full_text"] = df["Title"] + " " + df["Abstract"] + " " + df["Keywords"]
    df = df[df["full_text"].str.strip().str.len() > 10].reset_index(drop=True)
    df["Label"] = [f"{t}  ({y})" if y else t for t, y in zip(df["Title"], df["Year"], strict=True)]
    df.attrs["subjects"] = sorted({s for subjects in df["Subjects"] for s in subjects})
    return df


def get_papers() -> pd.DataFrame:
    if not DATA_PATH.exists():
        st.error(f"Dataset not found at `{DATA_PATH}`. Run `python scripts/download_data.py` first.")
        st.stop()
    return _load(str(DATA_PATH), DATA_PATH.stat().st_mtime)


def subject_options(df: pd.DataFrame) -> list[str]:
    return df.attrs.get("subjects") or sorted({s for subjects in df["Subjects"] for s in subjects})


def apply_filters(df: pd.DataFrame, years=None, subjects=None, text: str = "", text_cols=("Keywords",)) -> pd.Series:
    """Boolean mask for the common filters."""
    mask = pd.Series(True, index=df.index)
    if years:
        mask &= df["Year"].between(*years)
    if subjects:
        wanted = set(subjects)
        mask &= df["Subjects"].map(lambda s: bool(wanted.intersection(s)))
    text = text.strip()
    if text:
        hit = pd.Series(False, index=df.index)
        for col in text_cols:
            hit |= df[col].str.contains(text, case=False, regex=False)
        mask &= hit
    return mask

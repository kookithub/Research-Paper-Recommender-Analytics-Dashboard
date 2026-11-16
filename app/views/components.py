"""Shared UI pieces."""

import re

import pandas as pd
import streamlit as st

from core.data import apply_filters, subject_options

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>#$|~])")


def esc(text: str) -> str:
    """Escape Markdown/LaTeX so titles and abstracts with $, *, [ ] render as plain text."""
    return _MD_SPECIAL.sub(r"\\\1", str(text))


def safe_url(url: str) -> str:
    """Percent-encode characters that would end a Markdown link target early."""
    return url.strip().replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def short_authors(authors: str, limit: int = 3) -> str:
    names = [a.strip() for a in authors.split(",") if a.strip()]
    if not names:
        return "Unknown authors"
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])} +{len(names) - limit} more"


def paper_card(row: pd.Series, score: float | None = None, expanded: bool = False) -> None:
    with st.container(border=True):
        title = esc(row["Title"])
        st.markdown(f"**[{title}]({safe_url(row['Link'])})**" if row["Link"] else f"**{title}**")
        meta = [
            str(row["Year"]) if row["Year"] else "",
            esc(row["Publication_name"]),
            esc(short_authors(row["Authors"])),
        ]
        st.caption(" · ".join(m for m in meta if m))
        badges = [f":green-badge[:material/join_inner: {score:.0%} match]"] if score is not None else []
        badges += [f":blue-badge[{esc(s)}]" for s in row["Subjects"]]
        if badges:
            st.markdown(" ".join(badges))

        abstract = row["Abstract"]
        if abstract:
            if expanded:
                st.markdown(esc(abstract))
            else:
                preview = abstract if len(abstract) <= 280 else abstract[:280].rsplit(" ", 1)[0] + "…"
                st.markdown(esc(preview))
                if len(abstract) > 280:
                    with st.expander("Full abstract"):
                        st.markdown(esc(abstract))
        else:
            st.caption("No abstract available.")
        if row["Keywords"]:
            st.caption(f"Keywords: {esc(row['Keywords'])}")


def filter_controls(df: pd.DataFrame, key: str, with_text: bool = True, text_label: str = "Keyword contains"):
    """Year range + subject + optional text filter. Returns a boolean mask."""
    years_all = df.loc[df["Year"] > 0, "Year"]
    lo, hi = int(years_all.min()), int(years_all.max())
    years = st.slider("Years", lo, hi, (lo, hi), key=f"{key}_years")
    subjects = st.multiselect("Subject areas", subject_options(df), key=f"{key}_subjects", placeholder="Any subject")
    text = st.text_input(text_label, key=f"{key}_text", placeholder="e.g. machine learning") if with_text else ""
    return years, subjects, text


def mask_from(df, years, subjects, text, text_cols=("Keywords",)):
    full_range = years == (int(df.loc[df["Year"] > 0, "Year"].min()), int(df["Year"].max()))
    return apply_filters(df, None if full_range else years, subjects, text, text_cols)

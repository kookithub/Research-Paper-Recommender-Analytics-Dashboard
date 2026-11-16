import pandas as pd
import streamlit as st

from core.data import get_papers
from views.components import filter_controls, mask_from


def _bar(series: pd.Series, label: str, n: int = 10) -> None:
    """Horizontal bar chart of the n most common non-empty values, largest on top."""
    counts = series[series.astype(bool)].value_counts().head(n)
    data = counts.rename("Papers").rename_axis(label).reset_index()
    st.bar_chart(data, x=label, y="Papers", horizontal=True, sort="-Papers", height=360)


def insights_page():
    df_all = get_papers()
    st.title("Dataset insights")

    with st.sidebar:
        st.subheader("Filter")
        years, subjects, _ = filter_controls(df_all, key="ins", with_text=False)
    df = df_all[mask_from(df_all, years, subjects, "")]
    if df.empty:
        st.warning("No papers match these filters.")
        return

    # horizontal container wraps metrics onto a new line on narrow screens instead of clipping them
    with st.container(horizontal=True, gap="large"):
        st.metric("Papers", f"{len(df):,}", width="content")
        st.metric("Years", f"{df['Year'][df['Year'] > 0].min()}–{df['Year'].max()}", width="content")
        st.metric(
            "Sources",
            f"{df['Publication_name'].nunique():,}",
            help="Distinct journals, conferences and books.",
            width="content",
        )
        st.metric(
            "Authors / paper",
            f"{df['Author_count'].median():.0f}",
            help=(
                f"Median. The mean is {df['Author_count'].mean():.1f}, "
                "pulled up by large collaborations with thousands of authors."
            ),
            width="content",
        )

    st.subheader("Papers per year")
    per_year = df[df["Year"] > 0]["Year"].value_counts().sort_index()
    st.bar_chart(per_year.rename("Papers").rename_axis("Year"), height=280)

    subjects_long = df[["Year", "Subjects"]].explode("Subjects").dropna()
    st.subheader("Top subject areas")
    _bar(subjects_long["Subjects"], "Subject")

    st.subheader("Top sources")
    _bar(df["Publication_name"], "Source")

    st.subheader("Subject areas over time")
    top6 = subjects_long["Subjects"].value_counts().head(6).index
    trend = (
        subjects_long[subjects_long["Subjects"].isin(top6) & (subjects_long["Year"] > 0)]
        .groupby(["Year", "Subjects"])
        .size()
        .unstack(fill_value=0)
    )
    trend.index = trend.index.astype(str)  # numeric years would be labelled "2,010"
    st.line_chart(trend, x_label="Year", y_label="Papers", height=320)

    st.subheader("Most frequent first authors")
    first_authors = df["Authors"].str.split(",").str[0].str.strip()
    _bar(first_authors, "Author")
    st.caption("Some records list surnames only, so different people with the same surname may be counted together.")

import streamlit as st

from core.data import get_papers
from views.components import filter_controls, mask_from, paper_card

COLUMNS = [
    "Title",
    "Year",
    "Authors",
    "Author_count",
    "Publication_name",
    "Subject_Fields",
    "Keywords",
    "Link",
    "Abstract",
]


def explore_page():
    df = get_papers()
    st.title("Explore the data")

    with st.sidebar:
        st.subheader("Filter")
        years, subjects, text = filter_controls(df, key="exp", text_label="Search title, authors, keywords")

    view = df[mask_from(df, years, subjects, text, text_cols=("Title", "Authors", "Keywords"))]
    st.caption(
        f"{len(view):,} of {len(df):,} papers. Click a column header to sort, or select a row to see the full record."
    )

    event = st.dataframe(
        view[COLUMNS],
        hide_index=True,
        height=520,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Year": st.column_config.NumberColumn("Year", format="%d", width="small"),
            "Author_count": st.column_config.NumberColumn("# Authors", format="%d", width="small"),
            "Publication_name": st.column_config.TextColumn("Source"),
            "Subject_Fields": st.column_config.TextColumn("Subjects"),
            "Link": st.column_config.LinkColumn("Link", display_text="open"),
            "Abstract": st.column_config.TextColumn("Abstract", width="medium"),
        },
    )

    st.download_button(
        "Download filtered rows (CSV)",
        lambda: view[COLUMNS].to_csv(index=False).encode("utf-8"),  # built only on click, not every rerun
        file_name="papers_filtered.csv",
        mime="text/csv",
        icon=":material/download:",
    )

    rows = event.selection.rows
    if rows:
        st.markdown("##### Selected paper")
        paper_card(view.iloc[rows[0]], expanded=True)

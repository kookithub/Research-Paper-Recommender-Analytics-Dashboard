import streamlit as st

from core.data import get_papers
from core.model import get_model, scores_for_paper, scores_for_text, top_matches
from views.components import filter_controls, mask_from, paper_card


def recommend_page():
    df = get_papers()
    vectorizer, matrix = get_model(df)
    labels = df["Label"].tolist()

    st.title("Find related research")
    st.caption(
        f"Content-based matches over {len(df):,} Chulalongkorn papers on Scopus, using title, abstract and keywords."
    )

    with st.sidebar:
        st.subheader("Filter results")
        years, subjects, text = filter_controls(df, key="rec")
        n = st.slider("Number of results", 5, 30, 10, step=5)

    mode = st.radio("Start from", ["A topic", "A paper"], horizontal=True, label_visibility="collapsed")

    if mode == "A topic":
        query = st.text_input(
            "Describe what you are looking for",
            placeholder="e.g. deep learning for rice disease detection from leaf images",
        )
        if not query.strip():
            st.info("Type a topic, a question or a few keywords, then press Enter.")
            return
        scores = scores_for_text(vectorizer, matrix, query)
        if scores.max() <= 0:
            st.warning("None of those words appear in the dataset. Try different or more general terms.")
            return
        exclude = None
    else:
        idx = st.selectbox(
            "Pick a paper",
            options=range(len(df)),
            format_func=labels.__getitem__,
            index=None,
            placeholder=f"Type to search {len(df):,} titles…",
        )
        if idx is None:
            st.info("Start typing a title to pick a paper, and similar papers will show up below.")
            return
        st.markdown("##### Selected paper")
        paper_card(df.iloc[idx])
        scores = scores_for_paper(matrix, idx)
        exclude = idx

    mask = mask_from(df, years, subjects, text)
    results = top_matches(df, scores, mask, n, exclude=exclude)

    st.markdown(f"##### Top {len(results)} matches")
    if results.empty:
        st.warning("No matches with the current filters. Widen the year range or clear the subject/keyword filters.")
        return
    for _, row in results.iterrows():
        paper_card(row, score=row["Score"])

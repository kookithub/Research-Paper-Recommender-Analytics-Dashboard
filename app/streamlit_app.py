"""Research Paper Recommender & Analytics Dashboard. Run from the repo root:  streamlit run app/streamlit_app.py"""

import streamlit as st

st.set_page_config(page_title="Research Paper Recommender", page_icon=":material/menu_book:", layout="wide")

from views.explore import explore_page  # noqa: E402  (set_page_config must run first)
from views.insights import insights_page  # noqa: E402
from views.recommend import recommend_page  # noqa: E402

page = st.navigation(
    [
        st.Page(recommend_page, title="Recommend", icon=":material/auto_awesome:", url_path="recommend", default=True),
        st.Page(insights_page, title="Insights", icon=":material/bar_chart:", url_path="insights"),
        st.Page(explore_page, title="Explore data", icon=":material/table_view:", url_path="explore"),
    ]
)
page.run()

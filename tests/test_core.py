import numpy as np
import pandas as pd
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from core import data
from core.model import scores_for_paper, scores_for_text, top_matches
from views.components import esc, safe_url, short_authors

CSV = """Title,Publication Name,Date,Authors,Author_Count,Keywords,Abstract,Link,Subject_Fields,Year
Solid oxide fuel cell modelling,J. Power Sources,2010-01-01,"A, B",2,"fuel cell, methane",Models of a solid oxide fuel cell fed by methane.,No Link,"['Energy', 'Chemistry']",2010
Fuel cell control structure,Chem Eng Trans,2014-01-01,C,1,-,Control of a solid oxide fuel cell with methane reforming.,www.example.com/p,"['Chem Eng']",2014
Rice leaf disease detection,Comp Elec Agri,2021-05-01,"D, E, F, G",4,"deep learning, rice",Deep learning detects rice leaf disease from images.,https://x.org/a,"['Comp Sci', 'Agri & Bio']",2021
Short,,2020-01-01,,0,,,,,2020
"""


@pytest.fixture(scope="module")
def df(tmp_path_factory):
    path = tmp_path_factory.mktemp("d") / "info.csv"
    path.write_text(CSV, encoding="utf-8")
    return data._load(str(path), 0.0)


def test_parse_subjects_handles_both_formats():
    assert data._parse_subjects("['Energy', 'Chemistry']") == ["Energy", "Chemistry"]
    assert data._parse_subjects("Energy, Chemistry") == ["Energy", "Chemistry"]
    assert data._parse_subjects("") == []
    assert data._parse_subjects(float("nan")) == []


def test_clean_link():
    assert data._clean_link("No Link") == ""
    assert data._clean_link("www.example.com/p") == "https://www.example.com/p"
    assert data._clean_link("http://a.b") == "http://a.b"


def test_load_normalises_columns_and_placeholders(df):
    assert {"Publication_name", "Author_count", "Subjects", "full_text", "Label"} <= set(df.columns)
    assert len(df) == 3  # "Short" row has <10 chars of text and is dropped
    assert df.loc[1, "Keywords"] == ""  # "-" placeholder removed
    assert df.loc[0, "Subjects"] == ["Energy", "Chemistry"]
    assert df.attrs["subjects"] == ["Agri & Bio", "Chem Eng", "Chemistry", "Comp Sci", "Energy"]


def test_apply_filters(df):
    assert data.apply_filters(df, years=(2012, 2023)).tolist() == [False, True, True]
    assert data.apply_filters(df, subjects=["Comp Sci"]).tolist() == [False, False, True]
    assert data.apply_filters(df, text="METHANE").tolist() == [True, False, False]
    assert data.apply_filters(df, text="rice", text_cols=("Title",)).tolist() == [False, False, True]


def test_per_query_scores_equal_full_matrix_row(df):
    """The app's per-query scoring returns exactly the row the old N x N matrix stored."""
    vec = TfidfVectorizer(stop_words="english")
    matrix = vec.fit_transform(df["full_text"])
    full = linear_kernel(matrix, matrix)
    for i in range(len(df)):
        np.testing.assert_allclose(scores_for_paper(matrix, i), full[i])


def test_topic_query_ranks_relevant_paper_first(df):
    vec = TfidfVectorizer(stop_words="english")
    matrix = vec.fit_transform(df["full_text"])
    scores = scores_for_text(vec, matrix, "rice disease images")
    assert int(np.argmax(scores)) == 2


def test_top_matches_excludes_self_masks_and_drops_zero_scores(df):
    scores = np.array([1.0, 0.6, 0.0])
    all_rows = pd.Series(True, index=df.index)
    res = top_matches(df, scores, all_rows, n=5, exclude=0)
    assert res.index.tolist() == [1]  # self excluded, zero score dropped
    assert res["Score"].tolist() == [0.6]
    masked = top_matches(df, scores, pd.Series([True, False, True]), n=5)
    assert masked.index.tolist() == [0]


def test_ui_helpers():
    assert esc("cost $5 *bold* [x]") == r"cost \$5 \*bold\* \[x\]"
    assert safe_url("https://a.b/x (1)") == "https://a.b/x%20%281%29"
    assert short_authors("A, B, C, D, E") == "A, B, C +2 more"
    assert short_authors("") == "Unknown authors"

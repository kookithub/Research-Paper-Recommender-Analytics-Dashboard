"""Rebuild the dataset (2018-2023 only) from the raw Scopus zip.

Port of notebooks/Data_Extracting_Process.ipynb. Reads the JSON records straight
out of data/raw/ScopusData2018-2023.zip (no unzip needed). The app uses the full
2010-2023 info.csv instead; the 2010-2017 raw files are no longer obtainable
(Scopus API access ended), so this is for checking/reproducing the pipeline.

Run:  python scripts/download_data.py --raw && python scripts/build_dataset.py
"""

import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "data" / "raw" / "ScopusData2018-2023.zip"
OUT_PATH = ROOT / "data" / "processed" / "info_from_zip_2018-2023.csv"

# Scopus ASJC 2-digit prefix -> short field name (same map as the notebook)
FIELD_CODE = {
    10: "Multidisciplinary",
    11: "Agri & Bio",
    12: "Arts & Hum",
    13: "Biochem & Genetics",
    14: "Business & Mgmt",
    15: "Chem Eng",
    16: "Chemistry",
    17: "Comp Sci",
    18: "Decision Sci",
    19: "Earth & Planet",
    20: "Econ & Finance",
    21: "Energy",
    22: "Engineering",
    23: "Environment",
    24: "Immuno & Micro",
    25: "Materials",
    26: "Math",
    27: "Medicine",
    28: "Neuroscience",
    29: "Nursing",
    30: "Pharma & Tox",
    31: "Physics",
    32: "Psychology",
    33: "Social Sci",
    34: "Vet Med",
    35: "Dentistry",
    36: "Health",
}


def as_list(x):
    if isinstance(x, dict):
        return [x]
    return x if isinstance(x, list) else []


def author_name(a):
    given = a.get("ce:given-name", "") or a.get("given-name", "") or ""
    surname = a.get("ce:surname", "") or a.get("surname", "") or ""
    name = f"{given} {surname}".strip()
    return name or a.get("ce:indexed-name") or a.get("indexed-name") or ""


def parse(data, folder_year):
    root = data.get("abstracts-retrieval-response", {}) or {}
    item = root.get("item", {}) or {}
    head = (item.get("bibrecord", {}) or {}).get("head", {}) or {}
    core = root.get("coredata", {}) or {}
    source = head.get("source", {}) or {}

    title = core.get("dc:title") or head.get("citation-title") or source.get("title") or "Unknown Title"
    pub = core.get("prism:publicationName") or source.get("sourcetitle") or "Unknown Source"

    authors = []
    for group in as_list(head.get("author-group")):
        for a in as_list(group.get("author")):
            n = author_name(a)
            if n:
                authors.append(n)
    if not authors:
        creator = core.get("dc:creator", {})
        for a in as_list(creator.get("author") if isinstance(creator, dict) else None):
            n = author_name(a)
            if n:
                authors.append(n)

    abstract = core.get("dc:description") or "No Abstract"

    kw_raw = as_list((root.get("authkeywords") or {}).get("author-keyword"))
    keywords = ", ".join(k.get("$") for k in kw_raw if isinstance(k, dict) and k.get("$"))

    link = None
    for site in as_list(source.get("website")):
        for addr in as_list(site.get("ce:e-address")):
            if isinstance(addr, dict) and addr.get("$"):
                link = addr["$"]
                break
        if link:
            break
    if not link:
        for ln in as_list(core.get("link")):
            if isinstance(ln, dict) and ln.get("@ref") == "scopus":
                link = ln.get("@href")
                break

    codes = set()
    for s in as_list((root.get("subject-areas") or {}).get("subject-area")):
        code = str(s.get("@code") or "")
        if len(code) >= 2 and code[:2].isdigit():
            codes.add(int(code[:2]))
    fields = [FIELD_CODE[c] for c in sorted(codes) if c in FIELD_CODE]

    return {
        "Title": title,
        "Publication_name": pub,
        "Date": core.get("prism:coverDate"),
        "Authors": ", ".join(authors),
        "Author_count": len(authors),
        "Keywords": keywords,
        "Abstract": abstract,
        "Link": link or "No Link",
        "Subject_Fields": ", ".join(fields),
        "Folder_Year": folder_year,
    }


def main():
    if not ZIP_PATH.exists():
        sys.exit(f"Missing {ZIP_PATH}")
    rows, bad = [], 0
    with zipfile.ZipFile(ZIP_PATH) as z:
        for info in z.infolist():
            parts = info.filename.split("/")
            # keep ScopusData2018-2023/<year>/<eid>; skip __MACOSX, .DS_Store, dirs
            if info.is_dir() or parts[0].startswith("__MACOSX") or len(parts) != 3 or parts[2].startswith("."):
                continue
            try:
                data = json.loads(z.read(info).decode("utf-8"))
                rows.append(parse(data, int(parts[1]) if parts[1].isdigit() else None))
            except Exception as e:
                bad += 1
                if bad <= 5:
                    print(f"skip {info.filename}: {e!r}")

    df = pd.DataFrame(rows).drop_duplicates(subset=["Title"], keep="first")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = df["Date"].dt.year.fillna(df.pop("Folder_Year")).astype("Int64")
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"parsed {len(rows)} records ({bad} unreadable), {len(df)} after title dedupe")
    print(df["Year"].value_counts().sort_index().to_string())
    print(f"saved {OUT_PATH}")


if __name__ == "__main__":
    main()

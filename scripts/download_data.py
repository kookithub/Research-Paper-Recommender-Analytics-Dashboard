"""Download the dataset from the project's Google Drive (link-shared files).

python scripts/download_data.py          # info.csv only (86 MB) - all the app needs
python scripts/download_data.py --raw    # also the raw Scopus zip (502 MB, 2018-2023)
"""

import argparse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t"

FILES = {
    # path: (drive file id, size in bytes)
    "data/processed/info.csv": ("1F-bNqPESVX_6Tt6SyHpV4uGFp_FSw2K_", 86_440_262),
}
RAW_FILES = {
    "data/raw/ScopusData2018-2023.zip": ("1NAc-Tw1i0l8xdu3JZzjBdocqGQwbL0W3", 501_991_648),
}


def fetch(rel_path: str, file_id: str, size: int) -> None:
    dest = ROOT / rel_path
    if dest.exists() and dest.stat().st_size == size:
        print(f"ok      {rel_path} (already downloaded)")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"get     {rel_path} ({size / 1e6:.0f} MB)...")
    urllib.request.urlretrieve(URL.format(id=file_id), tmp)
    if tmp.stat().st_size != size:
        raise SystemExit(f"size mismatch for {rel_path}: got {tmp.stat().st_size}, expected {size}")
    tmp.replace(dest)
    print(f"saved   {rel_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", action="store_true", help="also download the raw Scopus zip")
    args = ap.parse_args()
    files = {**FILES, **(RAW_FILES if args.raw else {})}
    for path, (file_id, size) in files.items():
        fetch(path, file_id, size)


if __name__ == "__main__":
    main()

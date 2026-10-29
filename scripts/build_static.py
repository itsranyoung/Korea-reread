#!/usr/bin/env python3
"""Build a safe static deployment directory for Vercel.

Only allowlisted public pages and reviewed/public catalog JSON are shipped.
Research scripts, audit logs, source originals, and *-draft.json stay private
to the repository. No external dependencies or API access required.
"""
import json
from pathlib import Path
from shutil import copy2, rmtree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".vercel-output-static"
PAGES = ("index.html", "archive-1901.html", "archive-reader.html")
DATA = (
    "issues-1901-1906.json",
    "1901.json",
    "1904.json",
    "1906.json",
)

def main():
    if OUT.exists():
        rmtree(OUT)
    (OUT / "data").mkdir(parents=True)
    for name in PAGES:
        src = ROOT / name
        if not src.is_file():
            raise FileNotFoundError(f"Missing public page: {name}")
        copy2(src, OUT / name)
    for name in DATA:
        src = ROOT / "data" / name
        if not src.is_file():
            raise FileNotFoundError(f"Missing public catalog: {name}")
        json.loads(src.read_text(encoding="utf-8"))
        copy2(src, OUT / "data" / name)
    # Optional catalog appears only after the original DOCX cross-check succeeds.
    optional = ROOT / "data" / "1902.json"
    if optional.is_file():
        json.loads(optional.read_text(encoding="utf-8"))
        copy2(optional, OUT / "data" / "1902.json")
    # Verify all relative local asset references in the main archive.
    main_html = (OUT / "index.html").read_text(encoding="utf-8")
    for name in DATA:
        if f"./data/{name}" in main_html and not (OUT / "data" / name).exists():
            raise AssertionError(f"Unresolved data URL: {name}")
    print(f"Built {len(PAGES)} public HTML pages and {len(DATA)} public JSON files in {OUT.name}")

if __name__ == "__main__":
    main()

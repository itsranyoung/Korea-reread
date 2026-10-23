# KOREA RE:READ — Source ingestion (1901–1906)

## Primary source
Homer B. Hulbert (ed.), *The Korea Review*, 1901–1906. Source provider: https://anthony.sogang.ac.kr/KoreaReview/index.html

The provider describes its files as **corrected OCR**. They are not guaranteed to match the original printed pages in every detail.

## 1. Acquire volume text as printed-page blocks
```sh
python -m pip install beautifulsoup4
python scripts/ingest_volumes.py --years 1901 1902 1903 1904 1905 1906
```
This command requests each annual HTML file, saves a local source copy, extracts text and attempts to divide by `[page N]` markers. Result files:
- `imports/<year>/source.html` — downloaded HTML
- `imports/<year>/pages.json` — machine-extracted **page blocks, not articles**
- `imports/<year>/manifest.json` — source and integrity warnings

Do **not** commit or publish these files before confirming re-use permissions, completeness and text accuracy. The extraction has not been executed within ChatGPT because its runtime cannot reach the external source site.

## 2. Manually verify article boundaries
Use each issue table of contents and inspect original scans. A printed page can contain multiple articles or one article can continue across pages. Cross-check title, author, page spans, footnotes, serial articles and issue dates. Save reviewed texts and metadata as structured JSON with article-level citations. Avoid using page-block output as if it were complete articles.

## 3. Provisional NLP
`scripts/process_archive.py` accepts manually divided article text JSON and generates preliminary entity and keyword candidates. It does not currently generate an AI Korean summary. Label all machine candidates as unverified until human review.

## 4. Publication
Only explicitly reviewed and cleared article records should be included in public `data/articles-<year>.json`. Existing `data/1901.json` is a **selection of 37 table-of-contents entries**, not the full volume. Existing `data/issues-1901-1906.json` stores 72 monthly **issue placeholders**, not 72 articles.

## Academic research audit
Keep separate originals, corrected OCR, AI draft, human corrected edition, reviewer rationale and dates. Record exact source URLs and printed pages per passage to measure AI vs. human intervention.

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
PAGES = ("index.html",)
DATA = (
    "issues-1901-1906.json",
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
    verified = ROOT / "data" / "public-verified.json"
    if not verified.is_file():
        raise FileNotFoundError("Strict public catalog must be generated before deployment")
    catalog = json.loads(verified.read_text(encoding="utf-8"))["records"]
    drafts = json.loads((ROOT / "data" / "curated-60-ocr-drafts.json").read_text(encoding="utf-8"))["records"]
    checks = json.loads((ROOT / "audit" / "curated-60-source-collation.json").read_text(encoding="utf-8"))["checks"]
    by_id = {r["id"]:r for r in drafts}
    verified_ids = {r["id"] for r in checks if r["status"] == "source_text_exactly_matched_review_needed"}
    if len(catalog) != 57 or len(drafts) != 57 or set(by_id) != {r["id"] for r in catalog}:
        raise AssertionError("57 selected metadata and OCR text IDs must match exactly")
    if set(by_id) != verified_ids:
        raise AssertionError("Unmatched source OCR record cannot be published")
    analyses = json.loads((ROOT / "data" / "ai-analysis-57-drafts.json").read_text(encoding="utf-8"))["records"]
    analysis_by_id = {a["id"]: a for a in analyses}
    if len(analyses) != 57 or set(analysis_by_id) != set(by_id):
        raise AssertionError("All 57 articles must have an AI analysis record")
    for analysis in analyses:
        if analysis["review"]["status"] != "pending_human_review":
            raise AssertionError("Never publish unverified analysis as reviewed")
        if analysis.get("summary_ko") and analysis["summary_status"] != "ai_draft_requires_human_review":
            raise AssertionError("Summary draft must be labeled")
        text = by_id[analysis["id"]]["text"]
        for group in ("topic_candidates", "entities", "evidence_passages"):
            for item in analysis[group]:
                quote = item.get("evidence_quote", item.get("quote"))
                if not quote or quote not in text:
                    raise AssertionError(f"Missing source evidence: {analysis['id']} / {group}")
    copy2(verified, OUT / "data" / "public-verified.json")
    for y in range(1901,1907):
        group = [r for r in catalog if r["year"] == y]
        payload = []
        for r in group:
            d = by_id[r["id"]]
            if (d["year"], d["month"], d["title"]) != (r["year"],r["month"],r["title"]):
                raise AssertionError("Title/year/month mismatch for " + r["id"])
            body = d.get("text") or ""
            if len(body) < 100:
                raise AssertionError("Missing OCR body for " + r["id"])
            payload.append({"id":r["id"],"title":r["title"],"year":y,
                "month":r["month"],"printed_page_start":r["printed_page_start"],
                "source_url":d["source_url"],"text":body,
                "transcription_status":"matched_corrected_ocr_not_facsimile_verified",
                "human_review_status":"pending_facsimile_collation"})
        analysis_payload = []
        for r in group:
            a = analysis_by_id[r["id"]]
            analysis_payload.append({
                "id": a["id"], "title": a["title"], "year": a["year"],
                "summary_ko": a["summary_ko"], "summary_status": a["summary_status"],
                "topic_candidates": a["topic_candidates"], "entities": a["entities"],
                "evidence_passages": a["evidence_passages"],
                "review": a["review"], "provenance": a["provenance"],
                "analysis_stage": a["analysis_stage"]
            })
        (OUT / "data" / f"analysis-{y}.json").write_text(
            json.dumps({"year": y, "records": analysis_payload}, ensure_ascii=False), encoding="utf-8")
        (OUT / "data" / f"articles-{y}.json").write_text(
            json.dumps({"year":y,"records":payload},ensure_ascii=False),encoding="utf-8")
    # Verify all relative local asset references in the main archive.
    main_html = (OUT / "index.html").read_text(encoding="utf-8")
    for name in DATA:
        if f"./data/{name}" in main_html and not (OUT / "data" / name).exists():
            raise AssertionError(f"Unresolved data URL: {name}")
    print("Built archive + 57 OCR articles and 57 labeled analysis records in year-sharded files")

if __name__ == "__main__":
    main()

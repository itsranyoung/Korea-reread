#!/usr/bin/env python3
"""Safely recover kr-1901-011 from the March 1901 corrected OCR DOCX.

Run from repository root: python scripts/repair_sul_chong.py
No publication occurs unless strict source-boundary checks pass.
"""
import io
import json
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://anthony.sogang.ac.kr/KoreaReview/KoreaReviewVolume1-03.docx"
ID = "kr-1901-011"
NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def write(path, data):
    (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "KoreaReReadResearch/1.0"})
    with urllib.request.urlopen(req, timeout=75) as response:
        raw = response.read()
    doc = ET.fromstring(zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml"))
    ps = []
    for p in doc.iter(NS + "p"):
        value = " ".join("".join(t.text or "" for t in p.iter(NS + "t")).split())
        if value:
            ps.append(value)
    # The monthly DOCX repeats titles in its TOC; take a body heading only
    # when the following paragraphs demonstrably contain the actual article.
    starts = [i for i, p in enumerate(ps)
              if re.search(r"sul.{0,8}ch.{0,8}ong|father of korean literature", p, re.I)]
    # The March 1901 corrected DOCX contains repeated running headings.
    # Source-boundary audit identifies the article body at index 26,
    # while index 3 is its table of contents entry.
    candidates = [i for i in starts if i > 12]
    if not candidates or candidates[0] != 26:
        raise AssertionError(f"Unexpected article-body heading: {candidates}; all hits {starts}")
    start = candidates[0]
    next_titles = [i for i in range(start+12, len(ps))
                   if re.fullmatch(r"a leaf from my journal\.?|a leaf from my journal\s+.*", ps[i], re.I)]
    if not next_titles:
        raise AssertionError("Cannot find next article boundary")
    end = next_titles[0]
    body = ps[start:end]
    text = "\n\n".join(body)
    if len(text) < 10000 or not re.search(r"GEO\.? HEBER JONES", text, re.I):
        raise AssertionError("Body too short or author signature absent")
    # Extract verbatim article paragraphs as evidence. The full source
    # remains available and the human reviewer must validate the summary.
    substantive = [p for p in body[1:] if len(p) >= 250]
    if len(substantive) < 3:
        raise AssertionError("Insufficient source passages for evidence")
    evidence = substantive[:4]
    summary = ("이 글은 신라의 학자 설총을 한국 문학사의 출발점으로 평가하는 "
               "조지 헤버 존스의 논의를 소개한다. 필자는 설총의 명성을 신라 역사서 저술 전승, "
               "「모란의 비유」, 유교 경전의 신라 구어 해설, 이두와 관련된 공헌을 중심으로 설명한다. "
               "특히 기존 불교계 학문 전통이 있었음을 인정하면서도, 후대에 지배적으로 기억된 "
               "유교적 학문 계보의 출발점으로 설총을 위치시킨다. 이는 1901년 필자의 역사 해석이며 "
               "각 주장에 대한 현대 역사학적 검증을 의미하지 않는다.")

    edits = [
        "data/curated-60-ocr-drafts.json",
        "data/transcriptions/1901-ocr-drafts.json",
    ]
    for path in edits:
        obj = load(path)
        matches = [r for r in obj["records"] if r["id"] == ID]
        if len(matches) != 1:
            raise AssertionError(f"Missing or duplicate ID in {path}")
        r = matches[0]
        r["text"] = text
        r["characters"] = len(text)
        r["body_start_paragraph"] = start
        r["body_end_paragraph_exclusive"] = end
        r["boundary_basis"] = "corrected_monthly_docx_body_heading_to_next_article_heading"
        r["transcription_status"] = "corrected_ocr_body_reextracted_pending_facsimile_review"
        write(path, obj)
    analysis_path = "data/ai-analysis-57-drafts.json"
    a = load(analysis_path)
    record = next(r for r in a["records"] if r["id"] == ID)
    record["summary_ko"] = summary
    record["summary_status"] = "ai_draft_requires_human_review"
    record["analysis_stage"] = "korean_summary_sample_pending_human_review"
    record["evidence_passages"] = [{"quote": p, "status": "source_quote_pending_human_review"} for p in evidence]
    record["topic_candidates"] = []
    record["entities"] = []
    write(analysis_path, a)
    audit = ROOT / "audit" / "sul-chong-source-diagnosis.json"
    audit.write_text(json.dumps({
        "source": SOURCE, "paragraph_count": len(ps), "body_start": start,
        "body_end_exclusive": end, "body_characters": len(text),
        "page_range_from_corrected_volume_pdf": "101-111",
        "next_article": ps[end],
        "review_status": "corrected_ocr_recovered_facsimile_and_human_review_pending"
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recovered {ID}: paragraphs {start}-{end-1}, {len(text)} characters")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Produce a conservative sentence-level evidence audit for all 57 Korean summaries.

IMPORTANT: string occurrence is NOT semantic entailment. This script NEVER awards
"source-supported" or "partly supported" automatically. It finds traceable
candidate excerpts and leaves final classification to a human researcher.
No existing research records are mutated.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audit" / "summary-evidence-57.json"
SOURCE_MAP = {
    "서울": ["seoul"], "도로": ["road", "street"], "궁궐": ["palace"],
    "학교": ["school"], "교육": ["education", "school"], "철도": ["railway"],
    "부산": ["fusan", "pusan"], "일본": ["japan", "japanese"],
    "러시아": ["russia", "russian"], "전쟁": ["war", "battle"],
    "여성": ["woman", "women"], "노비": ["slave", "slavery"],
    "화폐": ["currency", "coin", "money"], "한글": ["alphabet", "character"],
    "문자": ["alphabet", "character", "writing"], "언어": ["language"],
    "목판": ["woodblock", "xylograph"], "인쇄": ["print"],
    "설총": ["sul ch", "sulch"], "유교": ["confucian"],
    "불교": ["buddhis"], "이두": ["i-du"], "모란": ["peony"],
    "장례": ["burial", "funeral"], "무당": ["mudang"],
    "제주": ["quelpart", "cheju"], "제물포": ["chemulpo"],
    "광업": ["mining", "mine"], "금": ["gold"], "병원": ["hospital"],
    "선교": ["mission"], "성경": ["bible", "scripture"],
    "조세": ["tax"], "세금": ["tax"], "이주": ["emigrat", "immigrat"],
    "천도교": ["heavenly way", "chondo"], "역사": ["history"],
    "하와이": ["hawaii"], "인구": ["population"], "종교": ["religion"],
    "상투": ["top-knot"], "속담": ["proverb"], "통신": ["telegraph", "postal"],
    "보부상": ["peddlar", "peddler"], "포르모사": ["formosa", "formosan"],
}
CAUTION = re.compile(r"해석|평가|가설|확정|한계|대표하지|주의|검증|단정|관점|당대|시대|추론|추정|구분|편향")

def sentences(text):
    # Full stops are an adequate delimiter for the current editorial Korean drafts.
    # Keep text intact and verify reconstruction, rather than truncating abbreviations.
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    if " ".join(parts) != " ".join(text.split()):
        raise AssertionError("Sentence segmentation lost source text")
    return parts

def paragraphs(source):
    return [p.strip() for p in re.split(r"\n\s*\n", source) if p.strip()]

def candidates(sentence, text):
    tokens = sorted({token for key, words in SOURCE_MAP.items()
                     if key in sentence for token in words})
    if not tokens:
        return [], []
    matches = []
    for i, para in enumerate(paragraphs(text)):
        hits = [word for word in tokens if word in para.lower()]
        if hits:
            # Exact, bounded original text. A candidate is NOT evidence of the claim.
            matches.append((len(hits), i, para[:700], hits))
    matches.sort(key=lambda x: (-x[0], x[1]))
    return [{"source_paragraph_index": i, "quote": q, "matched_english_terms": hits,
             "quote_is_exact_substring": q in text}
            for _, i, q, hits in matches[:2]], tokens

def main():
    catalog = json.loads((ROOT / "data/public-verified.json").read_text(encoding="utf8"))["records"]
    raw = json.loads((ROOT / "data/curated-60-ocr-drafts.json").read_text(encoding="utf8"))["records"]
    analyses = json.loads((ROOT / "data/ai-analysis-57-drafts.json").read_text(encoding="utf8"))["records"]
    ids = [x["id"] for x in catalog]
    if len(ids) != len(set(ids)) or len(ids) != 57:
        raise AssertionError("Selected catalog must contain exactly 57 unique IDs")
    if {x["id"] for x in raw} != set(ids) or {x["id"] for x in analyses} != set(ids):
        raise AssertionError("OCR and analysis ID sets differ from the locked catalog")
    raw_by = {x["id"]: x for x in raw}
    ai_by = {x["id"]: x for x in analyses}
    out = []
    counts = Counter()
    for article in catalog:
        aid = article["id"]
        source = raw_by[aid]["text"]
        analysis = ai_by[aid]
        summary = analysis["summary_ko"]
        if not summary or not source:
            raise AssertionError("Missing article source or Korean summary: " + aid)
        rows = []
        for index, sentence in enumerate(sentences(summary), 1):
            found, terms = candidates(sentence, source)
            caution = bool(CAUTION.search(sentence))
            # This is a triage category, NOT a claim about historical truth.
            triage = "해석상 주의 필요" if caution else "근거 불충분"
            rows.append({
                "sentence_id": aid + "-s" + str(index).zfill(2),
                "sentence_ko": sentence,
                "provisional_classification": triage,
                "classification_basis": ("interpretive_or_qualifying_language"
                                         if caution else "no_sentence_level_semantic_verification"),
                "semantic_verification": "not_performed",
                "manual_classification": None,
                "candidate_excerpts": found,
                "matched_dictionary_terms": terms,
                "reviewer": None, "review_notes": None,
            })
            counts[triage] += 1
        out.append({"id": aid, "year": article["year"], "title": article["title"],
                    "source_url": raw_by[aid]["source_url"],
                    "summary_status": analysis["summary_status"],
                    "human_review_status": "pending_human_review",
                    "summary_sentences": rows})
    output = {
        "schema_version": "1.0.0", "scope": "exactly_57_existing_selected_articles",
        "method": "deterministic_Korean_sentence_segmentation_and_transparent_bilingual_anchor_lookup",
        "limitations": [
            "Candidate quotations are source-exact excerpts, not proof of Korean claim entailment.",
            "Dictionary matching may miss evidence, conflate meanings, or retrieve irrelevant passages.",
            "Provisional '근거 불충분' means NOT YET semantically verified, not that the article disproves the claim.",
            "Provisional '해석상 주의 필요' is linguistic triage, not an identified factual error.",
            "Only human reviewers may assign final four-way evidence categories.",
            "OCR matched to corrected DOCX is not independently facsimile-verified.",
        ],
        "allowed_manual_categories": ["원문 근거 있음", "부분적으로 뒷받침됨", "근거 불충분", "해석상 주의 필요"],
        "article_count": len(out), "sentence_count": sum(len(x["summary_sentences"]) for x in out),
        "provisional_counts": dict(counts), "records": out,
    }
    for record in out:
        source = raw_by[record["id"]]["text"]
        for row in record["summary_sentences"]:
            if any(x["quote"] not in source for x in row["candidate_excerpts"]):
                raise AssertionError("Fabricated or changed source quote")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps({"articles": output["article_count"], "sentences": output["sentence_count"],
                      "triage": output["provisional_counts"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()

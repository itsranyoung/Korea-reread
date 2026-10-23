#!/usr/bin/env python3
"""KOREA RE:READ 1901 research pipeline (review-first).

Usage:
  python scripts/process_1901.py --input source_text.txt --record-id kr-1901-001 --output reviews/1901-001-draft.json

Pass ONLY the text of ONE manually delimited article, copied and checked against
the credited source. Output is an unverified draft, never a reviewed edition.
Optional: pip install spacy && python -m spacy download en_core_web_sm
"""
import argparse, json, re
from pathlib import Path
from collections import Counter

def entities(text):
    """spaCy suggestions only; can confuse historical romanization."""
    try:
        import spacy
        nlp=spacy.load("en_core_web_sm")
        d=nlp(text[:800000])
        labels={"PERSON":"persons","GPE":"places","LOC":"places","ORG":"organizations"}
        found={"persons":[],"places":[],"organizations":[]}
        for x in d.ents:
            field=labels.get(x.label_)
            if field and x.text not in found[field]:
                found[field].append(x.text)
        return found, "spacy_unverified"
    except (ImportError, OSError):
        return {"persons":[],"places":[],"organizations":[]}, "not_processed_missing_spacy_model"

def candidate_keywords(text):
    stop=set("about after again also among because been being before could every first from have into korea korean more most other over shall some such than that their there these they this those through under until upon very were what when where which while with would".split())
    words=[x.lower() for x in re.findall(r"[A-Za-z][A-Za-z'-]{3,}",text)]
    return [w for w,_ in Counter(w for w in words if w not in stop).most_common(12)]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--record-id",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    data=json.loads(Path("data/1901.json").read_text(encoding="utf-8"))
    selected=next((r for r in data["records"] if r["id"]==args.record_id),None)
    if not selected: parser.error("Unknown record ID")
    text=Path(args.input).read_text(encoding="utf-8").strip()
    if len(text)<30: parser.error("Text is too short for an article transcription")
    tags,tag_status=entities(text)
    output={
      "id": selected["id"],"title":selected["title"],"source_url":selected["source_url"],
      "article_text":text,"transcription_status":"source_text_imported_needs_original_scan_review",
      "entities":tags,"entity_status":tag_status,
      "keyword_candidates":candidate_keywords(text),
      "keyword_status":"frequency_suggestions_unreviewed",
      "summary_ko":None,"summary_status":"not_processed",
      "metadata":{key:selected.get(key) for key in ("year","month","volume","issue","printed_page_start")},
      "human_review_status":"pending",
      "notes":"Check article boundaries, footnotes, OCR spelling, historical names and page numbers against original scans. No AI language model has generated a summary."
    }
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Wrote UNVERIFIED draft:",target)
if __name__=="__main__":main()

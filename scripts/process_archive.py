#!/usr/bin/env python3
"""KOREA RE:READ: provenance-aware multi-year ingestion and draft NLP.

Input: a JSON file containing an array named "articles". Each article must
include year, month, title, text, source_url, and source_page.
DO NOT feed whole issues as one article: article boundaries require verification.

Usage: python scripts/process_archive.py articles-input.json data/articles-draft.json
Optional local NER: pip install spacy; python -m spacy download en_core_web_sm
Summaries are intentionally null until generated and source-verified.
"""
import json,sys,re,hashlib
from pathlib import Path
from collections import Counter

def ner(text):
    labels={"PERSON":"persons","GPE":"places","LOC":"places","ORG":"organizations"}
    results={"persons":[],"places":[],"organizations":[]}
    try:
        import spacy
        nlp=spacy.load("en_core_web_sm")
    except (ImportError,OSError):
        return results,"not_processed_model_unavailable"
    for chunk in [text[i:i+25000] for i in range(0,len(text),25000)]:
        for entity in nlp(chunk).ents:
            key=labels.get(entity.label_)
            if key and entity.text not in results[key]:
                results[key].append(entity.text)
    return results,"unreviewed_machine_candidates"

def keywords(text):
    stop=set("about after again along also although among because before been being between could during every first from have into just korea korean many might more most other over same should since some such than that their them there these they this those through under until very were what when where which while with would your".split())
    words=re.findall(r"[a-z][a-z'-]{3,}",text.lower())
    return [w for w,_ in Counter(w for w in words if w not in stop).most_common(12)]

def process(article):
    for field in ["year","month","title","text","source_url","source_page"]:
        if field not in article: raise ValueError("Missing required "+field)
    y,m=int(article["year"]),int(article["month"])
    if y not in range(1901,1907) or m not in range(1,13): raise ValueError("Outside 1901–1906")
    title,text=article["title"].strip(),article["text"].strip()
    if not title or len(text)<30: raise ValueError("Empty title or too-short article")
    tags,state=ner(text)
    record_id="kr-"+str(y)+"-"+hashlib.sha256((str(m)+title+article["source_url"]).encode()).hexdigest()[:10]
    return {"id":record_id,"record_type":"article","title":title,"year":y,"month":m,
      "volume":y-1900,"issue":m,"printed_page_start":article["source_page"],
      "source_url":article["source_url"],"source_transcription":text,
      "transcription_status":"imported_not_scan_verified",
      "persons":tags["persons"],"places":tags["places"],"organizations":tags["organizations"],
      "entity_status":state,"keywords":keywords(text),"keywords_status":"unreviewed_frequency_candidates",
      "summary_ko":None,"summary_status":"not_processed",
      "human_review_status":"pending",
      "provenance_note":"Source text imported by user. OCR/transcription and article boundaries require scan check."}

def main():
    if len(sys.argv)!=3: raise SystemExit("Usage: process_archive.py input.json output.json")
    payload=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    rows=payload.get("articles")
    if not isinstance(rows,list): raise ValueError("Input must have articles array")
    result=[process(row) for row in rows]
    out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"record_count":len(result),"articles":result},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Created",len(result),"UNREVIEWED article drafts at",out)
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Audit printed issue article boundaries against 72 corrected-OCR DOCX sources.

Research-only outputs: audit/issue-boundaries/*.json, audit/issue-boundaries/summary.json.
Does not alter public article catalogs or claim a heading is an article without review.
Uses the source's original, explicitly separate table-of-contents paragraphs where
possible; title matching in the body is only corroboration.

Usage: python scripts/audit_article_boundaries.py
"""
import collections
import io
import json
import re
import time
import unicodedata
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE="https://anthony.sogang.ac.kr/KoreaReview/"
NS="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
OUT=ROOT/"audit/issue-boundaries"
OUT.mkdir(parents=True,exist_ok=True)
MONTHS="January February March April May June July August September October November December".split()
TOC_HINT=re.compile(r"(contents|table of contents|vol(?:ume)?\s*[ivx\d]+|no\.?\s*\d+)",re.I)
PAGE_MARKER=re.compile(r"(?:\[page\s*(\d{1,4})\]|\bpage\s*(\d{1,4})\b)",re.I)
END_PAGE=re.compile(r"^(.*?)(?:\s+|\.{2,})(\d{1,3})\s*\.?$")
JUNK=re.compile(r"^(?:the korea review|contents|page|news calendar|editorial comment|history of korea)$",re.I)

def norm(t):
    t=unicodedata.normalize("NFKC",t).replace("¡¯","'").replace("¡®","'")
    return re.sub(r"[^a-z0-9]+"," ",t.casefold()).strip()

def get_month(year,month):
    url=BASE+f"KoreaReviewVolume{year-1900}-{month:02d}.docx"
    req=urllib.request.Request(url,headers={"User-Agent":"KoreaReReadResearchAudit/1.0"})
    with urllib.request.urlopen(req,timeout=85) as response: raw=response.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        xml=ET.fromstring(archive.read("word/document.xml"))
    rows=[]
    for p in xml.iter(NS+"p"):
        text=" ".join("".join(n.text or "" for n in p.iter(NS+"t")).split())
        if not text:continue
        ppr=p.find(NS+"pPr")
        st=ppr.find(NS+"pStyle") if ppr is not None else None
        rows.append({"text":text,"style":st.attrib.get(NS+"val","") if st is not None else ""})
    return rows,url

def indexed_year(year):
    p=ROOT/"data"/f"{year}.json"
    if not p.is_file():return []
    rows=json.loads(p.read_text(encoding="utf8")).get("records",[])
    return [r for r in rows if isinstance(r.get("month"),int)]

def inspect(year,month,records):
    rows,url=get_month(year,month)
    # Title paragraphs are commonly found in early issue's contents and repeated
    # within the body. Preserve both as candidates; never merge based on title alone.
    ntext=[norm(r["text"]) for r in rows]
    nrecords=[r for r in records if r.get("month")==month]
    matched=[];unmatched=[]
    for r in nrecords:
        q=norm(r["title"])
        hits=[{"paragraph_index":i,"style":rows[i]["style"],"text":rows[i]["text"]}
              for i,t in enumerate(ntext) if t==q and q]
        evidence={"id":r["id"],"title":r["title"],
                  "catalog_page":r.get("printed_page_start"),
                  "heading_evidence":hits[:20],
                  "heading_count":len(hits),
                  "status":"standalone_heading_match_unverified" if hits else "no_exact_heading_match"}
        (matched if hits else unmatched).append(evidence)
    # Potential additional headings: short paragraphs in an early contents zone
    # with table-of-contents styled short lines. Not a fully verified missing list.
    candidates=[]
    for i,r in enumerate(rows[:min(len(rows),110)]):
        t=r["text"]
        if len(t)<5 or len(t)>110 or not re.search("[A-Za-z]",t):continue
        if TOC_HINT.search(t) or JUNK.fullmatch(norm(t)):continue
        # Keep only headings that also occur separately later in document.
        indices=[j for j in range(i+1,len(rows)) if ntext[j]==ntext[i]]
        if not indices:continue
        if norm(t) in {norm(z["title"]) for z in nrecords}:continue
        candidates.append({"title_candidate":t,"toc_paragraph_index":i,
                           "body_paragraph_indices":indices[:12],
                           "source":"repeated_standalone_paragraph",
                           "status":"possible_unlisted_heading_not_verified"})
    dedup={}
    for c in candidates:dedup.setdefault(norm(c["title_candidate"]),c)
    return {"year":year,"month":month,"source_url":url,
       "docx_paragraphs":len(rows),"catalog_records":len(nrecords),
       "matched_count":len(matched),"unmatched_count":len(unmatched),
       "matches":matched,"no_exact_heading_matches":unmatched,
       "possible_unlisted_headings":list(dedup.values()),
       "note":"Not proof of complete article bibliography or exact boundaries. Check original printed TOC, page starts, serials and section headings."}

def main():
    totals=collections.Counter()
    summary={"scope":"72 monthly issues 1901–1906",
             "verification_level":"automated_heading_correspondence_only",
             "article_completeness_confirmed":False,
             "body_boundaries_confirmed":False,
             "months":{},"download_errors":[]}
    for year in range(1901,1907):
        records=indexed_year(year)
        summary["months"][str(year)]={}
        for month in range(1,13):
            try:
                result=inspect(year,month,records)
                (OUT/f"{year}-{month:02d}.json").write_text(
                    json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
                compact={k:result[k] for k in ("catalog_records","matched_count",
                         "unmatched_count","docx_paragraphs","source_url")}
                compact["possible_unlisted_count"]=len(result["possible_unlisted_headings"])
                summary["months"][str(year)][str(month)]=compact
                totals.update({"months_read":1,"matched":result["matched_count"],
                    "unmatched":result["unmatched_count"],
                    "potential_unlisted":compact["possible_unlisted_count"]})
                print(f"{year}-{month:02d}: matched {compact['matched_count']}, "
                      f"unmatched {compact['unmatched_count']}, possible unlisted {compact['possible_unlisted_count']}",flush=True)
            except Exception as exc:
                error={"year":year,"month":month,"error":str(exc)}
                summary["download_errors"].append(error)
                print("ERROR",error,flush=True)
            time.sleep(.1)
    summary["totals"]=dict(totals)
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf8")
if __name__=="__main__":main()

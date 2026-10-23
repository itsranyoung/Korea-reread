#!/usr/bin/env python3
"""Harvest printed tables of contents for 1902, 1903 and 1905.

Run on a machine with network access:
    pip install requests beautifulsoup4 lxml
    python scripts/harvest_toc.py

The old ContentsXX.htm may have invalid Unicode declarations; requests.content
+ charset_normalizer and BeautifulSoup avoid browsers' decode failure.
Do not silently invent missing start pages or article titles.
"""
from __future__ import annotations
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup
BASE="https://anthony.sogang.ac.kr/KoreaReview/"
YEARS={1902:2,1903:3,1905:5}
MONTHS="January February March April May June July August September October November December".split()
ROOT=Path("data")
OUT=Path("audit");OUT.mkdir(parents=True,exist_ok=True)
HEADERS={"User-Agent":"KoreaReReadMetadataAudit/1.0 (historical source research)"}
def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=60)
    r.raise_for_status()
    # Older pages include Windows-1252, malformed tags or mixed encodings.
    for encoding in ["utf-8-sig", "windows-1252"]:
        value=r.content.decode(encoding,errors="replace")
        if value.count("\ufffd")<=1: return value
    return r.content.decode("windows-1252",errors="replace")
def get_lines(html):
    soup=BeautifulSoup(html,"lxml")
    for tag in soup(["script","style"]): tag.decompose()
    lines=[re.sub(r"\s+"," ",x).strip() for x in soup.get_text("\n").splitlines()]
    return [x for x in lines if x]
def parse(year,lines):
    """Extract page-referenced ANNUAL INDEX headings, not authenticated article titles.

    The Contents02/03/05 files are alphabetical indexes, not monthly ToCs.
    Publication month is deliberately left null pending issue verification.
    """
    results=[];rejected=[];buffer=[]
    ignored=re.compile(r"^(?:The Korea Review|Index|Ind|ex|Contents|Volume\s+\d+|19\d{2}|unless otherwise indicated|\*Articles by the Editor)$",re.I)
    ending=re.compile(r"^(.*?)(?:\s+|[,;.]{1,3}\s*)(\d{1,3}(?:\s*[,;]\s*\d{1,3})*)\s*$")
    barepages=re.compile(r"^\d{1,3}(?:\s*[,;]\s*\d{1,3})*$")
    def emit(title,pages):
        title=" ".join(title).strip(" .,;")
        title=title.replace("¡¯","'").replace("¡®","'")
        title=re.sub(r"\s+"," ",title)
        if len(title)<4 or len(title)>150 or not re.search("[A-Za-z]",title):return
        numbers=[int(p) for p in re.findall(r"\d{1,3}",pages)]
        for n in numbers:
            if n<1 or n>600:continue
            key=(title.casefold(),n)
            if any((r["title"].casefold(),r["printed_page_start"])==key for r in results):continue
            results.append({"id":f"kr-{year}-idx-{len(results)+1:03d}",
             "record_type":"annual_index_heading_candidate","title":title,
             "year":year,"month":None,"month_status":"not_verified",
             "volume":year-1900,"issue":None,
             "printed_page_start":n,
             "source_url":BASE+f"Contents{year-1900:02d}.htm",
             "metadata_status":"annual_index_machine_extracted_unreviewed_not_confirmed_article",
             "transcription_status":"not_processed",
             "entity_status":"not_processed","summary_status":"not_processed",
             "human_review_status":"pending"})
    for line in lines:
        line=line.strip()
        if ignored.fullmatch(line) or line.lower() in {"volume 2,","volume 3, 1903.","volume 5,"}:
            buffer=[];continue
        if line.isdigit() and len(line)==4 and 1900<=int(line)<=1910:
            buffer=[];continue
        match=ending.match(line)
        if match and re.search("[A-Za-z]",match.group(1)):
            # Joined line may be an actual heading or the end of split heading.
            emit(buffer+[match.group(1)],match.group(2));buffer=[];continue
        if barepages.fullmatch(line):
            if buffer:emit(buffer,line)
            buffer=[];continue
        # Index may contain a numeric continuation without a title.
        if line.startswith(","):continue
        if re.search(r"[A-Za-z]",line):
            buffer.append(line)
            if len(buffer)>5:buffer=buffer[-3:]
    return results
def main():
    audit={}
    for year,n in YEARS.items():
        url=BASE+f"Contents{n:02d}.htm"
        try:
            html=fetch(url)
            lines=get_lines(html)
            (OUT/f"toc-{year}-extracted-lines.txt").write_text("\n".join(lines),encoding="utf-8")
            records=parse(year,lines)
            audit[str(year)]={"url":url,"text_lines":len(lines),"record_count":len(records),
                "month_counts":{m:sum(x["month"]==i for x in records) for i,m in enumerate(MONTHS,1)},
                "status":"annual_index_headings_unreviewed",
                "warning":"Source is an alphabetical INDEX (not a monthly TOC). These are index-heading candidates, not verified article titles or issue assignments."}
            # Do not publish speculative or nearly empty results as complete.
            (ROOT/f"{year}-draft.json").write_text(json.dumps({"year":year,
                "source_url":url,"status":"annual_index_candidates_not_for_public_article_gallery","records":records},ensure_ascii=False,indent=2),encoding="utf-8")
            print(year,len(lines),"lines,",len(records),"draft entries")
        except Exception as exc:
            audit[str(year)]={"url":url,"status":"download_failed","error":str(exc)}
            print(year,"FAILED:",exc)
    (OUT/"harvest-report.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
if __name__=="__main__":main()

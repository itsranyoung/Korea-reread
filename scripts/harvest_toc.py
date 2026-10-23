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
    """Conservatively recognize nearby title and terminal page numbers.

    Records with ambiguous date / pages are quarantined in audit report.
    """
    results=[];rejected=[];month=None;pending=[]
    page_line=re.compile(r"^(?P<title>.*?[A-Za-z][^0-9]*?)\s*(?:\.{2,}|\s{2,})\s*(?P<page>\d{1,4})\s*$")
    # Annual ToCs frequently use a line-by-line table, sometimes with a
    # standalone page number next to the corresponding title.
    def add(title,page,m,method):
        title=re.sub(r"\s+"," ",title).strip(" .\u00a0")
        if not title or len(title)<3 or not re.search("[A-Za-z]",title):return
        if page<1 or page>1500 or m not in range(1,13):return
        key=(m,title.casefold(),page)
        if any((x["month"],x["title"].casefold(),x["printed_page_start"])==key for x in results):return
        results.append({"id":f"kr-{year}-{len(results)+1:03d}","record_type":"article_toc_entry",
            "title":title,"year":year,"month":m,"issue":m,"volume":year-1900,
            "printed_page_start":page,"printed_page_end":None,
            "source_url":BASE+f"Contents{year-1900:02d}.htm",
            "metadata_status":"machine_extracted_toc_requires_human_verification",
            "extraction_method":method,
            "original_text":None,"transcription_status":"not_processed",
            "persons":[],"places":[],"organizations":[],"entity_status":"not_processed",
            "summary_ko":None,"summary_status":"not_processed","human_review_status":"pending"})
    for i,line in enumerate(lines):
        lowered=line.lower()
        match_month=next((n for n,m in enumerate(MONTHS,1) if re.fullmatch(r"(?:contents (?:for|of) )?"+m.lower()+r"(?:[., ]+\d{4})?[.:]?",lowered)),None)
        if match_month:
            month=match_month;pending=[];continue
        # Only accept page/titles within explicit month sections.
        if not month:continue
        joined=page_line.match(line)
        if joined:
            add(joined.group("title"),int(joined.group("page")),month,"inline_month_section")
            pending=[];continue
        if re.fullmatch(r"\d{1,4}",line) and pending:
            add(pending[-1],int(line),month,"adjacent_line_month_section")
            pending=[];continue
        if len(line)>2 and re.search(r"[A-Za-z]",line) and not re.fullmatch(r"contents|page|articles",lowered):
            pending.append(line)
            if len(pending)>2:pending.pop(0)
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
                "status":"unreviewed_machine_parse",
                "warning":"No article row has been individually confirmed against original printed issues"}
            # Do not publish speculative or nearly empty results as complete.
            (ROOT/f"{year}-draft.json").write_text(json.dumps({"year":year,
                "source_url":url,"status":"unreviewed_draft","records":records},ensure_ascii=False,indent=2),encoding="utf-8")
            print(year,len(lines),"lines,",len(records),"draft entries")
        except Exception as exc:
            audit[str(year)]={"url":url,"status":"download_failed","error":str(exc)}
            print(year,"FAILED:",exc)
    (OUT/"harvest-report.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
if __name__=="__main__":main()

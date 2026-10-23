#!/usr/bin/env python3
"""Acquire source HTML and split by PRINTED page markers, NOT by article.

Requires: Python 3.10+, beautifulsoup4 (pip install beautifulsoup4)
Run: python scripts/ingest_volumes.py --years 1901 1902
     python scripts/ingest_volumes.py --years 1901 1902 1903 1904 1905 1906

This writes files to imports/ (gitignored by recommendation). Copyright
and reuse requirements must be checked before public redistribution.
Source HTML is corrected OCR, not a critical edition; manual checks required.
"""
from __future__ import annotations
import argparse, json, re, time, urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

BASE = "https://anthony.sogang.ac.kr/KoreaReview/"
VOLUMES = {
    1901: "KoreaReviewFullTextVolumeOne.html",
    1902: "KoreaReviewFullTextVolumeTwo.html",
    1903: "KoreaReviewFullTextVolumeThree.html",
    1904: "KoreaReviewFullTextVolumeFour.html",
    1905: "KoreaReviewFullTextVolumeFive.html",
    1906: "KoreaReviewVolume6FullText.html",
}
HEADERS = {"User-Agent":"KoreaReReadAcademicPrototype/0.1 (source-attributed research)"}
PAGE_PATTERN = re.compile(r"\[(?:page|Page)\s*(\d{1,4})\]")
def retrieve(url:str)->str:
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=75) as resp:
        charset=resp.headers.get_content_charset() or "utf-8"
        raw=resp.read()
    return raw.decode(charset,errors="replace")
def ingest(year:int, root:Path):
    url=BASE+VOLUMES[year]
    html=retrieve(url)
    soup=BeautifulSoup(html,"html.parser")
    for unwanted in soup(["script","style","noscript"]): unwanted.decompose()
    # Keep explicit visible page markers. HTML conversion may collapse
    # magazine layout; all page boundaries require manual inspection.
    body=soup.body or soup
    text=body.get_text(separator=" ",strip=True)
    text=re.sub(r"\s+"," ",text)
    matches=list(PAGE_PATTERN.finditer(text))
    pages=[]
    for index,match in enumerate(matches):
        page=int(match.group(1))
        end=matches[index+1].start() if index+1<len(matches) else len(text)
        segment=text[match.end():end].strip()
        pages.append({
            "page_marker":page, "text":segment,
            "source_url":url,"year":year,
            "status":"corrected_ocr_page_unverified",
            "article_boundary_verified":False
        })
    warnings=[]
    if len(matches)<10:
        warnings.append("Few page markers found; review source HTML layout.")
    prior=-1
    for item in pages:
        if item["page_marker"] <= prior:
            warnings.append(f"Non-monotonic or duplicate page marker: {item['page_marker']}")
        prior=item["page_marker"]
    directory=root/str(year);directory.mkdir(parents=True,exist_ok=True)
    # Raw original saved locally for audit. Do not publish without licensing review.
    (directory/"source.html").write_text(html,encoding="utf-8")
    (directory/"pages.json").write_text(json.dumps({
        "year":year,"source_url":url,
        "record_type":"printed_page_blocks_not_articles",
        "page_count":len(pages),"warnings":warnings,"pages":pages
    },ensure_ascii=False,indent=2),encoding="utf-8")
    (directory/"manifest.json").write_text(json.dumps({
        "year":year,"source_url":url,"page_blocks":len(pages),
        "source_characters":len(text),"warnings":warnings,
        "article_segmentation_status":"not_started",
        "human_verification_status":"pending"
    },ensure_ascii=False,indent=2),encoding="utf-8")
    return len(pages),warnings
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--years",nargs="+",type=int,default=[1901])
    p.add_argument("--output",default="imports")
    a=p.parse_args()
    root=Path(a.output)
    for year in a.years:
        if year not in VOLUMES: p.error("Year must be 1901 through 1906")
        try:
            count,warnings=ingest(year,root)
            print(f"{year}: {count} OCR page blocks saved; {len(warnings)} warnings")
        except Exception as exc:
            print(f"{year}: FAILED ({exc})")
        time.sleep(1)
if __name__=="__main__":main()

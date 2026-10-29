#!/usr/bin/env python3
"""1905 catalog verification: compare annual-index candidates to each monthly DOCX.

Extract paragraph text and styles, scan title candidates, and record evidence.
Publish only records whose month is uniquely supported by a title-sized paragraph.
These remain MACHINE-VERIFIED CANDIDATES pending a printed-issue page check.
"""
import io, json, re, time, unicodedata, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request, urlopen
from collections import defaultdict

REPO=Path(__file__).resolve().parents[1]
INDEX=REPO/"data/1905-draft.json"
OUT=REPO/"data/1905.json"
AUDIT=REPO/"audit/1905-month-verification.json"
BASE="https://anthony.sogang.ac.kr/KoreaReview/"
NS="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
STOP={"news calendar","editorial comment","history of korea","correspondence"}
def norm(v):
    v=unicodedata.normalize("NFKC",v).replace("¡¯","'").replace("¡®","'")
    return re.sub(r"[^a-z0-9]+"," ",v.casefold()).strip()
def clean(v):
    return re.sub(r"\s+"," ",v).strip()
def fetch(month):
    url=BASE+f"KoreaReviewVolume5-{month:02d}.docx"
    with urlopen(Request(url,headers={"User-Agent":"KoreaReReadSourceAudit/1.0"}),timeout=85) as r:
        raw=r.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        document=ET.fromstring(z.read("word/document.xml"))
    result=[]
    for p in document.iter(NS+"p"):
        text=clean("".join(t.text or "" for t in p.iter(NS+"t")))
        if not text:continue
        ppr=p.find(NS+"pPr")
        style=ppr.find(NS+"pStyle") if ppr is not None else None
        result.append({"text":text,"style":style.attrib.get(NS+"val","") if style is not None else ""})
    return result,url

def main():
    candidates=json.loads(INDEX.read_text(encoding="utf8"))["records"]
    indexed=defaultdict(list)
    for item in candidates:
        title=norm(item["title"])
        if len(title)>=9 and title not in STOP:indexed[title].append(item)
    month_sources={};errors=[]
    for month in range(1,13):
        try:
            paras,url=fetch(month)
            month_sources[month]={"paragraphs":paras,"url":url}
            print(f"1905-{month:02d}: {len(paras)} paragraphs")
        except Exception as e:
            errors.append({"month":month,"error":str(e)})
            print(f"1905-{month:02d}: ERROR {e}")
        time.sleep(.3)
    occurrences=defaultdict(list)
    for month,source in month_sources.items():
        for idx,para in enumerate(source["paragraphs"]):
            title=norm(para["text"])
            # Only standalone title-like lines; not matches buried in article body.
            if title in indexed and len(para["text"])<135:
                occurrences[title].append({"month":month,"paragraph":idx,"style":para["style"],"raw":para["text"]})
    published=[];ambiguous=[];unmatched=[];resolved_by_page=[]
    if len(month_sources)!=12:
        raise RuntimeError("All 12 original monthly DOCX sources must be available before modifying published catalog")
    for title,items in indexed.items():
        hits=occurrences.get(title,[])
        months=sorted(set(h["month"] for h in hits))
        for item in items:
            # Index gives printed starting pages: Vol. 2 uses 48-page monthly issues.
            # Only accept a page-derived month if that month also contains the heading.
            pg=item.get("printed_page_start")
            page_month=(int(pg)-1)//48+1 if isinstance(pg,int) and 1<=pg<=576 else None
            selected_month=(months[0] if len(months)==1 else page_month if page_month in months else None)
            if selected_month is not None:
                mo=selected_month
                r={**item,"id":f"kr-1905-{len(published)+1:04d}","record_type":"annual_index_title_month_candidate",
                   "month":mo,"issue":mo,"source_url":month_sources[mo]["url"],
                   "annual_index_url":item["source_url"],"source_month_matches":hits,
                   "month_status":("unique_standalone_title_line_machine_match" if len(months)==1 else "page_and_monthly_docx_correlated_candidate"),
                   "metadata_status":"monthly_docx_title_match_requires_human_article_and_page_verification",
                   "source_page_verified":False,
                   "title_verified_against_print_scan":False}
                published.append(r)
                if len(months)>1: resolved_by_page.append({"title":item["title"],"page":pg,"selected_month":mo,"possible_months":months})
            elif len(months)>1:
                ambiguous.append({"title":item["title"],"indexed_page":item["printed_page_start"],"matches":hits})
            else:
                unmatched.append({"title":item["title"],"indexed_page":item["printed_page_start"]})
    published.sort(key=lambda r:(r["month"],r["printed_page_start"],r["title"].casefold()))
    for i,r in enumerate(published,1):r["id"]=f"kr-1905-{i:04d}"
    OUT.write_text(json.dumps({
        "year":1905,"status":"provisional_monthly_article_candidates_not_human_verified",
        "warning":"Annual alphabetical index contains subject headings, repeats, and continuation references. This is not a complete article bibliography.",
        "method":"Unique standalone-paragraph normalized title match in original monthly DOCX; excludes repeat section headings.",
        "source_index_url":BASE+"Contents05.htm","records":published
    },ensure_ascii=False,indent=2),encoding="utf8")
    AUDIT.parent.mkdir(exist_ok=True)
    AUDIT.write_text(json.dumps({"year":1905,"source_errors":errors,
        "processed_months":list(month_sources),"published_candidates":len(published),
        "month_counts":{str(m):sum(r["month"]==m for r in published) for m in range(1,13)},
        "resolved_by_page_and_source":resolved_by_page,
        "ambiguous":ambiguous,"unmatched":unmatched,
        "warning":"False title matches are possible; publication pending editorial review."},
        ensure_ascii=False,indent=2),encoding="utf8")
    print("Result:",len(published),"month candidates,",len(resolved_by_page),"resolved using page+source,",len(ambiguous),"ambiguous,",len(unmatched),"unmatched")
if __name__=="__main__":main()

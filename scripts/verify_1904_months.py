#!/usr/bin/env python3
"""Cross-check provisional 1904 year/page-month placements against monthly DOCX.

Exact separate-paragraph title matches are RESEARCH LEADS, not verification of
article boundaries or printed page numbers. Produces audit only.
"""
import io,json,re,zipfile,requests,xml.etree.ElementTree as ET
from pathlib import Path
BASE="https://anthony.sogang.ac.kr/KoreaReview/KoreaReviewVolume4-"
DATA=Path("data/1904.json");OUT=Path("audit/1904-month-check.json")
NS="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
def norm(t):return re.sub(r"[^a-z0-9]+"," ",t.casefold()).strip()
def paragraphs(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:xml=z.read("word/document.xml")
    tree=ET.fromstring(xml)
    return ["".join(n.text or "" for n in p.iter(NS+"t")).strip() for p in tree.iter(NS+"p")]
def main():
    rows=json.loads(DATA.read_text(encoding="utf-8"))["records"]
    source_warnings=[];matches={r["id"]:[] for r in rows}
    for month in range(1,13):
        url=BASE+f"{month:02d}.docx"
        try:
            r=requests.get(url,timeout=65);r.raise_for_status()
            para=paragraphs(r.content)
            normparas=set(norm(p) for p in para if 4<len(p)<180)
            for row in rows:
                t=norm(row["title"])
                if len(t)>=8 and t in normparas:
                    matches[row["id"]].append(month)
            print("1904",month,"downloaded",len(para),"paragraphs")
        except Exception as exc:
            source_warnings.append({"month":month,"reason":str(exc)})
    output={"year":1904,"method":"exact normalized paragraph match to monthly DOCX source text",
      "limitations":"Full body phrases can also match; no page and article boundary verification. Never treat as human-confirmed month.",
      "source_warnings":source_warnings,
      "entries":[{
        "id":row["id"],"title":row["title"],"indexed_page":row["printed_page_start"],
        "current_provisional_month":row["month"],
        "source_paragraph_matches":matches[row["id"]],
        "status":("same_month_candidate" if matches[row["id"]]==[row["month"]] else
                  "conflicting_month_candidate" if matches[row["id"]] else "no_exact_heading_match")
      } for row in rows]}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
if __name__=="__main__":main()

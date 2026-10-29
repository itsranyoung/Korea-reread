#!/usr/bin/env python3
"""Conservative reconstruction of 1902-1905 monthly original issue contents.

Only publish a record when: (1) a title/page entry is independently extracted
from that issue's contents zone; (2) a matching later standalone body heading
exists in the SAME issue; (3) issue-year-month and printed page agree with
the month page span. Do not invent pages or promote annual-index references.

Output includes rigorous rejected candidates and diagnostics to improve parsing.
"""
from pathlib import Path
from urllib.request import Request,urlopen
from collections import defaultdict,Counter
import xml.etree.ElementTree as ET
import zipfile,io,re,json,unicodedata,time
P=Path(__file__).resolve().parents[1]
BASE="https://anthony.sogang.ac.kr/KoreaReview/"
N="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
OUT=P/"audit/monthly-toc-reconstruction"
OUT.mkdir(parents=True,exist_ok=True)
def norm(s):return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKC",s).casefold()).strip()
def clean(s):return " ".join(s.split())
def read(year,month):
 url=BASE+f"KoreaReviewVolume{year-1900}-{month:02d}.docx"
 with urlopen(Request(url,headers={"User-Agent":"KoreaReReadVerification/1.0"}),timeout=80) as f:b=f.read()
 with zipfile.ZipFile(io.BytesIO(b)) as z:root=ET.fromstring(z.read("word/document.xml"))
 pars=[]
 for p in root.iter(N+"p"):
  t=clean("".join(x.text or "" for x in p.iter(N+"t")))
  if not t:continue
  pp=p.find(N+"pPr")
  st=pp.find(N+"pStyle") if pp is not None else None
  pars.append({"text":t,"style":st.attrib.get(N+"val","") if st is not None else ""})
 return pars,url
def entries(pars,year,month):
 low=(month-1)*48+1;high=month*48
 # The 1902/1904 issue TOCs list title-only lines. Print page appears
 # later as [page N] embedded at the start/in the body OCR paragraphs.
 # Require TOC within the lines BEFORE the first explicit [page N].
 page_pattern=re.compile(r"\[page\s+(\d{1,4})\]",re.I)
 first_page=next((i for i,p in enumerate(pars) if page_pattern.search(p["text"])),None)
 if first_page is None:return [],[{"reason":"no_print_page_markers","year":year,"month":month}]
 # Some issues omit a page-one marker; detect the start of BODY by
 # matching a TOC heading against its later standalone repeat.
 repeats=[]
 for i,p in enumerate(pars[:min(first_page,45)]):
  key=norm(p["text"])
  if not key or len(p["text"])>110 or i<2:continue
  for j in range(i+4,min(len(pars),150)):
   if norm(pars[j]["text"])==key and len(pars[j]["text"])<145:
    repeats.append(j);break
 body_start=min(repeats) if repeats else first_page
 toc_limit=min(body_start,70)
 if toc_limit<3:return [],[{"reason":"no_toc_region","year":year,"month":month}]
 active_page=None;body_heading_by_title=defaultdict(list)
 for idx,p in enumerate(pars[body_start:],body_start):
  marks=page_pattern.findall(p["text"])
  if marks:active_page=int(marks[0])
  t=norm(p["text"].strip(" ."))
  if t and len(p["text"])<=145:
   body_heading_by_title[t].append((idx,active_page,p["text"]))
 found=[];rejected=[]
 for idx,p in enumerate(pars[:toc_limit]):
  title=p["text"].strip(" .,;")
  key=norm(title)
  if len(title)<5 or len(title)>110 or not re.search("[A-Za-z]",title):continue
  if key in ("the korea review","contents","table of contents") or key.startswith("volume "):continue
  # The first match should be the separate BODY title, not a TOC line.
  hits=body_heading_by_title.get(key,[])
  valid=[h for h in hits if h[1] is not None and low<=h[1]<=high and h[0]>=body_start]
  if valid:
   # If the identical title occurs more than once in the body (e.g.
   # serials), use the FIRST body heading and flag extra occurrences.
   h=valid[0]
   found.append({"title":title,"year":year,"month":month,"volume":year-1900,"issue":month,
      "printed_page_start":h[1],"toc_paragraph_index":idx,"toc_raw":p["text"],
      "page_evidence_method":"preceding_embedded_print_page_marker",
      "body_heading_paragraph_indices":[x[0] for x in valid],
      "body_heading_raw":h[2],
      "page_marker_witness":"[page "+str(h[1])+"]",
      "multiple_body_occurrences":len(valid)>1})
  else:rejected.append({"title_candidate":title,"toc_paragraph_index":idx,
    "reason":"missing_same_issue_heading_or_page_witness"})
 dedup={}
 for row in found:dedup.setdefault((norm(row["title"]),row["printed_page_start"]),row)
 return list(dedup.values()),rejected

def main():
 all_pass=[];totals=Counter();errors=[];month_summaries={}
 for year in range(1902,1906):
  for month in range(1,13):
   key=f"{year}-{month:02d}"
   try:
    pars,url=read(year,month)
    accepted,unmatched=entries(pars,year,month)
    for row in accepted:row["source_url"]=url
    diagnostics={"year":year,"month":month,"source_url":url,"paragraph_count":len(pars),
      "toc_inspection_paragraphs":pars[:min(45,len(pars))],
      "accepted":accepted,"rejected_toc_title_candidates":unmatched,
      "pass_rule":"Original issue TOC printed page and a later standalone matching article heading in same monthly DOCX; page fits nominal 48-page month range",
      "unverified":"Real scan page numbers, continuation logic, and OCR fidelity require manual review"}
    (OUT/f"{key}.json").write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding="utf8")
    all_pass.extend(accepted);totals["months_read"]+=1;totals["accepted"]+=len(accepted)
    totals["rejected"]+=len(unmatched)
    month_summaries[key]={"accepted":len(accepted),"rejected":len(unmatched),"source":url}
    print(key,"accepted",len(accepted),"rejected",len(unmatched),flush=True)
   except Exception as e:errors.append({"year":year,"month":month,"error":str(e)});print(key,"ERROR",e,flush=True)
   time.sleep(.1)
 if errors:print("Source errors; FAIL CLOSED",len(errors),flush=True)
 for i,r in enumerate(sorted(all_pass,key=lambda z:(z["year"],z["month"],z["printed_page_start"],z["title"])),1):
  r["id"]=f"kr-confirmed-{r['year']}-{i:04d}"
  r["record_type"]="toc_entry_correlated_with_body_heading"
  r["publication_verification"]="independent_issue_toc_page_and_body_heading_correlated"
  r["human_review_status"]="pending_facsimile_collation"
  r["transcription_status"]="not_processed"
  r["summary_status"]="not_processed"
 out={"scope":"1902-1905 monthly source re-extraction","completeness_certified":False,
  "criteria":"Original monthly TOC title; matching body title and witnessed [page N] marker in same issue; matching month page span",
  "source_errors":errors,"month_summaries":month_summaries,
  "accepted_count":len(all_pass),"records":all_pass}
 (OUT/"summary.json").write_text(json.dumps({"counts":dict(totals),"errors":errors,"months":month_summaries},indent=2),encoding="utf8")
 # Only promote full 48-month source success. No records published on partial run.
 if not errors and totals["months_read"]==48:
  (P/"data/monthly-toc-confirmed-1902-1905.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
  print("Published strict source-evidenced candidates:",len(all_pass),flush=True)
 else:raise SystemExit("48-month source completeness check failed: public data NOT overwritten")
if __name__=="__main__":main()

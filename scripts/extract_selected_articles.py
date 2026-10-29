#!/usr/bin/env python3
"""Extract selected articles from corrected-OCR monthly DOCX sources (1901–1906).

Scope is LOCKED to the 251 records in data/public-verified.json. All extraction
is conservative: body headings must be uniquely aligned, in article order and
within original month; a next heading or printed page end bounds each article.
An ambiguous boundary becomes a rejected draft, never public text.
Original DOCX content is NOT modified. Generated transcriptions are OCR drafts,
not facsimile-certified scholarly transcriptions.
"""
import io,json,re,unicodedata,zipfile,time
import xml.etree.ElementTree as ET
from collections import defaultdict,Counter
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
NS="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
BASE="https://anthony.sogang.ac.kr/KoreaReview/"
PAGE=re.compile(r"\[page\s+(\d{1,4})\]",re.I)
def norm(s):
 return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKC",str(s)).casefold()).strip()
def acquire(year,month):
 url=BASE+f"KoreaReviewVolume{year-1900}-{month:02d}.docx"
 with urlopen(Request(url,headers={"User-Agent":"KoreaReReadOCRResearch/1.0"}),timeout=85) as stream:
  data=stream.read()
 with zipfile.ZipFile(io.BytesIO(data)) as doc:
  root=ET.fromstring(doc.read("word/document.xml"))
 pars=[]
 for p in root.iter(NS+"p"):
  t=" ".join("".join(x.text or "" for x in p.iter(NS+"t")).split())
  if t:pars.append(t)
 return pars,url
def locate(pars,r):
 title=norm(r["title"]);hits=[]
 # Source audit supplies heading offsets with styles; use as hints ONLY.
 for i,t in enumerate(pars):
  if norm(t)==title and len(t)<=145:hits.append(i)
 if not hits:return None,"heading_not_found"
 # TOC normally precedes body; a paragraph after 6+ index paragraphs is not
 # automatically body. Require a later matching occurrence if early TOC exists.
 toc=r.get("toc_paragraph_index")
 if isinstance(toc,int):
  hits=[h for h in hits if h>toc+3]
 elif len(hits)>=2:
  hits=hits[1:]
 if not hits:return None,"body_heading_not_distinguished_from_toc"
 hint=r.get("body_heading_paragraph_indices",[])
 if hint:
  overlap=[h for h in hits if h in hint]
  if overlap:hits=overlap
 if len(hits)!=1:return None,"ambiguous_multiple_body_headings"
 return hits[0],None
def split_month(year,month,selected):
 pars,url=acquire(year,month)
 # Independent content-end guard: no next known heading => cannot confidently
 # establish a complete boundary. The final article can only end at issue end.
 headings=[];issues=[]
 for r in selected:
  pos,err=locate(pars,r)
  if err:issues.append({"id":r["id"],"reason":err});continue
  headings.append((pos,r))
 headings.sort(key=lambda x:x[0])
 if len({i for i,_ in headings})!=len(headings):
  return [],issues+[{"reason":"two_records_same_heading"}]
 output=[]
 for j,(start,r) in enumerate(headings):
  next_start=headings[j+1][0] if j+1<len(headings) else len(pars)
  # The selected list is deliberately a SUBSET of source articles. If it does
  # not contain all original headings, the next selected title is NOT a safe
  # article boundary. Find any short, standalone headings known from the TOC.
  toc_titles=[]
  limit=min(start,65)
  for k in range(2,limit):
   t=paras[k]
   if 5<=len(t)<=120 and re.search("[A-Za-z]",t):
    toc_titles.append(norm(t))
  toc_set=set(toc_titles)
  possible_boundaries=[]
  for k in range(start+1,next_start):
   t=pars[k]
   if len(t)<=145 and norm(t) in toc_set and norm(t)!=norm(r["title"]):
    possible_boundaries.append(k)
  if possible_boundaries:next_start=min(next_start,min(possible_boundaries))
  if next_start<=start+1:
   issues.append({"id":r["id"],"reason":"empty_article_body"});continue
  # If no next source heading and the article ends with remainder of issue,
  # that may include unrelated unlisted articles; reject rather than overcopy.
  if next_start==len(pars):
   issues.append({"id":r["id"],"reason":"unbounded_end_of_issue"});continue
  body=pars[start:next_start]
  text="\n\n".join(body).strip()
  if len(text)<120:
   issues.append({"id":r["id"],"reason":"too_short_for_reliable_article","characters":len(text)});continue
  pages=[int(v) for item in body for v in PAGE.findall(item)]
  actual=r.get("printed_page_start")
  # Page markers sometimes only appear AFTER a title; do not certify first page.
  if pages and pages[0]<actual:
   issues.append({"id":r["id"],"reason":"page_marker_precedes_catalog_page","catalog_start":actual,"first_seen":pages[0]});continue
  output.append({
   "id":r["id"],"year":year,"month":month,"title":r["title"],"source_url":url,
   "printed_page_start_catalog":actual,
   "page_markers_within_body":pages,
   "body_start_paragraph":start,"body_end_paragraph_exclusive":next_start,
   "text":text,"characters":len(text),
   "transcription_status":"corrected_ocr_provisional_requires_boundary_and_facsimile_review",
   "publication_status":"research_draft_not_public",
   "boundary_basis":"standalone matched body heading to next standalone issue TOC heading",
  })
 return output,issues
def main():
 master=json.loads((ROOT/"data/public-verified.json").read_text(encoding="utf8"))
 selected=master["records"]
 counts=Counter(r["year"] for r in selected)
 lock=json.loads((ROOT/"data/selected-251.lock.json").read_text(encoding="utf8"))
 if sorted(r["id"] for r in selected)!=lock["ids"]:
  raise SystemExit("Catalog lock failed: selected IDs changed without explicit approval")
 if len(selected)!=251 or len({r["id"] for r in selected})!=251 or any(v>50 for v in counts.values()):
  raise SystemExit("Catalog lock failed: expected exactly 251 unique selected records, <=50/year. No output overwritten.")
 drafts=[];failed=[];sources=[];done=0
 for year in range(1901,1907):
  for month in range(1,13):
   rows=[r for r in selected if r["year"]==year and r["month"]==month]
   try:
    result,errors=split_month(year,month,rows)
    drafts.extend(result)
    failed.extend({"year":year,"month":month,**e} for e in errors)
    sources.append(f"{year}-{month:02d}")
    done+=1
    print(f"{year}-{month:02d}: {len(result)} provisional / {len(errors)} unresolved",flush=True)
   except Exception as ex:
    failed.append({"year":year,"month":month,"reason":"source_fetch_or_parse_error","error":str(ex)})
    print(f"ERROR {year}-{month:02d}: {ex}",flush=True)
   time.sleep(.10)
 if done!=72:raise SystemExit(f"Only {done}/72 source issues readable; refuse partial save")
 out=ROOT/"data/transcriptions";out.mkdir(parents=True,exist_ok=True)
 for year in range(1901,1907):
  records=[r for r in drafts if r["year"]==year]
  (out/f"{year}-ocr-drafts.json").write_text(json.dumps({"year":year,"status":"draft_not_facsimile_verified_or_public","records":records},ensure_ascii=False,indent=2),encoding="utf8")
 audit=ROOT/"audit";audit.mkdir(exist_ok=True)
 report={"selected_record_count":251,"monthly_source_count":done,
  "draft_extracted_count":len(drafts),"unresolved_count":len(failed),
  "drafts_by_year":{str(y):sum(r["year"]==y for r in drafts) for y in range(1901,1907)},
  "failures":failed,
  "caveat":"These OCR excerpts are NOT authoritative publication texts. Unselected articles and uncertain endings must not be combined into a selected article. Manual boundary verification required."}
 (audit/"transcription-boundary-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
 print(json.dumps({k:v for k,v in report.items() if k!="failures"},ensure_ascii=False),flush=True)
if __name__=="__main__":main()

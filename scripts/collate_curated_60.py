#!/usr/bin/env python3
"""Strict source re-collation of 60 chosen Korea Review articles.

Reads each of 48? unique monthly corrected-OCR DOCX sources once; compares
57 existing drafts to the actual source paragraphs; examines 3 unresolved
records with title/next-heading/page evidence. Reports provisional text only,
not human-certified facsimile content. Never changes the 60-item public catalog.
"""
import io,json,re,unicodedata,zipfile,urllib.request,time,collections
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
N="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
PAGE=re.compile(r"\[page\s+(\d{1,4})\]",re.I)
def norm(s):
 return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKC",str(s)).casefold()).strip()
def get_source(y,m):
 url=f"https://anthony.sogang.ac.kr/KoreaReview/KoreaReviewVolume{y-1900}-{m:02d}.docx"
 with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"KoreaReReadAcademicVerification/1.0"}),timeout=90) as r:raw=r.read()
 with zipfile.ZipFile(io.BytesIO(raw)) as z:root=ET.fromstring(z.read("word/document.xml"))
 ps=[]
 for p in root.iter(N+"p"):
  t=" ".join("".join(x.text or "" for x in p.iter(N+"t")).split())
  if t:ps.append(t)
 return ps,url
def assess_existing(r,ps):
 start,end=r.get("body_start_paragraph"),r.get("body_end_paragraph_exclusive")
 if not isinstance(start,int) or not isinstance(end,int) or start<0 or end>len(ps) or start>=end:
  return {"status":"needs_boundary_review","reason":"paragraph_coordinates_invalid"}
 exact="\n\n".join(ps[start:end]).strip()==(r.get("text") or "").strip()
 if not exact:return {"status":"needs_source_review","reason":"saved_text_differs_from_monthly_docx","start":start,"end":end}
 marks=[int(z) for p in ps[start:end] for z in PAGE.findall(p)]
 lo=(r["month"]-1)*48+1;hi=r["month"]*48
 reasons=[]
 if any(x<lo or x>hi for x in marks):reasons.append("page_markers_outside_nominal_month")
 if any(a>b for a,b in zip(marks,marks[1:])):reasons.append("page_markers_decrease")
 title=norm(r["title"])
 if title not in norm(ps[start]):reasons.append("start_heading_not_exactly_normalized")
 return {"status":"source_text_exactly_matched_review_needed" if not reasons else "source_text_exactly_matched_with_flags",
  "text_matches_original_docx":True,"flags":reasons,"start":start,"end_exclusive":end,
  "characters":len(r.get("text") or "")}
def match_heading(p,t):
 return norm(p)==norm(t)
def find_toc(ps,target):
 # detect title line near opening and re-appearance in body
 key=norm(target)
 hits=[i for i,p in enumerate(ps) if match_heading(p,target) and len(p)<145]
 toc=[i for i in hits if i<50]
 body=[i for i in hits if i>=max((toc[0]+3 if toc else 2),2)]
 return hits,body
def try_recover(meta,ps,all_source_titles):
 title=meta["title"]
 hits,body=find_toc(ps,title)
 if len(body)!=1:return {"status":"needs_manual_boundary_review","reason":"ambiguous_or_missing_body_heading","heading_positions":hits}
 start=body[0]
 # Use known original monthly contents headings, not the next SELECTED article.
 toc_region=[norm(p) for p in ps[2:min(start,65)] if 5<=len(p)<=125]
 toc_set=set(toc_region)
 boundaries=[i for i in range(start+1,len(ps)) if len(ps[i])<145 and norm(ps[i]) in toc_set and norm(ps[i])!=norm(title)]
 if not boundaries:
  return {"status":"needs_manual_boundary_review","reason":"next_source_article_heading_unlocated",
   "heading_position":start,"source_paragraphs":len(ps)}
 end=min(boundaries)
 # Ignore page markers found in quoted context; do not assign them to the heading's printed page.
 text="\n\n".join(ps[start:end]).strip()
 if len(text)<120:return {"status":"needs_manual_boundary_review","reason":"body_too_short","start":start,"end":end}
 markers=[int(n) for p in ps[start:end] for n in PAGE.findall(p)]
 return {"status":"provisional_source_boundary_candidate_not_verified","start":start,"end_exclusive":end,
  "characters":len(text),"page_markers":markers,"title_evidence":ps[start],
  "text":text,"reason":"next_standalone_toc_heading_verified_as_boundary_candidate"}
def main():
 selected=json.loads((ROOT/"data/public-verified.json").read_text(encoding="utf8"))["records"]
 if len(selected)!=60 or any(sum(x["year"]==y for x in selected)!=10 for y in range(1901,1907)):
  raise RuntimeError("60 curated titles changed; refuse run")
 existing=json.loads((ROOT/"data/curated-60-ocr-drafts.json").read_text(encoding="utf8"))["records"]
 old={x["id"]:x for x in existing}
 out=[];source_errors=[];retrieved=0
 grouped=collections.defaultdict(list)
 for r in selected:grouped[(r["year"],r["month"])].append(r)
 for (y,m),group in sorted(grouped.items()):
  try:
   ps,url=get_source(y,m);retrieved+=1
   for r in group:
    prior=old[r["id"]]
    if prior.get("text"):
     check=assess_existing(prior,ps)
     out.append({"id":r["id"],"year":y,"title":r["title"],"source_url":url,**check})
    else:
     recovered=try_recover(r,ps,group)
     out.append({"id":r["id"],"year":y,"title":r["title"],"source_url":url,**recovered})
   print(f"{y}-{m:02d}: {len(group)} articles compared",flush=True)
  except Exception as e:
   source_errors.append({"year":y,"month":m,"error":str(e)})
   for r in group:out.append({"id":r["id"],"year":y,"title":r["title"],"status":"source_unavailable"})
  time.sleep(.10)
 count=collections.Counter(x["status"] for x in out)
 result={"scope":"60_curated_articles","selected_count":60,"months_fetched":retrieved,
  "status_counts":dict(count),"source_errors":source_errors,
  "warning":"Comparisons are against corrected OCR DOCX only, not scanned original print. No text is certified human-reviewed.",
  "checks":out}
 (ROOT/"audit/curated-60-source-collation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
 # Insertion of recovered drafts is allowed ONLY for bounded source candidates,
 # and still carries an explicit preliminary status. Never alter public metadata.
 byid={x["id"]:x for x in existing}
 for x in out:
  if x["status"]=="provisional_source_boundary_candidate_not_verified" and not byid[x["id"]].get("text"):
   d=byid[x["id"]];d["text"]=x["text"];d["characters"]=x["characters"]
   d["body_start_paragraph"]=x["start"];d["body_end_paragraph_exclusive"]=x["end_exclusive"]
   d["transcription_status"]="provisional_corrected_ocr_recovered_pending_facsimile_review"
   d["source_url"]=x["source_url"];d["boundary_basis"]=x["reason"]
 (ROOT/"data/curated-60-ocr-drafts.json").write_text(json.dumps({
  "scope":"representative_60_articles","status":"research_ocr_drafts_not_public_and_not_facsimile_verified",
  "records":existing},ensure_ascii=False,indent=2),encoding="utf8")
 print(json.dumps({"status_counts":dict(count),"source_errors":len(source_errors)},ensure_ascii=False),flush=True)
if __name__=="__main__":main()

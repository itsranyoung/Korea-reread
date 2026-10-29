#!/usr/bin/env python3
"""Review all locked 251 selected OCR drafts and 51 prior unresolved boundaries.

This is deterministic internal QC, NOT printed-facsimile certification. Never
promote OCR draft text to the public Vercel build.
"""
import json,re
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads((ROOT/path).read_text(encoding="utf8"))
def main():
 master=load("data/research-251-before-curation.json")["records"]
 lock=load("data/selected-251.lock.json")
 if len(master)!=251 or sorted(x["id"] for x in master)!=lock["ids"]:raise RuntimeError("selected 251 baseline changed")
 source={x["id"]:x for x in master}
 report=load("audit/transcription-boundary-report.json")
 drafts=[r for y in range(1901,1907) for r in load(f"data/transcriptions/{y}-ocr-drafts.json")["records"]]
 if len(drafts)!=report["draft_extracted_count"]:raise RuntimeError("draft count mismatch")
 verdict=[];counts=Counter()
 for r in drafts:
  reasons=[]
  original=source.get(r["id"])
  if original is None:reasons.append("id_not_in_locked_catalog")
  else:
   for field in ("year","month","title"):
    if r.get(field)!=original.get(field):reasons.append("catalog_"+field+"_mismatch")
   if r.get("printed_page_start_catalog")!=original.get("printed_page_start"):reasons.append("catalog_page_mismatch")
  body=r.get("text","")
  if len(body)!=r.get("characters"):reasons.append("incorrect_character_count")
  if len(body)<350:reasons.append("short_ocr_excerpt_review")
  if len(body)>60000:reasons.append("exceptionally_long_excerpt_review")
  marks=r.get("page_markers_within_body",[])
  low=(r["month"]-1)*48+1;high=r["month"]*48
  if any(not low<=p<=high for p in marks):reasons.append("page_marker_outside_expected_month")
  if any(a>b for a,b in zip(marks,marks[1:])):reasons.append("non_monotonic_print_page_markers")
  if r.get("body_end_paragraph_exclusive",0)<=r.get("body_start_paragraph",0)+1:reasons.append("invalid_body_boundary")
  if original and original.get("title","").casefold().replace("’","'")[:15] not in body[:260].casefold().replace("’","'"):
   reasons.append("title_not_in_transcribed_opening")
  status="ocr_draft_passed_automated_consistency_checks" if not reasons else "ocr_draft_requires_manual_review"
  counts[status]+=1
  verdict.append({"id":r["id"],"year":r["year"],"month":r["month"],"title":r["title"],"status":status,"reasons":reasons,"characters":len(body)})
 failure=[{"id":r.get("id"),"year":r["year"],"month":r["month"],"status":"no_reliable_draft", "reason":r.get("reason")} for r in report["failures"]]
 seen={r["id"] for r in drafts}|{r["id"] for r in failure if r.get("id")}
 missing=[x["id"] for x in master if x["id"] not in seen]
 result={"scope":"all_251_locked_selected_articles","ocr_draft_count":len(drafts),"unresolved_prior":len(failure),
  "automated_consistency_pass":counts["ocr_draft_passed_automated_consistency_checks"],
  "manual_review_flagged":counts["ocr_draft_requires_manual_review"],
  "missing_from_draft_and_failure_reports":missing,
  "by_year":{str(y):{"draft":sum(r["year"]==y for r in verdict),
    "automated_pass":sum(r["year"]==y and r["status"]=="ocr_draft_passed_automated_consistency_checks" for r in verdict),
    "flagged":sum(r["year"]==y and r["status"]=="ocr_draft_requires_manual_review" for r in verdict),
    "unresolved":sum(r["year"]==y for r in failure)} for y in range(1901,1907)},
  "draft_reviews":verdict,"unresolved":failure,
  "limitations":"OCR consistency check only; not article-by-article comparison against original scanned print. Do not label these human-verified."}
 out=ROOT/"audit/transcription-qc-251.json";out.parent.mkdir(exist_ok=True)
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
 print(json.dumps({k:v for k,v in result.items() if k not in ("draft_reviews","unresolved")},ensure_ascii=False))
if __name__=="__main__":main()

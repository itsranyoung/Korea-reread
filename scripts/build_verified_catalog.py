#!/usr/bin/env python3
"""Fail-closed public catalog: original monthly TOC + matching standalone body heading.

Do not equate a match with final page-level diplomatic transcription. Older catalogs
are retained as research inputs and never automatically published.
"""
import json,re,unicodedata
from pathlib import Path
P=Path(__file__).resolve().parents[1]
def norm(s):
 return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKC",str(s)).casefold()).strip()
def write(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf8")
def main():
 eligible=[];excluded=[];issues=[];missing=[]
 for year in range(1901,1907):
  cat=json.loads((P/f"data/{year}.json").read_text(encoding="utf8"))["records"]
  for month in range(1,13):
   p=P/f"audit/issue-boundaries/{year}-{month:02d}.json"
   if not p.exists():missing.append(str(p.relative_to(P)));continue
   report=json.loads(p.read_text(encoding="utf8"))
   evidence={z["id"]:z for z in report.get("matches",[])}
   for r in (z for z in cat if z.get("month")==month):
    e=evidence.get(r.get("id"))
    # Independent monthly TOC required, not annual alphabetic index.
    toc=(year==1901 and r.get("metadata_status")=="title_month_start_page_from_1901_toc") or (year==1906 and r.get("metadata_status")=="monthly_toc_checked")
    matches=bool(e and e.get("heading_count",0)>0)
    page=isinstance(r.get("printed_page_start"),int) and 1<=r["printed_page_start"]<=576
    reason=[] if toc and matches and page else [v for condition,v in ((toc,"no_independent_monthly_toc_provenance"),(matches,"missing_standalone_heading_match"),(page,"missing_valid_print_page")) if not condition]
    if not reason:
     eligible.append({**r,"publication_verification":"monthly_toc_plus_source_heading_evidence","verification_note":"TOC and standalone OCR heading agree; printed page is TOC-derived. Full boundary and facsimile collation pending.","source_heading_evidence":e["heading_evidence"],"human_review_status":"pending_full_text_collation"})
    else:excluded.append({"id":r.get("id"),"title":r.get("title"),"year":year,"month":month,"printed_page_start":r.get("printed_page_start"),"reasons":reason})
 if missing:raise RuntimeError(f"Missing original-month audit reports: {missing}")
 # 1902–1905: independent monthly TOC with explicit page AND later body title.
 monthly=P/"data/monthly-toc-confirmed-1902-1905.json"
 if monthly.exists():
  recon=json.loads(monthly.read_text(encoding="utf8"))
  if recon.get("source_errors") or len(recon.get("month_summaries",{}))!=48:
   raise RuntimeError("Reconstructed monthly catalog incomplete; refuse public merge")
  for r in recon.get("records",[]):
   if r.get("page_evidence_method") not in ("inline_toc_page","next_paragraph_page","preceding_embedded_print_page_marker") or not r.get("body_heading_paragraph_indices"):
    raise ValueError("Reconstructed item lacks independent TOC/page/body evidence")
   eligible.append(r)
 ids=set()
 for r in eligible:
  if r["id"] in ids:raise ValueError(f"duplicate public ID {r['id']}")
  ids.add(r["id"])
 eligible.sort(key=lambda r:(r["year"],r["month"],r["printed_page_start"],norm(r["title"])))
 write(P/"data/public-eligible-unselected.json",{"status":"machine_evidence_screened_not_human_verified","records":eligible})
 write(P/"data/public-verified.json",{"status":"strict_toc_heading_correlated_not_final_facsimile_certified","criteria":"Independent monthly TOC page + matching standalone title in original monthly corrected OCR","records":eligible})
 write(P/"audit/publication-decisions.json",{"published_count":len(eligible),"excluded_count":len(excluded),"excluded":excluded,"notice":"Excluded means insufficient evidence, not proof the historical article never existed. No uncertain titles are published.","missing_month_audit_files":missing})
 print("PUBLIC",len(eligible),"EXCLUDED",len(excluded))
if __name__=="__main__":main()

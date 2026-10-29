#!/usr/bin/env python3
"""Select at most 50 independently evidenced archival records per year.

Eligibility is a prerequisite, not a score. The output is a deliberately
bounded scholarly selection; it is NOT a complete bibliography or human-certified
facsimile transcription. Preserve all unselected and rejected entries for audit.
"""
import json,re,unicodedata
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/"data/public-eligible-unselected.json"
PUBLIC=ROOT/"data/public-verified.json"
AUDIT=ROOT/"audit/editorial-selection-1901-1906.json"
MAX_PER_YEAR=50
TOPICS={
 "history":("history","dynasty","king","queen","histor","ancient","chronicle","annals","reign","emperor"),
 "society":("woman","women","marriage","burial","custom","social","family","village","peasant","festival","life","people"),
 "politics":("japan","russia","war","government","diplom","politic","treaty","foreign","relations","minister","empire"),
 "economy":("trade","mines","mining","railway","currency","commercial","industry","agriculture","market","export"),
 "culture":("literature","language","education","school","poetry","poem","story","folklore","religion","buddhis","mission","art","music")
}
LOW_PRIORITY=("odds and ends","editorial comment","news calendar","question and answer","correspondence","korean history")
def norm(s):
 return re.sub(r"[^a-z0-9]+"," ",unicodedata.normalize("NFKC",str(s)).lower()).strip()
def category(title):
 s=norm(title)
 for topic,words in TOPICS.items():
  if any(w in s for w in words):return topic
 return "other"
def eligible(r):
 if r.get("publication_verification") not in ("monthly_toc_plus_source_heading_evidence","independent_issue_toc_page_and_body_heading_correlated"):return False,"no_toc_heading_cross_evidence"
 if not isinstance(r.get("month"),int) or r["month"] not in range(1,13):return False,"invalid_month"
 if not isinstance(r.get("printed_page_start"),int) or r["printed_page_start"]<1:return False,"no_start_page"
 if not r.get("title") or not r.get("source_url"):return False,"missing_title_or_source"
 if r.get("publication_verification")=="independent_issue_toc_page_and_body_heading_correlated":
  if not r.get("toc_raw") or not r.get("body_heading_paragraph_indices") or r.get("page_evidence_method") not in ("inline_toc_page","next_paragraph_page","preceding_embedded_print_page_marker"):return False,"no_independent_toc_body_page_evidence"
  if r.get("page_evidence_method")=="preceding_embedded_print_page_marker" and r.get("page_marker_witness")!=f"[page {r['printed_page_start']}]":return False,"inconsistent_page_marker"
 else:
  if not r.get("source_heading_evidence"):return False,"no_source_heading_evidence"
 return True,None
def score(r):
 t=norm(r["title"]);c=category(t)
 value=0
 if c!="other":value+=25
 if len(t.split())>=3:value+=8
 if len(t.split())>=5:value+=5
 if any(w in t for w in ("korea","korean","seoul","japan","chose","corea")):value+=15
 if r.get("page_evidence_method") in ("inline_toc_page","next_paragraph_page"):value+=10
 if norm(r["title"]) in LOW_PRIORITY:value-=30
 if r.get("multiple_body_occurrences"):value-=15
 return value
def sortkey(r):return (-score(r),norm(r["title"]),r["printed_page_start"],r["id"])
def main():
 if not CAND.exists():raise SystemExit("Missing full eligible catalog; run build_verified_catalog.py first")
 all_items=json.loads(CAND.read_text(encoding="utf8"))["records"]
 byyear=defaultdict(list);rejected=[];seen=set()
 for r in all_items:
  ok,reason=eligible(r)
  unique=(r.get("year"),r.get("month"),norm(r.get("title","")),r.get("printed_page_start"))
  if unique in seen:ok=False;reason="duplicate_year_month_title_page"
  if ok:
   seen.add(unique);byyear[r["year"]].append(r)
  else:rejected.append({"id":r.get("id"),"year":r.get("year"),"reason":reason})
 selected=[];unselected=[];year_stats={}
 for year in range(1901,1907):
  pool=byyear[year];groups=defaultdict(list)
  for r in pool:groups[r["month"]].append(r)
  for m in groups:groups[m].sort(key=sortkey)
  chosen=[];keys=set();categories=Counter()
  # First rotation distributes representation among all months with evidence.
  while len(chosen)<MAX_PER_YEAR:
   changed=False
   for month in range(1,13):
    group=groups.get(month,[])
    candidate=next((r for r in group if r["id"] not in keys),None)
    if candidate is None:continue
    chosen.append(candidate);keys.add(candidate["id"]);categories[category(candidate["title"])]+=1;changed=True
    if len(chosen)==MAX_PER_YEAR:break
   if not changed:break
  # If selection was smaller than cap, already exhausted all eligible titles.
  selected.extend(chosen)
  unselected.extend({"id":r["id"],"year":year,"title":r["title"],"reason":"editorial_cap_or_monthly_balance"} for r in pool if r["id"] not in keys)
  year_stats[str(year)]={"eligible":len(pool),"selected":len(chosen),"unselected":len(pool)-len(chosen),
   "months_represented":len({r["month"] for r in chosen}),"categories":dict(categories)}
 selected.sort(key=lambda r:(r["year"],r["month"],r["printed_page_start"],norm(r["title"])))
 for r in selected:
  r["editorial_selection"]="bounded_source_correlated_representative_selection"
  r["editorial_selection_method"]="50 maximum per year, source evidence filter, monthly round-robin, transparent title-based thematic preference"
  r["human_review_status"]="pending_facsimile_collation"
 PUBLIC.write_text(json.dumps({"status":"curated_machine_cross_checked_pending_manual_facsimile_verification",
  "notice":"Representative scholarly selection, NOT an exhaustive bibliography nor final facsimile-verification.",
  "max_per_year":MAX_PER_YEAR,"records":selected},ensure_ascii=False,indent=2),encoding="utf8")
 AUDIT.parent.mkdir(exist_ok=True)
 AUDIT.write_text(json.dumps({"source_candidate_count":len(all_items),"selected_count":len(selected),
  "year_stats":year_stats,"excluded_for_insufficient_evidence":rejected,
  "eligible_but_not_selected":unselected,
  "limitations":["Topic classification is based on titles only, not article full text",
  "Page number may be inferred from OCR marker position; final facsimile comparison is pending",
  "Full article starts and ends have not been transcribed and verified",
  "Month coverage is a diversity objective, not evidence of completeness"]},ensure_ascii=False,indent=2),encoding="utf8")
 print(json.dumps(year_stats,ensure_ascii=False))
if __name__=="__main__":main()

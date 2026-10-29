#!/usr/bin/env python3
"""Strict six-volume catalog integrity audit. Does not certify completeness."""
from pathlib import Path
from collections import defaultdict,Counter
import json,re,datetime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"audit/catalog-integrity-1901-1906.json"
def norm(s):return re.sub(r"[^a-z0-9]+"," ",str(s).casefold()).strip()
result={"scope":"1901–1906","completeness_certified":False,"years":{}}
for y in range(1901,1907):
    p=ROOT/"data"/f"{y}.json"
    if not p.is_file():
        result["years"][str(y)]={"exists":False,"records":0,"missing_months":list(range(1,13)),"complete":False}
        continue
    rows=json.loads(p.read_text(encoding="utf-8")).get("records",[])
    groups=defaultdict(list);exact=defaultdict(list);ids=Counter();invalid=[];provisional=0
    for r in rows:
        rid=r.get("id");ids[rid]+=1
        m=r.get("month");title=r.get("title");page=r.get("printed_page_start")
        if r.get("year")!=y or not isinstance(m,int) or m<1 or m>12 or not title or not isinstance(page,int) or page<1:
            invalid.append({"id":rid,"reason":"year/month/title/page missing or invalid"})
        if isinstance(m,int) and 1<=m<=12:groups[m].append(r)
        exact[(m,norm(title),page)].append(rid)
        if r.get("human_review_status")!="verified":provisional+=1
    duplicated=[{"key":str(k),"ids":v} for k,v in exact.items() if len(v)>1]
    result["years"][str(y)]={
      "exists":True,"records":len(rows),
      "month_counts":{str(m):len(groups[m]) for m in range(1,13)},
      "missing_months":[m for m in range(1,13) if not groups[m]],
      "invalid_records":invalid,
      "duplicate_ids":[k for k,n in ids.items() if n>1],
      "exact_duplicate_article_candidates":duplicated,
      "not_human_verified":provisional,
      "complete":False,
      "note":"A full monthly contents to original article boundary reconciliation is needed before completeness is certified"
    }
result["totals"]={"records":sum(x["records"] for x in result["years"].values()),
    "missing_months":sum(len(x["missing_months"]) for x in result["years"].values()),
    "invalid_records":sum(len(x.get("invalid_records",[])) for x in result["years"].values()),
    "exact_duplicates":sum(len(x.get("exact_duplicate_article_candidates",[])) for x in result["years"].values())}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(result["totals"],ensure_ascii=False))

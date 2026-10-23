#!/usr/bin/env python3
"""Report missing months, duplicates and unverified month placement across archive.

This is an audit, not proof of bibliographic completeness: each year requires
comparison with the complete printed contents and original issue scans.
"""
import json,re
from collections import Counter,defaultdict
from pathlib import Path
DATA=Path("data");AUDIT=Path("audit");AUDIT.mkdir(exist_ok=True)
def norm(s):return re.sub(r"\W+"," ",s.casefold()).strip()
def main():
    reports={}
    for year in range(1901,1907):
        f=DATA/f"{year}.json"
        if not f.exists():
            reports[str(year)]={"status":"no_published_article_catalog","records":0}
            continue
        payload=json.loads(f.read_text(encoding="utf-8"))
        rows=payload.get("records",[])
        groups=defaultdict(list)
        for row in rows:groups[row.get("month")].append(row)
        duplicates=[];seen={}
        for row in rows:
            key=(row.get("month"),norm(row.get("title","")),row.get("printed_page_start"))
            if key in seen:duplicates.append({"first":seen[key],"second":row.get("id"),"reason":"identical title month page"})
            else:seen[key]=row.get("id")
        repeated_titles={k:v for k,v in Counter(norm(r["title"]) for r in rows).items() if v>1}
        month_problem=[r["id"] for r in rows if not isinstance(r.get("month"),int) or r["month"] not in range(1,13)]
        provisional=[r["id"] for r in rows if "needs_issue_check" in r.get("metadata_status","")]
        reports[str(year)]={
            "status":"partial_catalog_not_completeness_verified",
            "record_count":len(rows),
            "month_counts":{str(m):len(groups[m]) for m in range(1,13)},
            "missing_months":[m for m in range(1,13) if not groups[m]],
            "exact_duplicate_entries":duplicates,
            "repeated_titles_not_necessarily_duplicates":repeated_titles,
            "invalid_month_entries":month_problem,
            "needs_individual_month_source_verification":len(provisional),
            "provisional_record_ids":provisional,
            "warning":"Zero exact duplicates does NOT prove no articles are missing."
        }
    (AUDIT/"catalog-audit.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding="utf-8")
    for year,r in reports.items():
        print(year,r.get("record_count",0),"rows;",
              "exact duplicates",len(r.get("exact_duplicate_entries",[])),
              "missing months",r.get("missing_months",[]),
              "provisional",r.get("needs_individual_month_source_verification",0))
if __name__=="__main__":main()

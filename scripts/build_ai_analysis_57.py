#!/usr/bin/env python3
"""Build conservative source-evidenced STEP 03 draft analyses for 57 articles.
No model-generated factual summaries are invented. Only exact passages and
strict literal matches are stored as machine candidates for human review.
"""
import json,re,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/"data/curated-60-ocr-drafts.json").read_text(encoding="utf8"))["records"]
catalog=json.loads((ROOT/"data/public-verified.json").read_text(encoding="utf8"))["records"]
if len(data)!=57 or {x["id"] for x in data}!={x["id"] for x in catalog}:raise SystemExit("57 article identity mismatch")
LEXICON={
 "place":{"Seoul":["Seoul"],"Pyongyang":["Pyeng-Yang","P'yung-Yang","Pyongyang","P’yung-Yang"],"Chemulpo":["Chemulpo"],"Korea":["Korea","Korean"],"Japan":["Japan","Japanese"],"China":["China","Chinese"],"Hawaii":["Hawaii"],"Quelpart":["Quelpart"],"Fusan":["Fusan"],"Siberia":["Siberia"]},
 "organization":{"Severance Hospital":["Severance Hospital"],"Peddlars’ Guild":["Peddlars' Guild","Peddlars’ Guild"],"Bible Committee of Korea":["Bible Committee of Korea"]},
 "person":{"Min Yong-Whan":["Min Yong-Whan"],"Ch’oe Ch’i-Wun":["Ch'oe Ch'i-Wun","Ch’oe Ch’i-Wun"],"Henry G. Appenzeller":["Henry G. Appenzeller"]}
}
KEYWORDS={"education":["school","education","educational"],"history":["history","dynasty","kingdom"],"language":["language","alphabet","writing"],"culture":["custom","proverb","folklore"],"economy":["currency","trade","banking","mining","tax"],"politics":["government","official","law"],"international_relations":["Japan","Russia","war","foreign"],"religion":["religion","Buddhism","Christian"],"society":["woman","slavery","emigrant","hospital"]}
def excerpt(text,needle):
 p=re.search(r'(?<!\w)'+re.escape(needle)+r'(?!\w)',text,re.I)
 if not p:return None
 a=max(text.rfind("\n\n",0,p.start())+2,0)
 b=text.find("\n\n",p.end())
 if b<0:b=len(text)
 fragment=text[a:b].strip()
 return fragment[:500] if len(fragment)>500 else fragment
out=[]
for r in data:
 body=r["text"]
 evidence=[]
 for para in body.split("\n\n"):
  t=para.strip()
  if len(t)>=65 and not re.fullmatch(r"\[page\s*\d+\]",t,re.I):
   evidence.append({"quote":t[:450],"source":"ocr_text","location":"first_substantive_paragraph","truncated":len(t)>450})
   break
 entities=[]
 for kind,canon in LEXICON.items():
  for label,spellings in canon.items():
   for spelling in spellings:
    quote=excerpt(body,spelling)
    if quote:
     entities.append({"type":kind,"surface_form":spelling,"canonical_candidate":label,"evidence_quote":quote,"status":"candidate_requires_human_review","method":"literal_lexicon_match"})
     break
 words=[]
 for label,forms in KEYWORDS.items():
  for form in forms:
   quote=excerpt(body,form)
   if quote:
    words.append({"keyword_candidate":label,"trigger":form,"evidence_quote":quote,"status":"candidate_requires_human_review"})
    break
 out.append({"id":r["id"],"year":r["year"],"title":r["title"],"source_url":r["source_url"],
  "ocr_sha256":hashlib.sha256(body.encode("utf8")).hexdigest(),
  "analysis_schema_version":"0.1.0",
  "analysis_stage":"source_evidence_extracted_summary_pending",
  "summary_ko":None,"summary_status":"not_generated_no_unsupported_claims",
  "topic_candidates":words,
  "entities":entities,
  "evidence_passages":evidence,
  "review":{"status":"pending_human_review","reviewer":None,"reviewed_at":None,"corrections":[]},
  "provenance":{"method":"deterministic_literal_matching_not_llm","model":None,"input":"corrected_OCR_article_draft","source_text_verified_against_corrected_docx":True,"facsimile_verified":False},
  "limitations":["Literal entity candidates are not disambiguated","Topic matches are not semantic conclusions","No Korean summary was generated"]})
payload={"project":"KOREA RE:READ","scope":"57_selected_articles","status":"research_candidates_not_public","analysis_schema_version":"0.1.0","records":out}
target=ROOT/"data/ai-analysis-57-drafts.json"
target.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"articles":len(out),"entity_candidates":sum(len(x["entities"]) for x in out),"topic_candidates":sum(len(x["topic_candidates"]) for x in out),"with_ocr_evidence":sum(bool(x["evidence_passages"]) for x in out),"korean_summaries":0},ensure_ascii=False))

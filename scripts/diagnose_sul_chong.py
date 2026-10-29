#!/usr/bin/env python3
"""Diagnose March 1901 Sul-Chong article with corrected-OCR DOCX.
Produces bounded, inspectable candidate excerpts but never changes the archive.
"""
import io,zipfile,urllib.request,json,re,xml.etree.ElementTree as ET
from pathlib import Path
U="https://anthony.sogang.ac.kr/KoreaReview/KoreaReviewVolume1-03.docx"
with urllib.request.urlopen(urllib.request.Request(U,headers={"User-Agent":"KoreaReReadResearch/1.0"}),timeout=75) as f:raw=f.read()
root=ET.fromstring(zipfile.ZipFile(io.BytesIO(raw)).read("word/document.xml"))
NS="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ps=[]
for p in root.iter(NS+"p"):
 t=" ".join("".join(x.text or "" for x in p.iter(NS+"t")).split())
 if t:ps.append(t)
hits=[i for i,p in enumerate(ps) if re.search(r"sul.{0,12}ch.{0,8}ong|father.{0,12}korean literature|geo.{0,9}heber jones|a leaf from my journal",p,re.I)]
out={"source":U,"paragraph_count":len(ps),"matches":[{"index":i,"text":ps[i][:350],"context":[{"index":k,"text":ps[k][:600]} for k in range(max(0,i-2),min(len(ps),i+5))]} for i in hits],"page_markers":[{"index":i,"text":p[:160]} for i,p in enumerate(ps) if re.search(r"\[page\s*(?:10[0-9]|11[0-3])\]",p,re.I)][:25]}
Path("audit/sul-chong-source-diagnosis.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"paragraph_count":len(ps),"matches":len(hits)},ensure_ascii=False))

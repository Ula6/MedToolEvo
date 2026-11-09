"""Prepare every source question, without support-based exclusion or model calls."""
import hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).parent/"data"
SOURCE=ROOT/"BioASQ-training14b/training14b.json"
SEED="formal-v1-20261106"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open("x",encoding="utf-8") as f:json.dump(v,f,ensure_ascii=False,indent=2)
def task(q):
 evidence=[];seen=set()
 for s in q.get("snippets",[]):
  if not isinstance(s,dict) or not isinstance(s.get("text"),str) or not s["text"].strip():continue
  k=(s.get("document"),s["text"])
  if k in seen:continue
  seen.add(k)
  evidence.append({"evidence_id":f"e{len(evidence)+1}","source":s.get("document"),"text":s["text"],"section":s.get("beginSection"),"offset":s.get("offsetInBeginSection")})
 return {"id":q["id"],"question":q["body"],"type":q["type"],"evidence":evidence}
def main():
 summary=json.loads((ROOT/"audit_20261106/data_audit_v1/audit_summary.json").read_text(encoding="utf-8"))
 assert sha(SOURCE)==summary["source_sha256"],"Source differs from audited version"
 qs=json.loads(SOURCE.read_text(encoding="utf-8"))["questions"]
 groups=json.loads((ROOT/"audit_20261106/data_audit_v1/group_partitions.json").read_text(encoding="utf-8"))
 public={q["id"]:task(q) for q in qs}
 private={q["id"]:{"id":q["id"],"type":q["type"],"exact_answer":q.get("exact_answer"),"ideal_answer":q.get("ideal_answer")} for q in qs}
 assignment={};group_rows=[]
 for g in groups:
  bucket=int(hashlib.sha256((SEED+":"+g["component_id"]).encode()).hexdigest()[:8],16)%100
  split="development_seen" if g["partition"]=="previously_used" else "discovery" if bucket<20 else "admission" if bucket<40 else "evaluation"
  group_rows.append({"component_id":g["component_id"],"partition":split,"question_ids":g["question_ids"]})
  for qid in g["question_ids"]:
   assert qid not in assignment;assignment[qid]=(split,g["component_id"])
 assert set(assignment)==set(public)
 for view in ("all","list"):
  records=[q for q in qs if view=="all" or q["type"]=="list"]
  counts={}
  for part in ("development_seen","discovery","admission","evaluation"):
   chosen=[q for q in records if assignment[q["id"]][0]==part]
   chosen.sort(key=lambda q:hashlib.sha256((SEED+":order:"+q["id"]).encode()).hexdigest())
   folder=OUT/view/part
   save(folder/"tasks.json",[public[q["id"]] for q in chosen])
   save(folder/"references.json",[private[q["id"]] for q in chosen])
   counts[part]={"total":len(chosen),"types":dict(Counter(q["type"] for q in chosen))}
  save(OUT/view/"tasks.json",[public[q["id"]] for q in records])
  save(OUT/view/"references.json",[private[q["id"]] for q in records])
  save(OUT/view/"manifest.json",{"source_sha256":sha(SOURCE),"scope":view,"total":len(records),"partitions":counts,"seed":SEED,
   "all_source_items_included":True,"support_based_exclusions":0,"token_length_exclusions":0,
   "partition_method":"Question/paper-identifier connected groups across all types, fixed SHA256 buckets 20/20/60, with previously used connected groups assigned to development_seen.",
   "data_status":"Retrospective partition of a provided training corpus after offline audit, not official BioASQ test and not a previously untouched blind set.",
   "reference_visibility":"Only references.json contains exact/ideal labels; never send to models.",
   "limitations":["Canonical identifiers do not resolve every PMID/PMCID/DOI equivalence.","All ineligible and failed items must remain in reporting denominators.","Models may have pretrained on public data; no contamination-free claim."]})
 save(OUT/"group_partitions.json",group_rows)
 save(OUT/"provenance.json",{"source":str(SOURCE),"source_sha256":sha(SOURCE),"group_audit_sha256":sha(ROOT/"audit_20261106/data_audit_v1/group_partitions.json"),"all_questions":len(qs),"list_questions":sum(q["type"]=="list" for q in qs),"model_calls":0,"generator_sha256":sha(Path(__file__))})
 print(json.dumps({v:json.loads((OUT/v/"manifest.json").read_text(encoding="utf-8"))["partitions"] for v in ("all","list")},ensure_ascii=False,indent=2))
if __name__=="__main__":main()

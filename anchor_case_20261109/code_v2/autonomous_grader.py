"""Offline literal-alias coverage proxy; no reference items go to model roles."""
import re
def aliases(label):
 values=[label]+re.findall(r"\(([^()]*)\)",label)
 values.append(re.sub(r"^genotypes?\s+","",label,flags=re.I))
 out=[]
 for v in values:
  for a in v.split("/"):
   a=a.strip()
   if a and a not in out:out.append(a)
 return out
def hit(text,a):return re.search(r"(?<!\w)"+re.escape(a)+r"(?!\w)",text,re.I) is not None
def grade(task,reference,answer):
 if task.get("type")!="list":return {"eligible":False,"reason":"initial autonomous protocol is list evidence QA"}
 groups=reference.get("exact_answer")
 if not isinstance(groups,list) or not groups or any(not isinstance(g,list) or not g or any(not isinstance(x,str) for x in g) for g in groups):return {"eligible":False,"reason":"unsupported reference schema"}
 text="\n".join(e["text"] for e in task["evidence"]);supported=[];hits=[]
 for g in groups:
  aa=[a for name in g for a in aliases(name)]
  support=any(hit(text,a) for a in aa)
  supported.append(support);hits.append(support and any(hit(answer,a) for a in aa))
 total=sum(supported)
 return {"eligible":total==len(groups),"reason":"all reference groups literally supported" if total==len(groups) else "reference not fully supported by input snippets",
 "matched_groups":sum(hits),"supported_groups":total,"total_reference_groups":len(groups),"coverage":sum(hits)/total if total else None,"complete":bool(total) and all(hits),
 "metric":"literal alias coverage proxy, not semantic medical correctness"}
def redacted_feedback(score):
 return {"eligible":score.get("eligible",False),"status":"complete" if score.get("complete") else "incomplete","metric":"supported_reference_coverage_proxy","evaluation_performed":True,"reference_items_withheld":True}

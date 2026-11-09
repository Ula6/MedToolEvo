"""Transparent per-item list metrics; final reports also run the pinned BioASQ Java evaluator."""
import math,re
def parse_official_output(stdout):
 values={name:float(value) for name,value in re.findall(r"^List (Prec|Rec|F1): ([0-9.eE+-]+)$",stdout,re.M)}
 if set(values)!={"Prec","Rec","F1"} or any(not math.isfinite(x) for x in values.values()):raise ValueError("Official evaluator did not produce finite list metrics")
 return {"precision":values["Prec"],"recall":values["Rec"],"f1":values["F1"]}
def score_list(items,reference):
 groups=reference.get("exact_answer")
 if not isinstance(groups,list) or not groups or any(not isinstance(g,list) or not g or any(not isinstance(a,str) for a in g) for g in groups):
  return {"status":"invalid_reference","precision":0.0,"recall":0.0,"f1":0.0}
 if not isinstance(items,list) or any(not isinstance(s,str) or not s.strip() for s in items):
  return {"status":"invalid_prediction","precision":0.0,"recall":0.0,"f1":0.0}
 remaining=[{a.lower() for a in g} for g in groups];tp=0
 for item in items:
  for i,g in enumerate(remaining):
   if item.lower() in g:tp+=1;remaining.pop(i);break
 p=tp/len(items) if items else 0.0;r=tp/len(groups)
 return {"status":"scored","tp":tp,"fp":len(items)-tp,"fn":len(groups)-tp,"precision":p,"recall":r,"f1":2*p*r/(p+r) if p+r else 0.0}
def paired_gate(rows,alpha=.05,regression_weight=2):
 wins=sum(r["candidate_f1"]>r["baseline_f1"]+1e-12 for r in rows)
 losses=sum(r["candidate_f1"]<r["baseline_f1"]-1e-12 for r in rows)
 m=wins+losses;q=regression_weight/(1+regression_weight)
 p=sum(math.comb(m,k)*q**k*(1-q)**(m-k) for k in range(wins,m+1)) if m else 1.0
 gain=sum(r["candidate_f1"]-r["baseline_f1"] for r in rows)/len(rows) if rows else 0.0
 accept=bool(rows) and gain>1e-12 and losses==0 and p<alpha and all(r.get("execution_ok",False) for r in rows)
 return {"accept":accept,"mean_f1_gain":gain,"wins":wins,"regressions":losses,"ties":len(rows)-wins-losses,"paired_sign_tail":p,"alpha":alpha,"regression_weight":regression_weight,
  "rule":"positive mean F1 gain, no per-question F1 regression, one-sided weighted sign tail below alpha, all candidate executions valid",
  "interpretation":"conservative engineering gate with a paired sign diagnostic; not a proof of clinical correctness or an exact reproduction of SAGE"}

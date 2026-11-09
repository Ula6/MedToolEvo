"""Calibrate local P/R/F1 against the pinned official evaluator on fixed synthetic cases."""
import json,subprocess
from pathlib import Path
from formal_list_metrics import score_list,parse_official_output
from runtime_tools import ROOT
folder=ROOT/"tmp/formal_metric_calibration_20261106";folder.mkdir(exist_ok=True)
cases=[([["Alpha","A1"],["Beta"]],["alpha","wrong"]),([["Alpha","A1"]],["Alpha","A1"]),([["Alpha"]],[]),([["Alpha"]],["alpha"])]
gold={"questions":[{"id":f"q{i}","type":"list","exact_answer":g} for i,(g,p) in enumerate(cases)]}
pred={"questions":[{"id":f"q{i}","type":"list","exact_answer":[[x] for x in p]} for i,(g,p) in enumerate(cases)]}
for name,obj in (("gold",gold),("pred",pred)):(folder/(name+".json")).write_text(json.dumps(obj),encoding="utf-8")
jar=ROOT/"third_party/bioasq-evaluation/flat/BioASQEvaluation/dist/BioASQEvaluation.jar"
command=["java","-cp",str(jar)+":"+str(jar.parent/"lib/*"),"evaluation.EvaluatorTask1b","-phaseB","-e","5",str(folder/"gold.json"),str(folder/"pred.json"),"-verbose"]
p=subprocess.run(command,capture_output=True,text=True,timeout=30)
local=[score_list(items,{"exact_answer":g}) for g,items in cases]
report={"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"local_macro":{k:sum(x[k] for x in local)/len(local) for k in ("precision","recall","f1")}}
official=parse_official_output(p.stdout)
assert all(abs(report["local_macro"][k]-official[k])<1e-10 for k in official)
report["matches_official"]=True
(folder/"calibration.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
if p.returncode:raise SystemExit(p.returncode)

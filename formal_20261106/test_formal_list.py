"""Meaningful scoring, leakage, cache and fail-closed checks before freezing the study."""
import json,tempfile,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from formal_list_metrics import score_list,paired_gate,parse_official_output
from run_formal_list import Study,union,items_of,atomic,ROOT,ServiceUnavailable
from autonomous_evolution import assert_public
class FormalChecks(unittest.TestCase):
 def test_service_outage_is_not_a_wrong_answer(self):
  with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
   p=Study.__new__(Study);p.run=Path(d);p.references={"t":{"exact_answer":[["Alpha"]]}}
   p.ask=lambda *a,**k: (_ for _ in ()).throw(ServiceUnavailable("test outage"))
   with self.assertRaises(ServiceUnavailable):p.prepare_task({"id":"t","type":"list","question":"List","evidence":[]},"discovery")
   self.assertFalse((p.run/"tasks/t/base_results.json").exists())
 def test_official_evaluator_failure_cannot_look_completed(self):
  with self.assertRaises(ValueError):parse_official_output("Error: bad data")
  with self.assertRaises(ValueError):parse_official_output("List Prec: NaN\nList Rec: NaN\nList F1: NaN")
  self.assertEqual(parse_official_output("List Prec: 0.5\nList Rec: 0.625\nList F1: 0.5416666666666666")["precision"],.5)
 def test_alias_case_and_extra_items(self):
  r=score_list(["alpha","irrelevant"],{"exact_answer":[["Alpha","A1"],["Beta"]]})
  self.assertEqual((r["tp"],r["fp"],r["fn"]),(1,1,1));self.assertEqual(r["f1"],.5)
 def test_duplicate_synonyms_are_false_positives(self):
  r=score_list(["Alpha","A1"],{"exact_answer":[["Alpha","A1"]]})
  self.assertEqual((r["tp"],r["fp"]),(1,1));self.assertAlmostEqual(r["f1"],2/3)
 def test_empty_predictions_score_zero_without_losing_denominator(self):
  r=score_list([],{"exact_answer":[["Alpha"]]});self.assertEqual(r["f1"],0);self.assertEqual(r["fn"],1)
 def test_no_partial_string_credit(self):
  self.assertEqual(score_list(["Alpha receptor"],{"exact_answer":[["Alpha"]]})["f1"],0)
 def test_reference_is_not_mutated(self):
  ref={"exact_answer":[["Alpha","A1"]]};old=json.dumps(ref);score_list(["Alpha"],ref);self.assertEqual(json.dumps(ref),old)
 def test_weighted_gate_abstains_with_small_sample(self):
  rows=[{"baseline_f1":0,"candidate_f1":1,"execution_ok":True} for _ in range(4)]
  self.assertFalse(paired_gate(rows)["accept"])
 def test_weighted_gate_requires_no_regressions(self):
  rows=[{"baseline_f1":0,"candidate_f1":1,"execution_ok":True} for _ in range(20)]
  self.assertTrue(paired_gate(rows)["accept"])
  rows.append({"baseline_f1":1,"candidate_f1":0,"execution_ok":True});self.assertFalse(paired_gate(rows)["accept"])
 def test_failed_execution_blocks_gate(self):
  rows=[{"baseline_f1":0,"candidate_f1":1,"execution_ok":False} for _ in range(20)]
  self.assertFalse(paired_gate(rows)["accept"])
 def test_public_input_guard(self):
  with self.assertRaises(ValueError):assert_public({"task":{"exact_answer":["private"]}})
 def test_submission_renderer_is_bounded_and_keeps_raw_output(self):
  payload=[{"name":f"A{i}","evidence_id":"e1"} for i in range(105)]+[{"name":"x"*101,"evidence_id":"e1"}]
  result=union(payload);self.assertEqual(result["unique_entity_count"],106);self.assertEqual(len(items_of(result)),100)
  self.assertEqual(items_of(union([{"name":"x"*230,"evidence_id":"e1"}])),["x"*230])
 def test_cache_rejects_changed_input(self):
  with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
   p=Study.__new__(Study);p.run=Path(d);p.context=16384;p.generation_calls=0
   p.api=lambda endpoint,body:{"prompt":"formatted"} if endpoint=="apply-template" else {"tokens":[1]} if endpoint=="tokenize" else {"choices":[{"finish_reason":"stop","message":{"content":json.dumps({"items":["Alpha"]})}}],"usage":{}}
   self.assertEqual(p.ask("case/direct","prompt",{"question":"public"},10)["items"],["Alpha"])
   with self.assertRaisesRegex(ValueError,"input changed"):p.ask("case/direct","prompt",{"question":"different"},10)
 def test_partial_extraction_fails_shared_arms_closed(self):
  with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
   p=Study.__new__(Study);p.run=Path(d);p.references={"t":{"exact_answer":[["Alpha"]]}};p.event=lambda *a,**k:None;p.progress=lambda:None
   p.ask=lambda *a,**k:{"items":["Alpha"]}
   p.observations=lambda *a:{"mentions":[{"name":"Alpha","evidence_id":"e1","quote":"Alpha"}],"status":"partial","failed_chunks":[{"chunk":1}]}
   r=p.prepare_task({"id":"t","type":"list","question":"List","evidence":[]},"discovery")
   self.assertEqual(r["arms"]["trusted_aggregation"]["score"]["f1"],0)
   self.assertEqual(r["arms"]["same_observation_LLM"]["items"],[])
   self.assertEqual(r["arms"]["direct_QA"]["score"]["f1"],1)
 def test_final_report_keeps_all_partitions_and_official_metrics(self):
  with tempfile.TemporaryDirectory(dir=ROOT/"tmp") as d:
   root=Path(d);p=Study.__new__(Study);p.run=root/"experiment";p.run.mkdir()
   p.dataset=root/"dataset/list";p.dataset.mkdir(parents=True)
   p.parts={part:[{"id":f"t{i}","type":"list"}] for i,part in enumerate(["development_seen","discovery","admission","evaluation"])}
   p.tasks={t["id"]:t for ts in p.parts.values() for t in ts};p.references={k:{"exact_answer":[["Alpha"],["Beta"]]} for k in p.tasks}
   p.status={};p.generation_calls=0
   prediction={"status":"ok","items":["Alpha","wrong"],"score":score_list(["Alpha","wrong"],{"exact_answer":[["Alpha"],["Beta"]]})}
   atomic(p.run/"protocol.json",{"interpretation":["unit fixture"]})
   atomic(p.dataset.parent/"group_partitions.json",[{"component_id":k,"question_ids":[k]} for k in p.tasks])
   for part,ts in p.parts.items():
    for t in ts:
     folder=p.run/"tasks"/t["id"]
     atomic(folder/"base_results.json",{"task_id":t["id"],"partition":part,"literal_support":{"eligible":True},"arms":{a:prediction for a in ["direct_QA","same_observation_LLM","trusted_aggregation"]}})
     atomic(folder/"frozen_prediction.json",prediction)
     atomic(folder/"observations.json",{"mentions":[],"rejected":[],"failed_chunks":[]})
   fake=SimpleNamespace(returncode=0,stdout="List Prec: 0.5\nList Rec: 0.5\nList F1: 0.5\n",stderr="")
   with patch("run_formal_list.subprocess.run",return_value=fake):p.report({"frozen_strategy":"same_observation_LLM"})
   result=json.loads((p.run/"summary.json").read_text())
   self.assertEqual(result["status"],"completed")
   self.assertEqual(result["partitions"]["evaluation"]["arms"]["direct_QA"]["official"]["f1"],.5)
   self.assertEqual(result["source_questions"],4)
   self.assertEqual(result["paired_f1_bootstrap"]["trusted_aggregation"]["ci95"],[0,0])
if __name__=="__main__":unittest.main(verbosity=2)

"""Trusted contracts, source checks and code transport for generic evidence tools."""
import ast
import copy
import hashlib
import json
import re
from pathlib import Path


PRIVATE = {"gold", "gold_answer", "exact_answer", "ideal_answer", "references", "reference_answer", "gold_evidence"}


def public(value):
    if isinstance(value, dict):
        if PRIVATE.intersection(value):
            raise ValueError("Reference answers cannot enter model inputs")
        for child in value.values():
            public(child)
    elif isinstance(value, list):
        for child in value:
            public(child)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_answer(task, answer):
    """Quote presence is checked here; biomedical support remains a semantic judgment."""
    if not isinstance(answer, dict) or not isinstance(answer.get("items"), list):
        raise ValueError("Expected items array")
    if len(answer["items"]) > 100 or any(not isinstance(s, str) or not s.strip() or len(s) > 512 for s in answer["items"]):
        raise ValueError("Invalid answer items")
    items = [s.strip() for s in answer["items"]]
    evidence = {e["evidence_id"]: e["text"] for e in task["evidence"]}
    supports = answer.get("supports", [])
    if not isinstance(supports, list):
        raise ValueError("supports must be an array")
    valid, invalid = [], []
    for i, claim in enumerate(supports):
        if not isinstance(claim, dict):
            invalid.append({"index": i, "error": "malformed support"})
            continue
        quote = claim.get("quote")
        if claim.get("item") not in items or not isinstance(quote, str) or not quote.strip() or quote not in evidence.get(claim.get("evidence_id"), ""):
            invalid.append({"index": i, "error": "item or literal source span invalid", "claim": claim})
        else:
            valid.append(claim)
    missing = [s for s in items if not any(c["item"] == s for c in valid)]
    return {"items": items, "supports": valid, "invalid_supports": invalid, "unsupported_items": missing,
            "limitations": str(answer.get("limitations", "")), "source_binding_complete": not invalid and not missing}


def validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError("Missing operation specification")
    public(spec)
    for key in ("name", "description", "when_to_use", "requirements", "limitations"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError("Operation specification missing " + key)
    # Operation-name case is transport metadata, not a biomedical judgment.
    # Keep the raw Manager decision unchanged; normalize only the code identifier.
    spec = {**spec, "name": spec["name"].strip().lower()}
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", spec["name"]):
        raise ValueError("Use a generic lowercase operation name")
    for key in ("input_schema", "output_schema"):
        if not isinstance(spec.get(key), dict):
            raise ValueError("Missing JSON schema for " + key)
    if len(spec["requirements"]) < 40:
        raise ValueError("Operation requirements are too vague")
    return spec


def validate_cases(cases):
    if not isinstance(cases, list) or not 6 <= len(cases) <= 16:
        raise ValueError("Verifier must provide 6 to16 independent synthetic cases")
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("input"), dict):
            raise ValueError("Each test requires a JSON object input")
        if "expected" not in case and case.get("expected_error") != "ValueError":
            raise ValueError("Test requires expected JSON output or ValueError")
        public(case)
    if len({fingerprint(c["input"]) for c in cases}) != len(cases):
        raise ValueError("Repeated verifier inputs do not provide independent cases")
    return cases


def make_tests(cases):
    """Build trusted test code from verifier JSON; no verifier/Builder code executes."""
    validate_cases(cases)
    prefix = '''import copy,json,runpy,resource
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
FN=runpy.run_path('/work/candidate.py')['run']
CASES=json.loads(CASE_LITERAL)
def check_case(index):
 c=CASES[index]; payload=copy.deepcopy(c['input']); original=copy.deepcopy(payload)
 try: out=FN(payload)
 except ValueError:
  assert c.get('expected_error')=='ValueError',repr(c)
  assert payload==original,'Input mutated on rejection'
  return
 assert 'expected' in c,'Expected ValueError for '+repr(c)
 assert payload==original,'Input mutated for '+repr(c)
 assert out==c['expected'],'Input='+repr(original)+' expected='+repr(c['expected'])+' actual='+repr(out)
 assert FN(copy.deepcopy(original))==out,'Nondeterministic result'
 json.dumps(out,allow_nan=False)
'''.replace("CASE_LITERAL", repr(json.dumps(cases, ensure_ascii=False)))
    functions = "\n".join("def test_case_%02d():\n check_case(%d)\n" % (i, i) for i in range(len(cases)))
    runner = '''
if __name__=='__main__':
 results=[]
 for name,fn in sorted(list(globals().items())):
  if name.startswith('test_') and callable(fn):
   try: fn(); results.append({'test':name,'status':'PASS'})
   except Exception as exc: results.append({'test':name,'status':'FAIL','error':type(exc).__name__+': '+str(exc)})
 failed=sum(x['status']=='FAIL' for x in results)
 print(json.dumps({'tests':results,'passed':len(results)-failed,'failed':failed}))
 raise SystemExit(1 if failed else 0)
'''
    return prefix + "\n" + functions + runner


def source_groups_disjoint(a, b):
    return bool(a) and bool(b) and not set(a).intersection(b)


def candidate_gate(original, matched, after, validation, review):
    reasons = []
    if after <= original + 1e-12:
        reasons.append("no_original_task_gain")
    if after < matched - 1e-12:
        reasons.append("worse_than_same_evidence_Qwen_control")
    if not validation.get("source_binding_complete"):
        reasons.append("final_answer_has_unbound_items")
    if not review.get("supported"):
        reasons.append("semantic_reviewer_did_not_confirm_support")
    genuine = bool(review.get("supported")) and review.get("change_kind") in {"missing_supported_item", "unsupported_item_removed", "condition_corrected"}
    if not genuine:
        reasons.append("no_supported_capability_repair")
    return {"enter_trial": not reasons, "reasons": reasons, "genuine_answer_repair": genuine,
            "original_delta_f1": after - original, "same_evidence_delta_f1": after - matched,
            "interpretation": "Equal-score Qwen control does not establish unique code accuracy benefit"}


def trial_gate(discovery_sources, task_sources, used, before, after, binding_ok):
    if not used:
        return "not_applicable"
    if not source_groups_disjoint(discovery_sources, task_sources):
        return "overlapping_source_not_counted"
    if not binding_ok or after < before - 1e-12:
        return "regression"
    return "pass"


def build_candidate(root, run, build_dir, spec, cases, parent=None):
    """Coder writes code; existing frozen Builder helper executes immutable tests."""
    import shutil
    import subprocess
    import sys
    from uuid import uuid4
    from run_formal_list import atomic, load, sha
    from model_service import ensure
    validate_spec(spec)
    validate_cases(cases)
    build_dir.mkdir(parents=True, exist_ok=False)
    if parent:
        previous = load(Path(parent["verification_cases"]))
        combined = previous + [c for c in cases if fingerprint(c["input"]) not in {fingerprint(p["input"]) for p in previous}]
    else:
        combined = cases
    # Cap applies to each verifier round; retained historical tests remain intact.
    fixture_path = build_dir / "verification_cases.json"
    atomic(fixture_path, combined)
    test_path = build_dir / "independent_tests.py"
    if len(combined) <= 16:
        test_path.write_text(make_tests(combined), encoding="utf-8")
    else:
        # make_tests bounds newly proposed suites; reuse its trusted renderer with
        # a small valid placeholder and replace only the JSON literal afterwards.
        source = make_tests(cases)
        source = source.replace(repr(json.dumps(cases, ensure_ascii=False)), repr(json.dumps(combined, ensure_ascii=False)), 1)
        start = source.index("def test_case_00():")
        end = source.index("if __name__=='__main__':")
        source = source[:start] + "\n".join("def test_case_%02d():\n check_case(%d)\n" % (i, i) for i in range(len(combined))) + source[end:]
        test_path.write_text(source, encoding="utf-8")
    specification = json.dumps(spec, ensure_ascii=False, indent=2) + "\nImplement run(payload:dict). Do not infer medical facts; only execute the documented operation. Preserve inputs and deterministic JSON output. Raise ValueError for invalid inputs according to this specification. Nonempty docstring must state limitations. No files, network, model calls, dynamic imports or import-time execution."
    atomic(build_dir / "spec.json", {"trigger": "Qwen_Manager_actual_failure", "specification": specification,
                                     "parent_manifest": parent, "reference_answers_supplied": False})
    name = "open_" + spec["name"] + "_" + uuid4().hex[:8]
    code_path = root / "tools/candidates" / (name + "_v001.py")
    if parent:
        assert sha(Path(parent["code_path"])) == parent["sha256"]
        shutil.copy2(parent["code_path"], code_path)
    ensure("builder", build_dir / "services")
    helper = Path(__file__).resolve().parent / 'evolve_tool_stream.py'
    if not helper.exists():
        helper = root / 'scripts/evolve_tool_stream.py'
    command = [sys.executable, str(helper), "--candidate", str(code_path),
               "--spec", str(build_dir / "spec.json"), "--tests", str(test_path), "--max-repairs", "3", "--plain-prompt",
               "--diagnose-first", "--diagnoser-model", "medtool-qa"]
    if not parent:
        command.append("--fresh")
    proc = subprocess.run(command, capture_output=True, text=True, timeout=1500)
    atomic(build_dir / "builder_process.json", {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
    ensure("qa", build_dir / "services_restore")
    found = re.findall(r"Summary: (.+)", proc.stdout)
    if not found:
        raise RuntimeError("Builder did not produce a traceable summary")
    summary_path = Path(found[-1].strip())
    summary = load(summary_path)
    atomic(build_dir / "builder_summary.json", summary)
    if summary["status"] != "functional_pass_pending_task_validation":
        return None
    manifest = load(Path(summary["manifest"]))
    manifest.update(operation=spec, verification_cases=str(fixture_path), builder_summary=str(summary_path),
                    parent_sha256=parent["sha256"] if parent else None, replay_verified=False,
                    status="experimental_functional_pass", source_spec_sha256=sha(build_dir / "spec.json"))
    atomic(build_dir / "manifest.json", manifest)
    return build_dir / "manifest.json"

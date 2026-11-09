"""Read-only, standard-library review: hashes and independent stored-result checks.

This script never executes generated candidate code and never calls a model.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True

ROOT=Path(__file__).resolve().parents[1]
REMOTE=Path('/home/supervisor/project/sy/MedToolEvo')
CASES={
    'numeric':('engineering_case_20261109','engineering_weighted_case_20261109T095954','engineering_oracle'),
    'anchors':('anchor_case_20261109','engineering_anchor_case_v3_20261109T113122','anchor_oracle'),
    'policy':('policy_case_20261109','engineering_policy_case_20261109T121042','policy_oracle'),
}


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def reference(run,name):
    path=run/'code_snapshot'/(name+'.py')
    spec=importlib.util.spec_from_file_location('review_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def evidence_path(base,remote):
    rel=Path(remote).relative_to(REMOTE);path=base/'evidence'/rel
    assert path.resolve().is_relative_to(base.resolve())
    return path


def main():
    inventory=read(ROOT/'FILE_MANIFEST.json')
    for row in inventory['files']:
        path=ROOT/row['path'];assert path.is_file() and sha(path)==row['sha256'],row['path']
    out={'tracked_payload_hashes_verified':len(inventory['files']),'model_calls':0,'candidate_code_executed':False,'cases':{}}
    for name,(folder,rid,oracle_name) in CASES.items():
        base=ROOT/folder;run=base/'evidence/runs'/rid;a=read(run/'case_acceptance.json');assert a['pass']
        build=read(run/'builds/candidate/builder_summary.json');manifest=read(evidence_path(base,a['manifest']))
        code=evidence_path(base,manifest['code_path']);tests=run/'builds/candidate/independent_tests.py'
        assert sha(code)==manifest['sha256'];assert sha(tests)==build['test_sha256']
        checker=reference(run,oracle_name)
        before,retry,repair=read(run/'baseline.json'),read(run/'qwen_retry.json'),read(run/'original_repair.json')
        if name=='numeric':
            expected=checker.oracle(read(run/'task.json')['payload'])
            scores=[checker.evaluate(v,expected)['correct'] for v in [before['answer'],retry['answer'],repair['after']]]
            assert scores==[0,0,4]
        elif name=='anchors':
            expected=checker.oracle(read(run/'task.json')['fixed_source_queue'][0]['payload'])
            scores=[checker.evaluate(v,expected)['correct_groups'] for v in [before['answer'],retry['answer'],repair['after']]]
            assert scores==[1,1,7]
            audit=read(base/'posthoc_boundary_audit.json');assert audit['passed']==2 and audit['total']==5
        else:
            task=read(run/'task.json');expected={}
            for i,q in enumerate(task['queries']):
                p=read(run/'updated_tool_calls'/('query_'+str(i))/'input.json')
                expected[q['query_id']]=checker.oracle(p)
                assert read(run/'updated_tool_calls'/('query_'+str(i))/'output.json')==expected[q['query_id']]
            after=read(run/'api/policy/tool_executor/outcome.json')['parsed']
            scores=[checker.evaluate(v,expected)['correct'] for v in [before['answer'],retry['answer'],after]]
            assert scores==[6,6,12]
            parent=read(run/'parent_manifest.json');assert sha(evidence_path(base,parent['code_path']))==a['parent_sha256']==build['history'][0]['sha256']
            assert sha(run/'builds/candidate/legacy_original_tests.py')==parent['test_sha256']
        out['cases'][name]={'stored_results_independently_recomputed':scores,'code_sha256':sha(code),'test_sha256':sha(tests),'development_acceptance':True}
    snapshot=read(ROOT/'formal_snapshot/SNAPSHOT.json')
    out['formal_snapshot']={'captured_utc':snapshot['observed_utc'],'completed':snapshot['result_count'],
        'formal_stable_tools':snapshot['formal_stable_tools'],'partial_snapshot':snapshot['partial_snapshot']}
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

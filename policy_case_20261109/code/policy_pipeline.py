"""Third development lifecycle: extend a real existing ledger, retaining old tests."""
import argparse
import copy
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
from uuid import uuid4

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/supervisor/project/sy/MedToolEvo')
sys.path.insert(0,str(HERE))
from run_formal_list import Study,atomic,load,sha
from contract_guard import GuardMixin,validate_spec,audit_cases
from closed_loop_core_v5_1 import validate_cases,make_tests,public
from schema_support import check_data
from model_service import ensure
from runtime_tools import call_tool
from policy_oracle import oracle,evaluate
from policy_fixtures import fixed_inputs
from policy_protocol import INPUT_SCHEMA,OUTPUT_SCHEMA,RELATIONS,METHOD,ANNOTATOR,EXECUTOR,MANAGER,COMPILER,TEST_DESIGNER,REVIEW


class PolicyStudy(GuardMixin,Study):
    def __init__(self,run,task_dir,pilot_run,pilot_completed):
        self.run=run;run.mkdir(parents=True,exist_ok=False)
        self.task_dir,self.pilot_run,self.pilot_completed=task_dir,pilot_run,pilot_completed
        self.task=load(task_dir/'task.json');self.private_audit=load(task_dir/'private_annotation_audit.json')
        self.parent_path=Path(self.task['parent_registry']);self.parent=load(self.parent_path)
        assert sha(Path(self.parent['code_path']))==self.parent['sha256']
        assert sha(HERE/'legacy_regression.py')==self.parent['test_sha256']
        self.registry=run/'development_registry';self.registry.mkdir()
        self.context,self.generation_calls,self.builds=16384,0,0
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.state={'stage':'policy_case','events':[],'candidates':[],'full_started':False}
        self.status={'status':'running','phase':'initializing'}
        atomic(run/'task.json',self.task);atomic(run/'parent_manifest.json',self.parent)
        atomic(run/'protocol.json',{'scope':'third real-source derived development engineering case, not original medicalQA',
            'models':{'semantics':'Qwen3.5-27B','code':'Qwen3-Coder-30B'},'method':METHOD,
            'parent_code_sha256':self.parent['sha256'],'legacy_test_sha256':self.parent['test_sha256'],
            'code_repairs':3,'registration':'development extension only','full_authorized':False,
            'primary_goal':self.task['primary_goal'],'manual_intervention':self.task['manual_intervention'],
            'test_policy':'Retain exact10 old named regression tests; new Qwen-designed inputs plus preset boundary inputs get oracle-derived expectations and freeze before code.',
            'interpretation':'Tool-level policy failure and Qwen manual answers measured separately; do not assume Qwen is inferior. Citation membership is not clinical efficacy.',
            'hashes':{p.name:sha(p) for p in HERE.glob('*.py')}})
        for p in HERE.glob('*.py'):
            dest=run/'code_snapshot'/p.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(p.read_bytes())
        self.progress()

    def progress(self):
        self.status.update(stage='policy_case',full_started=False,full_completed=0,full_total=1130,
            pilot_completed=self.pilot_completed,pilot_total=100,pilot_passed=False,pilot_source_run=str(self.pilot_run),
            full_requires_100_pilot=True,qa_requests=self.generation_calls,build_attempts=self.builds,stable_tools=0,pending_tools=0,
            development_registered_tools=sum(load(p).get('status')=='development_registered' for p in self.registry.glob('*.json')),
            updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        atomic(self.run/'progress.json',self.status);atomic(self.run/'state.json',self.state)

    def event(self,name,**data):
        e={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':name,**data};self.state['events'].append(e)
        with (self.run/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
        self.progress();print(json.dumps(e,ensure_ascii=False),flush=True)

    def ask(self,key,system,body,max_tokens=4096):
        public(body);ensure('qa',self.run/'services');self.status['phase']=key.rsplit('/',1)[-1];self.progress()
        return super().ask(key,system,body,max_tokens)

    def annotate(self,source,label):
        assert hashlib.sha256(source['xml'].encode()).hexdigest()==source['source_sha256']
        errors=None
        for attempt in range(3):
            key='policy/'+label+('/annotate' if attempt==0 else '/annotate_retry_'+str(attempt))
            result=self.ask(key,ANNOTATOR,{'source':source,'relation_vocabulary':RELATIONS,'previous_audit_feedback':errors,
                'instruction':'Polarity describes whether the relationship is asserted, not whether a clinical characteristic is desirable. Never change study membership.'},4096)
            atomic(self.run/(label+'_annotation_'+str(attempt)+'.json'),result)
            by_id={a['group_id']:a for a in result['annotations']}
            expected=self.private_audit[label]
            bad=[gid for gid,meaning in expected.items() if gid not in by_id or [by_id[gid]['relation'],by_id[gid]['polarity']]!=meaning]
            if len(by_id)!=len(result['annotations']) or set(by_id)!=set(expected):bad+=['group ID set/duplicates']
            if not bad:
                self.event('source_annotations_verified',source=source['source_id'],groups=len(by_id),semantic_model='Qwen3.5-27B')
                return by_id
            errors={'recheck_group_ids':bad,'instruction':'Re-read the explicit relation attached to each indexed bracket in original XML; no expected label or result is supplied.'}
            self.event('annotation_audit_rejected',source=source['source_id'],attempt=attempt,recheck=bad)
        raise RuntimeError('Source semantic annotations did not pass preset source audit')

    def payload(self,source,annotations,policy=None):
        evidence=[];entries=[]
        for g in source['groups']:
            a=annotations[g['group_id']]
            evidence.append({'evidence_id':g['evidence_id'],'text':source['xml']})
            for member in g['members']:
                entries.append({'name':member,'group_id':member,'evidence_id':g['evidence_id'],'quote':g['quote'],
                    'eligible':True,'relation':a['relation'],'polarity':a['polarity'],'scope':source['source_id']})
        result={'evidence':evidence,'entries':entries}
        if policy is not None:result['policy']=policy
        return result

    def packet(self,source,annotations,queries):
        groups=[{'group_id':g['group_id'],'evidence_id':g['evidence_id'],'members':g['members'],
            'relation':annotations[g['group_id']]['relation'],'polarity':annotations[g['group_id']]['polarity']} for g in source['groups']]
        return {'question':self.task['question'],'policy_rules':METHOD,
                'original_source':{'source_id':source['source_id'],'xml':source['xml']},
                'shared_observations':{'scope':source['source_id'],'groups':groups},'queries':queries}

    def actual_queries(self,manifest,source,annotations,queries,folder,check_expected=True):
        answers=[]
        for i,q in enumerate(queries):
            payload=self.payload(source,annotations,q['policy'])
            result=call_tool(manifest,payload,self.run/folder/('query_'+str(i)))
            if check_expected:assert result==oracle(payload),'Actual extended ledger violates source policy'
            answers.append({'query_id':q['query_id'],'result':result})
        return {'answers':answers}

    def compile_operation(self,intent):
        draft=self.ask('policy/algorithm_contract',COMPILER,{'fixed_rules':METHOD,'manager_steps':intent['deterministic_steps'],
            'input_schema':INPUT_SCHEMA,'output_schema':OUTPUT_SCHEMA,'old_interface':'No policy: original evidence/entries ledger contract unchanged.'},3072)
        op=validate_spec({'name':intent['operation_name'],'description':'Backward-compatible evidence ledger with optional scoped signed-relation policy.',
            'when_to_use':'Conjunction, disjunction and exclusion over explicit runtime source-bound fact annotations.',
            'limitations':'Supplied annotations can be wrong; not medical inference. Missing facts are not negative facts.',
            'semantic_preprocessor':None,'code_contract':{'input_schema':INPUT_SCHEMA,'output_schema':OUTPUT_SCHEMA,
                'algorithm':METHOD+'\nQwen compiled extension:\n'+draft['algorithm'],
                'invariants':draft['invariants'],'edge_cases':draft['edge_cases']}})
        atomic(self.run/'operation.json',op);return op

    def independent_tests(self,operation):
        extra=self.ask('policy/test_inputs',TEST_DESIGNER,{'operation':operation},3072)
        atomic(self.run/'verifier_inputs.json',extra)
        assert extra['approve'] and len(extra['inputs'])==2
        inputs=fixed_inputs()+[r['payload'] for r in extra['inputs']]
        cases=[]
        for payload in inputs:
            try:value=oracle(payload)
            except ValueError:cases.append({'input':payload,'expected_error':'ValueError'})
            else:cases.append({'input':payload,'expected':value})
        validate_cases(cases);assert not audit_cases(operation,cases)
        atomic(self.run/'new_test_cases.json',cases)
        self.event('independent_tests_frozen',new_cases=len(cases),legacy_named_tests=10,
            expected_from_independent_rules=True,legacy_test_sha256=self.parent['test_sha256'])
        return cases

    def build_extension(self,operation,cases):
        d=self.run/'builds/candidate';d.mkdir(parents=True)
        source=Path(self.parent['code_path']);assert sha(source)==self.parent['sha256']
        name='evolved_'+operation['name']+'_'+uuid4().hex[:8]
        candidate=ROOT/'tools/candidates'/(name+'_v004.py');shutil.copyfile(source,candidate)
        assert sha(candidate)==self.parent['sha256']
        original=(HERE/'legacy_regression.py').read_text();assert sha(HERE/'legacy_regression.py')==self.parent['test_sha256']
        retained=original.split('results=[]',1)[0]
        rendered=make_tests(cases);split=rendered.index("if __name__=='__main__':")
        tests=d/'independent_tests.py';tests.write_text(rendered[:split]+'\n# Exact old test definitions, imports and helpers retained below.\n'+retained+'\n'+rendered[split:])
        shutil.copyfile(HERE/'legacy_regression.py',d/'legacy_original_tests.py')
        atomic(d/'verification_cases.json',cases)
        spec={'name':operation['name'],'description':operation['description'],'when_to_use':operation['when_to_use'],
              'requirements':operation['requirements'],'input_schema':operation['input_schema'],
              'output_schema':operation['output_schema'],'limitations':operation['limitations']}
        atomic(d/'spec.json',{'trigger':'Qwen_Manager_extend_existing_tool_after_actual_policy_failure',
            'specification':json.dumps(spec,ensure_ascii=False,indent=2)+'\nExtend actual current run(payload). Preserve exact old no-policy behavior and unchanged old tests. Only add generic optional-policy capability. No real source identifiers, clinical constants, files, network or model calls. Nonempty docstring states limitations.',
            'parent_manifest':str(self.parent_path),'parent_code_sha256':self.parent['sha256']})
        atomic(d/'lineage.json',{'parent_manifest':str(self.parent_path),'parent_version':self.parent['version'],
            'parent_code_sha256':self.parent['sha256'],'initial_existing_copy':str(candidate),
            'initial_copy_sha256':sha(candidate),'old_named_tests':10,'old_test_sha256':self.parent['test_sha256'],
            'old_test_definitions_sha256':hashlib.sha256(retained.encode()).hexdigest(),
            'new_cases':len(cases),'combined_test_sha256':sha(tests),'no_manual_candidate_edits':True})
        self.builds+=1;self.status['phase']='Coder_extends_existing_tool';self.progress()
        ensure('builder',d/'services')
        cmd=[sys.executable,str(HERE/'evolve_tool_stream.py'),'--candidate',str(candidate),'--spec',str(d/'spec.json'),
            '--tests',str(tests),'--max-repairs','3','--plain-prompt','--diagnose-first','--diagnoser-model','medtool-qa']
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=1500)
        atomic(d/'builder_process.json',{'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        ensure('qa',d/'restore_services')
        found=re.findall(r'Summary: (.+)',p.stdout)
        if not found:raise RuntimeError('Extension Builder did not produce traceable summary')
        summary=load(Path(found[-1].strip()));atomic(d/'builder_summary.json',summary)
        if summary['status']!='functional_pass_pending_task_validation':raise RuntimeError('Existing-tool extension exhausted frozen repair budget')
        manifest=load(Path(summary['manifest']));manifest.update(operation=operation,parent_manifest=str(self.parent_path),
            parent_version=self.parent['version'],parent_sha256=self.parent['sha256'],verification_cases=str(d/'verification_cases.json'),
            legacy_test_sha256=self.parent['test_sha256'],combined_tests=str(tests),status='development_extension_pending_admission',replay_verified=False)
        atomic(d/'manifest.json',manifest)
        assert summary['history'][0]['sha256']==self.parent['sha256'] and manifest['sha256']!=self.parent['sha256']
        self.state['candidates']=[{'name':operation['name'],'status':'functional_pass','manifest':str(d/'manifest.json')}]
        self.event('extension_functional_passed',old_regression_tests=10,new_tests=len(cases),
            parent_sha256=self.parent['sha256'],new_sha256=manifest['sha256'])
        return d/'manifest.json'

    def fresh_reuse(self,manifest,source,annotations,queries,label):
        batch=[{'query_id':q['query_id'],'payload':self.payload(source,annotations,q['policy'])} for q in queries]
        ip=self.run/('reload_'+label+'_input.json');atomic(ip,batch)
        script="import json,sys,os;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from runtime_tools import call_tool;rows=json.loads(Path(sys.argv[3]).read_text());out=[{'query_id':r['query_id'],'result':call_tool(Path(sys.argv[2]),r['payload'],Path(sys.argv[4])/str(i))} for i,r in enumerate(rows)];print(json.dumps({'pid':os.getpid(),'answers':out}))"
        proc=subprocess.run([sys.executable,'-c',script,str(HERE),str(manifest),str(ip),str(self.run/('reload_'+label+'_calls'))],capture_output=True,text=True,timeout=120)
        atomic(self.run/('reload_'+label+'_process.json'),{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr});assert proc.returncode==0
        result=json.loads(proc.stdout);expected={r['query_id']:oracle(r['payload']) for r in batch}
        assert result['pid']!=__import__('os').getpid() and evaluate(result,expected)['pass']
        answer=self.ask('policy/reuse_'+label+'_executor',EXECUTOR,{**self.packet(source,annotations,queries),
            'actual_reloaded_tool_output':{'answers':result['answers']}},6144)
        assert evaluate(answer,expected)['pass']
        self.event('reloaded_extension_reused',input=label,fresh_pid=result['pid'],queries=len(queries))
        return {'label':label,'fresh_pid':result['pid'],'actual_output':result,'executor_answer':answer}

    def run_pipeline(self):
        source=self.task['main_source'];annotations=self.annotate(source,'main')
        atomic(self.run/'shared_annotations.json',annotations)
        queries=self.task['queries'];expected={q['query_id']:oracle(self.payload(source,annotations,q['policy'])) for q in queries}
        atomic(self.run/'offline_oracle.json',expected)
        old=self.actual_queries(self.parent_path,source,annotations,queries,'old_tool_calls',False)
        old_score=evaluate(old,expected);atomic(self.run/'old_tool_results.json',{'output':old,'evaluation':old_score})
        assert not old_score['pass'],'Old tool already solves all policies; no failure manufactured'
        self.event('existing_tool_failed_new_requirements',**old_score)
        old_union=old['answers'][0]['result']
        assert all(r['result']==old_union for r in old['answers'])
        packet=self.packet(source,annotations,queries)
        observed={'same_union_for_all_policies':old_union,'deduplication_note':'Lossless: all actual old per-policy executions returned this identical union; full calls retained.'}
        baseline=self.ask('policy/baseline_executor',EXECUTOR,{**packet,'actual_old_tool_outputs':observed},8192)
        retry=self.ask('policy/retry_executor',EXECUTOR,{**packet,'actual_old_tool_outputs':observed,'previous_answer':baseline,
            'instruction':'Independently recheck the same source and annotations. Manual reasoning is allowed. No updated tool exists yet.'},8192)
        base_score,retry_score=evaluate(baseline,expected),evaluate(retry,expected)
        atomic(self.run/'baseline.json',{'answer':baseline,'evaluation':base_score});atomic(self.run/'qwen_retry.json',{'answer':retry,'evaluation':retry_score})
        intent=self.ask('policy/manager_intent',MANAGER,{**packet,'library':[{'name':'evidence_ledger','version':self.parent['version'],
            'code_sha256':self.parent['sha256'],'current_operation':'Exact quote validation, boolean eligible filtering, group union; no signed relation/scope/runtime policy.'}],
            'actual_old_tool_outputs':observed,'old_policy_checks':old_score,'initial_Executor_evaluation':base_score,'same_evidence_retry_evaluation':retry_score,
            'compatibility_requirement':'Optional policy extension must retain exact no-policy behavior and all10 old regression tests.'},2048)
        atomic(self.run/'manager.json',intent);self.event('update_object_selected',action=intent['action'],target=intent['target'],diagnosis=intent['diagnosis'])
        assert intent['action']=='extend' and intent['target'] in ['evidence_ledger',self.parent['tool'],self.parent['version']], 'Manager did not select existing-tool extension; do not force update'
        operation=self.compile_operation(intent);cases=self.independent_tests(operation);manifest=self.build_extension(operation,cases)
        actual=self.actual_queries(manifest,source,annotations,queries,'updated_tool_calls')
        after=self.ask('policy/tool_executor',EXECUTOR,{**packet,'actual_updated_tool_outputs':actual},8192)
        after_score=evaluate(after,expected);assert after_score['pass']
        controls=[]
        for i,indices in enumerate([[0],[1,2],[0,1,2]]):
            p=self.payload(source,annotations);p['entries']=[p['entries'][j] for j in indices]
            a=call_tool(self.parent_path,p,self.run/'controls'/('old_'+str(i)))
            b=call_tool(manifest,p,self.run/'controls'/('new_'+str(i)))
            assert a==b==oracle(p);controls.append({'input':p,'old':a,'updated':b,'same':True})
        atomic(self.run/'controls.json',controls)
        review=self.ask('policy/semantic_review',REVIEW,{**packet,'actual_old_output':observed,'actual_new_output':actual,
            'old_regression_tests_passed':10,'legacy_control_equalities':3,'initial_Executor_evaluation':base_score,
            'final_Executor_matches_actual_outputs':after_score['pass']},2048)
        assert all(review[k] is True for k in ['supported','tool_gap_repaired','legacy_preserved','annotations_supported'])
        atomic(self.run/'original_repair.json',{'old_tool':old_score,'initial_Qwen':base_score,'same_annotation_retry':retry_score,
            'updated_tool':evaluate(actual,expected),'after_Qwen':after_score,'review':review,
            'QA_improvement_observed':after_score['correct']>base_score['correct']})
        learned=load(manifest);learned.update(status='development_registered',replay_verified=True,
            scope='Backward-compatible signed-policy engineering extension; no formal medicalQA/stable claim',
            admission_report=str(self.run/'original_repair.json'))
        registered=self.registry/'evidence_ledger.json';atomic(registered,learned)
        self.state['candidates'][0].update(status='development_registered',development_manifest=str(registered))
        self.event('development_extension_registered',parent_version=self.parent['version'],new_sha256=learned['sha256'])
        reused=[self.fresh_reuse(registered,source,annotations,[queries[1],queries[-2]],'new_policies')]
        other=self.task['reuse_source'];other_annotations=self.annotate(other,'reuse')
        reused.append(self.fresh_reuse(registered,other,other_annotations,self.task['reuse_queries'],'cross_source'))
        atomic(self.run/'reuse.json',reused)
        assert sha(Path(self.parent['code_path']))==self.parent['sha256'] and sha(HERE/'legacy_regression.py')==self.parent['test_sha256']
        summary=load(self.run/'builds/candidate/builder_summary.json')
        report={'pass':True,'scope':'development existing-tool evolution lifecycle','medical_qa_result':False,'bioasq_result':False,
            'parent_version':self.parent['version'],'parent_sha256':self.parent['sha256'],'new_sha256':learned['sha256'],
            'old_tool_correct':old_score['correct'],'new_tool_correct':len(queries),'policy_queries':len(queries),
            'initial_Qwen_correct':base_score['correct'],'retry_Qwen_correct':retry_score['correct'],'after_Qwen_correct':after_score['correct'],
            'legacy_tests_passed':10,'new_functional_tests':len(cases),'test_count':summary['test_count'],'repair_calls':summary['repair_calls'],
            'legacy_controls_equal':3,'development_registered_tools':1,'fresh_process_reuses':2,'cross_source_reuse':True,
            'original_parent_unchanged':True,'stable_registered_tools':0,'pilot100_passed':False,'full_authorized':False,'manifest':str(registered)}
        atomic(self.run/'case_acceptance.json',report);self.status.update(status='policy_case_passed',phase='completed');self.event('existing_tool_evolution_completed',passed=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--task-dir',type=Path,required=True)
    p.add_argument('--pilot-run',type=Path,required=True);p.add_argument('--pilot-completed',type=int,required=True);a=p.parse_args()
    with (ROOT/'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);study=PolicyStudy(a.run_dir,a.task_dir,a.pilot_run,a.pilot_completed)
        try:study.run_pipeline()
        except BaseException as exc:
            for path in study.registry.glob('*.json'):
                m=load(path);m.update(status='development_rejected_after_validation',replay_verified=False,rejection_reason=str(exc));atomic(path,m)
            for c in study.state['candidates']:c.update(status='rejected',rejection_reason=str(exc))
            study.status.update(status='policy_case_failed',error=type(exc).__name__+': '+str(exc));study.event('policy_case_stopped',reason=study.status['error'])
            atomic(study.run/'case_acceptance.json',{'pass':False,'scope':'existing ledger development evolution','error':study.status['error'],'full_authorized':False});raise


if __name__=='__main__':main()

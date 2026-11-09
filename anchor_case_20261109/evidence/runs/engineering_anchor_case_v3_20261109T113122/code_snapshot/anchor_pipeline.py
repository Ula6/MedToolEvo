"""Second development lifecycle: real-prose anchor provenance, not numerical QA."""
import argparse
import copy
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/supervisor/project/sy/MedToolEvo')
sys.path.insert(0,str(HERE))
from run_formal_list import Study,atomic,load,sha
import run_closed_loop_v5_1_20261108 as bridge
from contract_guard import GuardMixin,install,validate_spec,audit_cases,COMPILER
from closed_loop_core_v5_1 import validate_cases,public
from schema_support import check_data
from model_service import ensure
from engineering_case_pipeline import without_annotations
from anchor_protocol import INPUT_SCHEMA,OUTPUT_SCHEMA,METHOD,EXECUTOR,MANAGER,VERIFIER,REVIEW
from anchor_oracle import oracle,evaluate
install(bridge)


class AnchorStudy(GuardMixin,Study):
    def __init__(self,run,task_dir,pilot_run,pilot_completed):
        self.run=run;run.mkdir(parents=True,exist_ok=False)
        self.task_dir,self.pilot_run,self.pilot_completed=task_dir,pilot_run,pilot_completed
        self.task=load(task_dir/'task.json');self.registry=run/'development_registry';self.registry.mkdir()
        self.context,self.generation_calls=16384,0
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.state={'stage':'anchor_case','events':[],'candidates':[],'full_started':False}
        self.status={'status':'running','phase':'initializing'};self.builds=0
        atomic(run/'task.json',self.task)
        atomic(run/'protocol.json',{'scope':'real-prose derived anchor-index development case, not original BioASQ/DocHopQA task',
            'implementation_revision':'v3 fixed interface plus oracle-derived synthetic expectations; same task/rules/I-O/oracle/acceptance;8 Qwen-designed inputs plus5 prebaseline CPU probes frozen before code',
            'models':{'semantics':'Qwen3.5-27B','code':'Qwen3-Coder-30B'},'method':METHOD,
            'code_repairs':3,'registration':'development only','full_authorized':False,
            'queue_policy':'Fixed1 source packets before baseline. Preserve every baseline/retry. Select only a substantive membership error that remains in same-evidence Qwen retry; otherwise continue the fixed queue without manufacturing failure.',
            'manual_intervention':'Source selection, structural question/rules, typed interface, offline oracle, controls/reuse and controller preset. No source/candidate edits, forced failures or expected index supplied to actors.',
            'infrastructure_change':'No whitelist expansion needed: quote alignment uses existing allowed unicodedata. Original frozen pilot helper is unchanged.',
            'hashes':{p.name:sha(p) for p in HERE.glob('*.py')}})
        for p in HERE.glob('*.py'):
            dest=run/'code_snapshot'/p.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(p.read_bytes())
        self.progress()

    def progress(self):
        self.status.update(stage='anchor_case',full_started=False,full_completed=0,full_total=1130,
            pilot_completed=self.pilot_completed,pilot_total=100,pilot_passed=False,pilot_source_run=str(self.pilot_run),
            full_requires_100_pilot=True,qa_requests=self.generation_calls,build_attempts=self.builds,
            stable_tools=0,pending_tools=0,development_registered_tools=sum(load(p).get('status')=='development_registered' for p in self.registry.glob('*.json')),
            updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        atomic(self.run/'progress.json',self.status);atomic(self.run/'state.json',self.state)

    def event(self,name,**data):
        event={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event':name,**data};self.state['events'].append(event)
        with (self.run/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
        self.progress();print(json.dumps(event,ensure_ascii=False),flush=True)

    def ask(self,key,system,body,max_tokens=4096):
        public(body);ensure('qa',self.run/'services');self.status['phase']=key.rsplit('/',1)[-1];self.progress()
        return super().ask(key,system,body,max_tokens)

    def packet(self,payload):
        return {'question':self.task['question'],'indexing_rules':METHOD,'public_payload':payload}

    def compile_operation(self,intent):
        answer=self.ask('anchor/algorithm_contract',
            'Compile ONLY the generic deterministic algorithm and invariants for this operation. Return JSON {algorithm:string,invariants:[string],edge_cases:[string]}. No schemas, code or source-specific values. Honor every supplied rule and exact I/O field. All semantic work remains outside code; this operation is literal Unicode/source-coordinate processing.',
            {'operation_name':intent['operation_name'],'fixed_rules':METHOD,
             'manager_steps':intent['deterministic_steps'],'fixed_input_schema':INPUT_SCHEMA,'fixed_output_schema':OUTPUT_SCHEMA},3072)
        operation={'name':intent['operation_name'],
            'description':'Generic Unicode-aware all-occurrence quote alignment with exact original source offsets.',
            'when_to_use':'When source quotes need exact original character coordinates, all hits and explicit absent-query rejection.',
            'limitations':'Literal source anchoring only; not semantic entailment or medical correctness.',
            'semantic_preprocessor':None,
            'code_contract':{'input_schema':copy.deepcopy(INPUT_SCHEMA),'output_schema':copy.deepcopy(OUTPUT_SCHEMA),
                'algorithm':METHOD+'\nQwen compiled algorithm:\n'+answer['algorithm'],
                'invariants':answer['invariants'],'edge_cases':answer['edge_cases']}}
        op=validate_spec(operation)
        atomic(self.run/'operation.json',op)
        self.event('fixed_interface_compiled',schemas_attached_from_frozen_protocol=True)
        return op

    def independent_tests(self,operation):
        source=ROOT/'runs/engineering_anchor_case_v2_20261109T112420/verifier_2.json'
        proposal=load(source)
        assert proposal['approve'] and len(proposal['cases'])==8
        inputs=[copy.deepcopy(c['input']) for c in proposal['cases']]
        def probe(text,query):
            return {'sources':[{'source_id':'S','text':text}],'queries':[{'query_id':'Q','text':query}]}
        # These five challenges are the unchanged pre-baseline CPU preflight probes.
        inputs.extend([probe('aaa','aa'),probe('\u00df','ss'),probe('\u00df','s'),
                       probe('X\uff21\t \u00a0Bz','a b'),probe('D\u2010blind','D-blind')])
        cases=[]
        for payload in inputs:
            try:expected=oracle(payload)
            except ValueError:cases.append({'input':payload,'expected_error':'ValueError'})
            else:cases.append({'input':payload,'expected':expected})
        validate_cases(cases)
        assert not audit_cases(operation,cases)
        atomic(self.run/'fixture_provenance.json',{'Qwen_input_proposal':str(source),'proposal_sha256':sha(source),
            'Qwen_designed_inputs':8,'prebaseline_CPU_boundary_inputs':5,
            'expected_values':'Derived offline by the independently checked fixed-rule oracle before any candidate exists; no Qwen expected coordinates accepted blindly.',
            'cases_sha256':hashlib.sha256(json.dumps(cases,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
            'no_previous_candidate_or_real_source_coordinates_used':True})
        self.event('independent_tests_approved',count=len(cases),oracle_checked=True,
                   expected_from_trusted_rules=True,inputs_from_Qwen_and_prebaseline_CPU_probes=True)
        return cases

    def actual_call(self,manifest,payload,directory):
        before=copy.deepcopy(payload);assert not check_data(load(manifest)['operation']['input_schema'],payload)
        output=bridge.call_tool(manifest,payload,directory)
        assert payload==before
        assert output==oracle(payload),'Generated result violates offline structural oracle'
        return output

    def run_pipeline(self):
        selected=None;attempts=[]
        for i,case in enumerate(self.task['fixed_source_queue']):
            payload=copy.deepcopy(case['payload'])
            assert hashlib.sha256(case['source_text'].encode()).hexdigest()==case['source_sha256']
            expected=oracle(payload);packet=self.packet(payload)
            before=self.ask('anchor/case_%d_baseline_executor'%i,EXECUTOR,packet,8192)
            score=evaluate(before,expected);attempts.append({'source':case['source_id'],'baseline':before,'evaluation':score})
            atomic(self.run/'baseline_attempts.json',attempts);self.event('baseline_completed',source=case['source_id'],**score)
            if score['substantive_index_error']:
                retry=self.ask('anchor/case_%d_retry_executor'%i,EXECUTOR,{**packet,'previous_answer':before,
                    'instruction':'Independently recheck every query occurrence, verbatim quote and original Unicode character span on the SAME source text. No new evidence or code tool.'},8192)
                retry_score=evaluate(retry,expected);attempts[-1].update(retry=retry,retry_evaluation=retry_score)
                atomic(self.run/'baseline_attempts.json',attempts)
                if retry_score['substantive_index_error']:
                    selected=(case,payload,expected,packet,before,score,retry,retry_score);break
                self.event('same_evidence_retry_resolved',source=case['source_id'],note='No persistent membership error; do not claim code-only benefit.')
                continue
            self.event('no_substantive_failure',source=case['source_id'],note='No failure manufactured; keep this baseline and proceed to next prespecified source.')
        if selected is None:raise RuntimeError('No persistent substantive indexing failure in fixed1 sources; no failure manufactured')
        case,payload,expected,packet,before,before_score,retry,retry_score=selected
        atomic(self.run/'selected_source.json',case);atomic(self.run/'offline_oracle.json',expected)
        atomic(self.run/'baseline.json',{'answer':before,'evaluation':before_score})
        atomic(self.run/'qwen_retry.json',{'answer':retry,'evaluation':retry_score})
        intent=self.ask('anchor/manager_intent',MANAGER,{**packet,'executor_answer':before,'retry_answer':retry,
            'independent_feedback':{'index_check_pass':False,'incorrect_groups':[r for r in before_score['group_checks'] if not r['pass']],
                                     'unique_index_exact':before_score['unique_index_exact']},
            'fixed_input_interface':INPUT_SCHEMA,'fixed_output_interface':OUTPUT_SCHEMA,
            'known_previous_development_capabilities':self.task.get('known_previous_development_capabilities',{})},1536)
        atomic(self.run/'manager.json',intent);self.event('failure_diagnosed',action=intent['action'],diagnosis=intent['diagnosis'])
        if intent['action']!='create':raise RuntimeError('Manager deferred; no tool creation forced')
        op=self.compile_operation(intent);cases=self.independent_tests(op)
        self.builds+=1;self.status['phase']='Coder_generation_and_independent_tests';self.progress()
        manifest=bridge.build_candidate(ROOT,self.run,self.run/'builds/candidate',op,cases)
        if manifest is None:raise RuntimeError('Functional repair budget exhausted; candidate rejected')
        self.state['candidates']=[{'name':op['name'],'manifest':str(manifest),'status':'functional_pass'}]
        self.event('functional_candidate_passed',manifest=str(manifest))
        output=self.actual_call(manifest,payload,self.run/'original_actual_call')
        after=self.ask('anchor/tool_executor',EXECUTOR,{**packet,'actual_generated_tool_output':output,
            'instruction':'Use the real generated-tool result while checking source identity, exact original spans and all occurrences.'},8192)
        after_score=evaluate(after,expected)
        review=self.ask('anchor/semantic_review',REVIEW,{**packet,'initial_answer':before,'final_answer':after,'actual_generated_tool_output':output},2048)
        atomic(self.run/'original_repair.json',{'before':before,'before_evaluation':before_score,'same_evidence_retry':retry,
            'retry_evaluation':retry_score,'tool_output':output,'after':after,'after_evaluation':after_score,'review':review})
        assert after_score['pass'] and before_score['substantive_index_error']
        assert all(review.get(k) is True for k in ['supported','index_repaired','source_binding_preserved'])
        self.event('original_index_repaired',before_correct=before_score['correct_groups'],after_correct=after_score['correct_groups'],total=after_score['total_groups'],retry_pass=retry_score['pass'])
        controls=[]
        for i,control in enumerate(self.task['controls']):
            cp=control['payload'];answer=self.ask('anchor/control_%d_baseline_executor'%i,EXECUTOR,self.packet(cp),3072)
            actual=self.actual_call(manifest,cp,self.run/('control_%d_call'%i));wanted=oracle(cp)
            controls.append({'construction':control['construction'],'input':cp,'baseline':answer,
                'baseline_evaluation':evaluate(answer,wanted),'tool_output':actual,'tool_evaluation':evaluate(actual,wanted)})
        assert all(c['tool_evaluation']['pass'] and c['tool_evaluation']['correct_groups']>=c['baseline_evaluation']['correct_groups'] for c in controls)
        atomic(self.run/'controls.json',controls);self.event('development_admission_passed',controls=len(controls),nonregression=True)
        learned=load(manifest);learned.update(status='development_registered',replay_verified=True,
            scope='Real-prose derived anchor-index engineering case only; not medical answer repair or formal stable registration',
            admission_report=str(self.run/'original_repair.json'),controls=str(self.run/'controls.json'))
        registered=self.registry/(op['name']+'.json');atomic(registered,learned)
        self.state['candidates'][0].update(status='development_registered',development_manifest=str(registered))
        self.event('development_tool_registered',manifest=str(registered),code_sha256=learned['sha256'])
        reuse=[]
        fresh=[('original',payload),('cross_source',self.task['reuse_payload'])]
        for name,current in fresh:
            ip=self.run/('reload_'+name+'_input.json');atomic(ip,current)
            script="import json,sys,os;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from runtime_tools import call_tool;print(json.dumps({'pid':os.getpid(),'output':call_tool(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_text()),Path(sys.argv[4]))}))"
            proc=subprocess.run([sys.executable,'-c',script,str(HERE),str(registered),str(ip),str(self.run/('reload_'+name+'_call'))],capture_output=True,text=True,timeout=90)
            atomic(self.run/('reload_'+name+'_process.json'),{'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr});assert proc.returncode==0
            result=json.loads(proc.stdout);assert result['pid']!=os.getpid() and result['output']==oracle(current)
            answer=self.ask('anchor/reuse_'+name+'_executor',EXECUTOR,{**self.packet(current),'actual_reloaded_tool_output':result['output']},8192)
            assert evaluate(answer,oracle(current))['pass']
            reuse.append({'input':name,'payload':current,'fresh_pid':result['pid'],'output':result['output'],'executor_answer':answer})
            self.event('reloaded_tool_reused',input=name,fresh_pid=result['pid'])
        atomic(self.run/'reuse.json',reuse)
        report={'pass':True,'scope':'development engineering anchor-index lifecycle only','bioasq_result':False,
            'medical_qa_repair':False,'baseline_correct_groups':before_score['correct_groups'],'after_correct_groups':after_score['correct_groups'],
            'total_groups':after_score['total_groups'],'retry_pass':retry_score['pass'],'functional_summary':str(self.run/'builds/candidate/builder_summary.json'),
            'controls_passed':len(controls),'development_registered_tools':1,'fresh_process_reuses':len(reuse),'cross_source_reuse':True,
            'stable_registered_tools':0,'pilot100_passed':False,'full_authorized':False,'manifest':str(registered),'source':case}
        atomic(self.run/'case_acceptance.json',report);self.status.update(status='anchor_case_passed',phase='completed');self.event('anchor_lifecycle_completed',passed=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--task-dir',type=Path,required=True)
    p.add_argument('--reuse-input-run',type=Path);p.add_argument('--pilot-run',type=Path,required=True);p.add_argument('--pilot-completed',type=int,required=True);a=p.parse_args()
    with (ROOT/'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);study=AnchorStudy(a.run_dir,a.task_dir,a.pilot_run,a.pilot_completed)
        if a.reuse_input_run:
            import shutil
            reused=[]
            for name in ['case_0_baseline_executor','case_0_retry_executor','manager_intent']:
                src=a.reuse_input_run/'api/anchor'/name;dest=study.run/'api/anchor'/name
                shutil.copytree(src,dest)
                reused.append({'source':str(src),'destination':str(dest),'files':{str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()}})
            atomic(study.run/'reused_observations.json',{'source_run':str(a.reuse_input_run),'policy':'Study.ask rechecks full prompt/body/schema/max-token fingerprint before reading cache; never reuse changed inputs. No previous code or expected coordinates imported.','operations':reused})
            src=ROOT/'runs/engineering_anchor_case_v2_20261109T112420/api/anchor/algorithm_contract';dest=study.run/'api/anchor/algorithm_contract'
            shutil.copytree(src,dest)
            atomic(study.run/'reused_algorithm.json',{'source':str(src),'files':{str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()},'policy':'Full request fingerprint is rechecked by Study.ask.'})
            study.generation_calls=sum(1 for _ in (study.run/'api').rglob('request.json'))
        try:study.run_pipeline()
        except BaseException as exc:
            for path in study.registry.glob('*.json'):
                record=load(path);record.update(status='development_rejected_after_reuse',replay_verified=False,rejection_reason=str(exc));atomic(path,record)
            for c in study.state['candidates']:c.update(status='rejected_development_admission',rejection_reason=str(exc))
            study.status.update(status='anchor_case_failed',error=type(exc).__name__+': '+str(exc));study.event('anchor_case_stopped',reason=study.status['error'])
            atomic(study.run/'case_acceptance.json',{'pass':False,'scope':'anchor engineering case','error':study.status['error'],'full_authorized':False,'bioasq_result':False});raise


if __name__=='__main__':main()

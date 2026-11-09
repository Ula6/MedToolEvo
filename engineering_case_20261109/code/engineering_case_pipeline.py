"""Real-source derivative engineering case; separate development registration."""
import argparse
import copy
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/supervisor/project/sy/MedToolEvo')
sys.path.insert(0, str(HERE))
from run_formal_list import Study, atomic, load, sha
import run_closed_loop_v5_1_20261108 as bridge
from contract_guard import GuardMixin, install, validate_spec, audit_cases, COMPILER
from closed_loop_core_v5_1 import validate_cases, public
from schema_support import check_data
from model_service import ensure
from engineering_protocol import METRICS, INPUT_SCHEMA, OUTPUT_SCHEMA, METHOD, EXECUTOR, MANAGER, VERIFIER, REVIEW
from engineering_oracle import oracle, evaluate
install(bridge)


def without_annotations(value):
    if isinstance(value, dict):
        return {k: (sorted(v) if k == 'required' else without_annotations(v))
                for k, v in value.items() if k not in {'description', 'title', 'default'}}
    if isinstance(value, list):
        return [without_annotations(v) for v in value]
    return value


class EngineeringStudy(GuardMixin, Study):
    def __init__(self, run, task_dir, pilot_run, pilot_completed):
        self.run = run
        run.mkdir(parents=True, exist_ok=False)
        self.task_dir, self.pilot_run, self.pilot_completed = task_dir, pilot_run, pilot_completed
        self.task = load(task_dir / 'task.json')
        self.context, self.generation_calls = 16384, 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.state = {'stage': 'engineering_case', 'events': [], 'candidates': [], 'full_started': False}
        self.status = {'status': 'running', 'phase': 'initializing'}
        self.registry = run / 'development_registry'
        self.registry.mkdir()
        self.versions = []
        atomic(run / 'task.json', self.task)
        atomic(run / 'protocol.json', {'scope': 'real-source researcher-constructed engineering case, not BioASQ',
            'models': {'semantics': 'Qwen3.5-27B', 'code': 'Qwen3-Coder-30B'},
            'context': 16384, 'numeric_tolerance': .0000005, 'code_repairs': 3,
            'registration': 'development only; never modifies original stable library or100-question gate',
            'source_construction': self.task['construction'], 'method': METHOD,
            'source_hashes': {p.name: sha(p) for p in HERE.glob('*.py')},
            'human_intervention': 'Source-row selection, derivative question/formulas, typed I/O, independent oracle and acceptance are fixed by researcher before baseline. No baseline edit, forced wrong answer or hand-written candidate code.',
            'repair_trigger': 'Only actual independent functional test failures; do not manufacture a failing version'})
        for p in HERE.glob('*.py'):
            destination = run / 'code_snapshot' / p.name
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(p.read_bytes())
        self.progress()

    def progress(self):
        self.status.update(stage='engineering_case', full_started=False, full_completed=0, full_total=1130,
            pilot_completed=self.pilot_completed, pilot_total=100, pilot_passed=False,
            pilot_source_run=str(self.pilot_run), full_requires_100_pilot=True, qa_requests=self.generation_calls,
            build_attempts=len(self.versions), stable_tools=0, pending_tools=0,
            development_registered_tools=sum(load(p).get('status') == 'development_registered' for p in self.registry.glob('*.json')),
            updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        atomic(self.run / 'progress.json', self.status)
        atomic(self.run / 'state.json', self.state)

    def event(self, name, **data):
        event = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'event': name, **data}
        self.state['events'].append(event)
        with (self.run / 'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
        self.progress()
        print(json.dumps(event, ensure_ascii=False), flush=True)

    def ask(self, key, system, body, max_tokens=3072):
        public(body)
        ensure('qa', self.run / 'services')
        self.status['phase'] = key.rsplit('/', 1)[-1]
        self.progress()
        return super().ask(key, system, body, max_tokens)

    def public_task(self, indices):
        rows = [self.task['row_provenance'][i] for i in indices]
        payload = {'rows': [{'value': r['value'], 'weight': r['weight']} for r in rows]}
        text = '\n'.join(f"{r['row_id']}: {r['label']}; mean={r['value']}; n={r['weight']}." for r in rows)
        evidence = self.task['evidence'] + [{'evidence_id': 'e2', 'source': self.task['evidence'][0]['source'],
            'text': text, 'derivation': 'Exact public cell extraction; original XML retained as e1'}]
        return {'question': self.task['question'] + '\nFor THIS invocation use ONLY public_payload.rows. Other source-table rows are context, not additional operands.',
                'public_payload': payload, 'selected_source_rows': [r['row_id'] for r in rows], 'evidence': evidence}

    def binding(self, answer, packet):
        return bool(answer.get('quote') and any(answer.get('evidence_id') == e['evidence_id']
            and answer['quote'] in e['text'] for e in packet['evidence']))

    def check_source(self):
        import xml.etree.ElementTree as ET
        text = self.task['evidence'][0]['text']
        assert hashlib.sha256(text.encode()).hexdigest() == self.task['construction']['source_sha256']
        parsed, active = [], False
        for tr in ET.fromstring(text).findall('.//tbody/tr'):
            cells = tr.findall('td')
            if len(cells) == 1 and cells[0].get('colspan'):
                active = 'System/body location' in ''.join(cells[0].itertext())
                continue
            if active:
                label, value_text = ''.join(cells[0].itertext()), ''.join(cells[1].itertext())
                parsed.append({'value': float(re.match(r'\s*([0-9]+(?:\.[0-9]+)?)', value_text).group(1)),
                               'weight': int(re.findall(r'\((\d+)\)', label)[-1])})
        assert parsed == self.task['payload']['rows']
        expected = oracle(self.task['payload'])
        assert expected == load(self.task_dir / 'oracle.json')['expected']
        atomic(self.run / 'offline_oracle.json', {'expected': expected, 'source_rows': len(parsed),
            'source_parsers': ['BeautifulSoup preparation', 'ElementTree independent replay'],
            'reference_math': 'Decimal60 precision, independently crosschecked against NumPy before baseline',
            'policy': 'Offline only, never supplied to baseline, Manager, Compiler or Builder'})
        self.event('source_verified', source_rows=len(parsed), total_weight=sum(r['weight'] for r in parsed))
        return expected

    def compile_operation(self, intent):
        proposed = {'name': intent['operation_name'], 'description': 'Generic deterministic weighted numerical summaries on explicit runtime value/weight rows.',
            'when_to_use': 'When a question requires reproducible weighted summaries of positive numerical values.',
            'requirements': METHOD + '\nManager steps:\n' + '\n'.join(intent['deterministic_steps']),
            'limitations': 'Arithmetic on supplied rounded numbers; not clinical inference or pooled patient variability.',
            'input_schema': INPUT_SCHEMA, 'output_schema': OUTPUT_SCHEMA, 'semantic_preprocessor': None}
        feedback = None
        for revision in range(3):
            result = self.ask('engineering/compile_%d' % revision, COMPILER,
                {'operation': proposed, 'fixed_input_schema': INPUT_SCHEMA, 'fixed_output_schema': OUTPUT_SCHEMA,
                 'interface_feedback': feedback,
                 'instruction': 'Preserve the supplied exact numeric I/O field names and structural constraints. Semantic preprocessor is null: all operands are already public typed data. Define deterministic code algorithm and invalid-input handling using the specified population formulas and6-decimal output. No real source values or medical facts.'}, 6144)
            op = validate_spec(result['operation'])
            if (without_annotations(op['input_schema']) == without_annotations(INPUT_SCHEMA) and
                    without_annotations(op['output_schema']) == without_annotations(OUTPUT_SCHEMA) and not op.get('semantic_preprocessor')):
                atomic(self.run / 'operation.json', op)
                return op
            feedback = 'Input/output schema must match the provided fixed numeric interface exactly; semantic_preprocessor=null.'
            self.event('interface_contract_rejected', revision=revision, reason=feedback)
        raise RuntimeError('Numeric interface compilation did not converge')

    def independent_tests(self, operation):
        feedback = None
        for revision in range(3):
            answer = self.ask('engineering/propose_tests_%d' % revision, VERIFIER,
                {'operation': operation, 'previous_fixture_feedback': feedback}, 4096)
            atomic(self.run / ('verifier_%d.json' % revision), answer)
            errors = []
            try:
                if not answer.get('approve'):
                    raise ValueError(answer.get('reason', 'Verifier declined'))
                cases = validate_cases(answer['cases'])
                errors.extend(audit_cases(operation, cases))
                for i, case in enumerate(cases):
                    try:
                        expected = oracle(case['input'])
                    except ValueError:
                        if case.get('expected_error') != 'ValueError':
                            errors.append({'case': i, 'issue': 'Input violates fixed interface; expected ValueError'})
                    else:
                        if case.get('expected') != expected:
                            errors.append({'case': i, 'issue': 'Synthetic expected result conflicts with independent arithmetic',
                                           'expected_from_definition': expected})
            except ValueError as exc:
                errors.append(str(exc))
            if not errors:
                self.event('independent_tests_approved', count=len(cases), oracle_checked=True)
                return cases
            feedback = {'issues': errors, 'previous_cases': answer.get('cases')}
            self.event('independent_fixture_rejected', revision=revision, issues=errors)
        raise RuntimeError('Independent numeric tests did not converge')

    def actual_call(self, manifest, packet, directory):
        payload = copy.deepcopy(packet['public_payload'])
        assert not check_data(load(manifest)['operation']['input_schema'], payload)
        output = bridge.call_tool(manifest, payload, directory)
        assert payload == packet['public_payload'], 'Source operands mutated'
        assert evaluate(output, oracle(payload))['pass'], 'Actual tool result failed independent source arithmetic'
        return output

    def run_pipeline(self):
        expected = self.check_source()
        packet = self.public_task(list(range(len(self.task['payload']['rows']))))
        before = self.ask('engineering/baseline_executor', EXECUTOR, packet)
        before_score = evaluate(before, expected)
        atomic(self.run / 'baseline.json', {'answer': before, 'evaluation': before_score})
        self.event('baseline_completed', correct=before_score['correct'], total=before_score['total'])
        if before_score['pass']:
            raise RuntimeError('Baseline already solves this task; no real failure to evolve. No failure manufactured.')
        retry = self.ask('engineering/retry_executor', EXECUTOR,
            {**packet, 'previous_answer': before, 'instruction': 'Independently recheck the same operands and formulas; no code tool is available yet.'})
        atomic(self.run / 'qwen_retry.json', {'answer': retry, 'evaluation': evaluate(retry, expected)})
        intent = self.ask('engineering/manager_intent', MANAGER,
            {**packet, 'executor_answer': before, 'retry_answer': retry,
             'independent_feedback': {'numeric_check_pass': False,
                'failed_fields': [k for k, v in before_score['checks'].items() if not v['pass']]},
             'fixed_input_interface': INPUT_SCHEMA, 'fixed_output_interface': OUTPUT_SCHEMA}, 1536)
        atomic(self.run / 'manager.json', intent)
        self.event('failure_diagnosed', action=intent['action'], diagnosis=intent['diagnosis'])
        if intent['action'] != 'create':
            raise RuntimeError('Manager deferred; no tool creation forced')
        operation = self.compile_operation(intent)
        cases = self.independent_tests(operation)
        self.versions.append(operation['name'])
        self.status['phase'] = 'Coder_generation_and_independent_tests'
        self.progress()
        manifest = bridge.build_candidate(ROOT, self.run, self.run / 'builds/candidate', operation, cases)
        if manifest is None:
            raise RuntimeError('Candidate exhausted functional repair budget; rejected')
        self.state['candidates'] = [{'name': operation['name'], 'manifest': str(manifest), 'status': 'functional_pass'}]
        self.event('functional_candidate_passed', manifest=str(manifest))
        output = self.actual_call(manifest, packet, self.run / 'original_actual_call')
        after = self.ask('engineering/tool_executor', EXECUTOR, {**packet, 'actual_generated_tool_output': output,
            'instruction': 'Use the actual executable result for the requested numerical fields; preserve source support and stated precision.'})
        after_score = evaluate(after, expected)
        review = self.ask('engineering/semantic_review', REVIEW,
            {**packet, 'method': METHOD, 'initial_answer': before, 'final_answer': after,
             'actual_generated_tool_output': output})
        atomic(self.run / 'original_repair.json', {'before': before, 'before_evaluation': before_score,
            'same_evidence_retry': retry, 'retry_evaluation': evaluate(retry, expected),
            'tool_output': output, 'after': after, 'after_evaluation': after_score, 'review': review})
        assert after_score['pass'] and after_score['accuracy'] > before_score['accuracy']
        assert self.binding(after, packet) and all(review.get(k) is True for k in
            ('supported', 'computation_repaired', 'source_operands_supported'))
        self.event('original_computation_repaired', before_correct=before_score['correct'], after_correct=after_score['correct'])
        controls = []
        for j, indices in enumerate(([0], [5], [10])):
            control = self.public_task(indices)
            predicted = self.ask('engineering/control_%d_baseline_executor' % j, EXECUTOR, control)
            actual = self.actual_call(manifest, control, self.run / ('control_%d_call' % j))
            control_expected = oracle(control['public_payload'])
            controls.append({'selected_rows': indices, 'baseline': predicted,
                'baseline_evaluation': evaluate(predicted, control_expected), 'tool_output': actual,
                'tool_evaluation': evaluate(actual, control_expected)})
        assert all(c['tool_evaluation']['pass'] and c['tool_evaluation']['accuracy'] >= c['baseline_evaluation']['accuracy'] for c in controls)
        atomic(self.run / 'controls.json', controls)
        self.event('development_admission_passed', controls=len(controls), nonregression=True)
        learned = load(manifest)
        learned.update(status='development_registered', replay_verified=True,
            scope='Constructed real-source engineering case; not formal BioASQ stable registration',
            admission_report=str(self.run / 'original_repair.json'), controls=str(self.run / 'controls.json'))
        registered = self.registry / (operation['name'] + '.json')
        atomic(registered, learned)
        self.state['candidates'][0].update(status='development_registered', development_manifest=str(registered))
        self.event('development_tool_registered', manifest=str(registered), code_sha256=learned['sha256'])
        reuse = []
        for name, indices in [('original', list(range(12))), ('new_subset', [2, 3, 4, 5])]:
            current = self.public_task(indices)
            input_path = self.run / ('reload_' + name + '_input.json')
            atomic(input_path, current['public_payload'])
            script = "import json,sys,os;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from runtime_tools import call_tool;print(json.dumps({'pid':os.getpid(),'output':call_tool(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_text()),Path(sys.argv[4]))}))"
            process = subprocess.run([sys.executable, '-c', script, str(HERE), str(registered), str(input_path),
                str(self.run / ('reload_' + name + '_call'))], capture_output=True, text=True, timeout=90)
            atomic(self.run / ('reload_' + name + '_process.json'), {'returncode': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr})
            assert process.returncode == 0
            result = json.loads(process.stdout)
            assert result['pid'] != os.getpid() and evaluate(result['output'], oracle(current['public_payload']))['pass']
            reused_answer = self.ask('engineering/reuse_' + name + '_executor', EXECUTOR,
                {**current, 'actual_reloaded_tool_output': result['output']})
            assert evaluate(reused_answer, oracle(current['public_payload']))['pass'] and self.binding(reused_answer, current)
            reuse.append({'input': name, 'selected_rows': indices, 'fresh_pid': result['pid'],
                          'output': result['output'], 'executor_answer': reused_answer})
            self.event('reloaded_tool_reused', input=name, fresh_pid=result['pid'])
        atomic(self.run / 'reuse.json', reuse)
        report = {'pass': True, 'scope': 'development engineering lifecycle only',
            'baseline_correct': before_score['correct'], 'after_correct': after_score['correct'], 'numeric_fields': 4,
            'functional_summary': str(self.run / 'builds/candidate/builder_summary.json'),
            'controls_passed': len(controls), 'development_registered_tools': 1, 'fresh_process_reuses': len(reuse),
            'stable_registered_tools': 0, 'bioasq_result': False, 'pilot100_passed': False, 'full_authorized': False,
            'manifest': str(registered), 'source': self.task['construction']}
        atomic(self.run / 'case_acceptance.json', report)
        self.status.update(status='engineering_case_passed', phase='completed')
        self.event('engineering_lifecycle_completed', passed=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--task-dir', type=Path, required=True)
    parser.add_argument('--pilot-run', type=Path, required=True)
    parser.add_argument('--pilot-completed', type=int, required=True)
    args = parser.parse_args()
    with (ROOT / 'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        study = EngineeringStudy(args.run_dir, args.task_dir, args.pilot_run, args.pilot_completed)
        try:
            study.run_pipeline()
        except BaseException as exc:
            for path in study.registry.glob('*.json'):
                record = load(path)
                record.update(status='development_rejected_after_reuse', replay_verified=False,
                              rejection_reason=type(exc).__name__ + ': ' + str(exc))
                atomic(path, record)
            for candidate in study.state['candidates']:
                candidate.update(status='rejected_development_admission', rejection_reason=str(exc))
            study.status.update(status='engineering_case_failed', error=type(exc).__name__ + ': ' + str(exc))
            study.event('engineering_case_stopped', reason=study.status['error'])
            atomic(study.run / 'case_acceptance.json', {'pass': False, 'scope': 'development engineering case',
                'error': study.status['error'], 'full_authorized': False, 'bioasq_result': False})
            raise


if __name__ == '__main__':
    main()

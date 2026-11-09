"""Fixed-model pilot with versioned transport, schema support and explicit provenance."""
import argparse
import copy
import fcntl
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/home/supervisor/project/sy/MedToolEvo')
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))
import run_pilot100_20261108 as pilot
from contract_guard import GuardMixin, install
from output_contracts import FACT_SCHEMA
from schema_support import check_data
from failure_authenticity import FAILURE_AUTH, assess_failure
install(pilot.base)


class ReliableStudy(GuardMixin, pilot.PilotStudy):
    def __init__(self, run, resume=False, seed_source=None):
        self.seed_source = Path(seed_source) if seed_source else None
        super().__init__(run, resume)
        if self.seed_source:
            expected = pilot.base.load(self.seed_source / 'pilot_protocol.json')['pilot_ids']
            assert expected == [t['id'] for t in self.pilot_tasks], 'The agreed100 IDs changed'
        manifest = {
            'version': 'reliability-v6.1-failure-authenticity', 'python': platform.python_version(),
            'sources': {p.name: pilot.base.sha(p) for p in sorted(HERE.glob('*.py'))},
            'dependencies': {name: importlib.metadata.version(name) for name in
                             ('jsonschema', 'referencing', 'rpds-py', 'attrs', 'jsonschema-specifications')},
            'seed_source': str(self.seed_source) if self.seed_source else None,
            'import_policy': 'Only schema-valid successful public facts with identical prompt and input; no answers, decisions, tests, code, scores, admission or registration imported.',
            'source_protocol_sha256': pilot.base.sha(self.seed_source / 'protocol.json') if self.seed_source else None,
            'weights_frozen': True, 'context': 16384, 'candidate_code_repairs': 3,
            'full_requires100_completed_and_accepted': True,
        }
        if resume:
            assert pilot.base.load(run / 'implementation_manifest.json') == manifest
        else:
            pilot.base.atomic(run / 'implementation_manifest.json', manifest)
            for source in HERE.glob('*.py'):
                shutil.copy2(source, run / 'code_snapshot' / source.name)

    def ask(self, key, system, body, max_tokens=3072):
        body = copy.deepcopy(body)
        for field in ('operation', 'previous_operation', 'executed_operation'):
            operation = body.get(field)
            if not isinstance(operation, dict) or not isinstance(operation.get('code_contract'), dict):
                continue
            code = operation['code_contract']
            for schema_name in ('input_schema', 'output_schema'):
                if operation.get(schema_name) == code.get(schema_name):
                    operation.pop(schema_name, None)
            expanded = code.get('algorithm', '') + '\nInvariants: ' + json.dumps(code.get('invariants', [])) + '\nEdge cases: ' + json.dumps(code.get('edge_cases', []))
            if operation.get('requirements') == expanded:
                operation.pop('requirements', None)
            operation['interface_note'] = 'Input/output schemas and algorithm are defined once in code_contract; the transport mirrors them when compiling.'
        # Import observations only; stricter output grammar is checked on reuse.
        if self.seed_source and '/facts_' in key:
            source = self.seed_source / 'api' / key
            outcome = source / 'outcome.json'
            if outcome.exists() and pilot.base.load(outcome).get('status') == 'ok':
                previous = pilot.base.load(outcome)['parsed']
                requests = sorted(source.glob('attempt_*/request.json'))
                exact = any((lambda m: m[0]['content'] == system and json.loads(m[1]['content']) == body)
                            (pilot.base.load(p)['messages']) for p in requests)
                if exact and not check_data(FACT_SCHEMA, previous):
                    record = self.run / 'api' / key / 'observation_import.json'
                    record.parent.mkdir(parents=True, exist_ok=True)
                    pilot.base.atomic(record, {'source': str(outcome), 'source_sha256': pilot.base.sha(outcome),
                                              'same_prompt_and_input': True, 'schema_valid': True})
                    return copy.deepcopy(previous)
        if getattr(self, '_authenticity', None) and 'capability-gap Manager' in system:
            body['source_grounded_failure_assessment'] = self._authenticity
        result = super().ask(key, system, body, max_tokens)
        if result.get('action') == 'repair' and 'active_tools' in body:
            available = body['active_tools']
            if result.get('repair_target') not in available:
                corrected = super().ask(key + '_repair_target_correction', system,
                    {**body, 'invalid_decision': result,
                     'instruction': 'A repair target must be in active_tools. Correct the action/target, or defer; do not invent an installed tool.'}, max_tokens)
                if corrected.get('action') == 'repair' and corrected.get('repair_target') not in available:
                    self.event('manager_metadata_rejected', operation=key, reason='Absent repair target after bounded correction')
                    return {'action': 'defer', 'reason': 'Invalid repair metadata; current library preserved',
                            'failure_kind': 'unresolved_manager_metadata', 'missing_operation': '',
                            'repair_target': None, 'operation': None, 'exploration_payload': None}
                return corrected
        return result

    def propose(self, task, initial, matched, facts, previous_trace, key, directory):
        assessment = self.ask(key + '/failure_authenticity', FAILURE_AUTH,
            {**self.evidence_view(task, facts), 'initial_items': initial['items'],
             'initial_supports': [{k: v for k, v in row.items() if k in ('item', 'evidence_id')} for row in initial['supports']], 'retry_items': matched['items'],
             'retry_supports': [{k: v for k, v in row.items() if k in ('item', 'evidence_id')} for row in matched['supports']]}, 3072)
        checked = assess_failure(task, assessment)
        pilot.base.atomic(directory / 'failure_authenticity.json', {'assessment': assessment, 'validation': checked})
        self.event('failure_authenticity_checked', task_id=task['id'], classification=assessment.get('classification'),
                   tool_justified=checked['allow_tool_discovery'], reason=checked['reason'])
        if not checked['allow_tool_discovery']:
            return None
        self._authenticity = assessment
        try:
            return super().propose(task, initial, matched, facts, previous_trace, key, directory)
        finally:
            self._authenticity = None

    def card(self, path):
        operation = super().card(path)
        # The requirements already include algorithm/invariants/edge cases;
        # avoid duplicating the exact same schemas and procedure in every prompt.
        return {k: copy.deepcopy(v) for k, v in operation.items() if k in {
            'name', 'description', 'when_to_use', 'requirements', 'input_schema',
            'output_schema', 'limitations', 'semantic_preprocessor'}}

    def evidence_view(self, task, facts):
        serialized = json.dumps(facts, ensure_ascii=False)
        if sum(len(e['text']) for e in task['evidence']) + len(serialized) <= 16000:
            return {'question': task['question'], 'evidence': task['evidence'], 'Qwen_records': facts}
        excerpts, records, seen = [], [], {}
        invalid = set(facts.get('invalid_record_indices', []))
        for i, record in enumerate(facts['records']):
            if i in invalid:
                continue
            span = (record['evidence_id'], record['quote'])
            if span not in seen:
                seen[span] = 's' + str(len(excerpts))
                excerpts.append({'span_id': seen[span], 'evidence_id': span[0], 'text': span[1]})
            records.append({k: v for k, v in record.items() if k != 'quote'} | {'source_span_ref': seen[span]})
        return {'question': task['question'], 'evidence': excerpts,
                'Qwen_records': {'records': records, 'coverage': facts['coverage'],
                                 'limitations': facts.get('limitations', '')},
                'context_mode': 'Every raw evidence batch was read. All retained valid records and distinct exact quotes are present once; source_span_ref points to evidence.span_id. Copy citations from that exact span and use its original evidence_id.'}

    def calibration(self, candidate, key, directory):
        checks = []
        for task in self.controls:
            folder = directory / task['id']
            folder.mkdir(parents=True, exist_ok=True)
            scoped = key + '/' + task['id']
            facts = self.fact_records(task, scoped, folder, developmental=False)
            view = self.evidence_view(task, facts)
            before = self.scored(task, self.ask(scoped + '/same_evidence_Qwen', pilot.base.ANSWER, view, 4096))
            after, used, trace = self.mounted(task, before, facts, scoped, folder / 'execution',
                                            {candidate['name']: Path(candidate['manifest'])})
            ok = (after['score']['f1'] >= before['score']['f1'] - 1e-12
                  and (not used or after['source_binding_complete']) and not (trace and trace.get('error')))
            checks.append({'task_id': task['id'], 'before': before, 'after': after,
                           'used_tools': used, 'pass': ok, 'trace': trace})
        pilot.base.atomic(directory / 'calibration.json', checks)
        return all(c['pass'] for c in checks)

    def run_pipeline(self):
        if self.state['stage'] == 'pilot100':
            for task in self.pilot_tasks:
                self.process(task, 'development')
                result = pilot.base.load(self.run / 'development/tasks' / task['id'] / 'result.json')
                if result.get('errors'):
                    self.status.update(status='pilot100_technical_error', phase='technical_checkpoint_failed')
                    self.event('pilot_technical_checkpoint_failed', task_id=task['id'], errors=result['errors'])
                    self.progress()
                    return
                count = len(list((self.run / 'development/tasks').glob('*/result.json')))
                if count == 10:
                    self.event('pilot_first10_technical_checkpoint_passed', completed=10,
                               interpretation='Technical checks only; not100 questions complete or full acceptance')
        return super().run_pipeline()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--seed-source', type=Path)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    with (ROOT / 'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        study = ReliableStudy(args.run_dir, args.resume, args.seed_source)
        try:
            pilot.base.ensure('qa', args.run_dir / 'services')
            study.run_pipeline()
        except BaseException as exc:
            study.status.update(status='stopped_error', error=type(exc).__name__ + ': ' + str(exc))
            study.save(); study.progress()
            raise


if __name__ == '__main__':
    main()

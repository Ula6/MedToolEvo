"""Regression replays of actual pilot faults; no GPU or language-model calls."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
CODE = Path(os.environ.get('MEDTOOL_TEST_CODE_DIR', HERE / 'reliability_v6_1'))
sys.path.insert(0, str(CODE))
if os.name == 'nt':
    sys.modules.setdefault('fcntl', SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=MagicMock()))
from schema_support import schema_contract, check_data, normalize_payload, assess_review
from contract_guard import validate_spec
from output_contracts import response_schema, FACT_SCHEMA
from run_formal_list import Study
from run_reliable_pilot100 import ReliableStudy, pilot
try:
    from failure_authenticity import assess_failure
except ImportError:
    assess_failure = None


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


class ActualFailureReplays(unittest.TestCase):
    def test_all_seven_actual_schema_failures_are_accepted_as_valid_schemas(self):
        faults = read(HERE / 'snapshot/run/state.json')
        task_ids = []
        for p in (HERE / 'snapshot/run/development/tasks').glob('*/result.json'):
            row = read(p)
            if any('code_contract.' in e for e in row.get('errors', [])):
                task_ids.append(row['task_id'])
        self.assertEqual(len(task_ids), 7)
        for task_id in task_ids:
            with self.subTest(task=task_id):
                candidates = sorted((HERE / 'failure_api/api/development' / task_id).glob('**/*repair_code_boundary/outcome.json'))
                self.assertTrue(candidates)
                operation = read(candidates[-1])['parsed']['operation']
                compiled = validate_spec(operation)
                self.assertIsInstance(compiled['input_schema'], dict)
                self.assertEqual(compiled['code_contract'], operation['code_contract'])

    def test_nullable_field_is_accepted_without_accepting_wrong_type(self):
        schema = {'type': ['string', 'null']}
        schema_contract(schema)
        self.assertEqual(check_data(schema, None), [])
        self.assertEqual(check_data(schema, 'A'), [])
        self.assertTrue(check_data(schema, 42))

    def test_default_is_annotation_and_never_fills_missing_required_data(self):
        schema = {'type': 'object', 'properties': {'count': {'type': 'integer', 'default': 1}}, 'required': ['count']}
        value = {}
        self.assertTrue(check_data(schema, value))
        self.assertEqual(value, {})

    def test_two_actual_array_envelopes_are_wrapped_without_changing_annotations(self):
        state = read(HERE / 'snapshot/run/state.json')
        for task_id in ['550e9d2cb305b40c5c000001', '58a71f7460087bc10a00002e']:
            with self.subTest(task=task_id):
                candidate = next(c for c in state['candidates'] if c['discovery_task'] == task_id)
                name = Path(candidate['manifest']).parent.name
                op = read(HERE / 'snapshot/run/builds' / name / 'full_operation.json')
                p = next((HERE / 'failure_api/api/development' / task_id).glob('**/semantic_preprocessor/outcome.json'))
                previous = read(p)['parsed']
                original = copy.deepcopy(previous)
                normalized, adapter = normalize_payload(previous, op['input_schema'])
                self.assertIn(adapter, {'array_argument_wrapper', 'direct_object'})
                self.assertEqual(next(iter(normalized['payload'].values())), previous['payload'])
                self.assertEqual(previous, original)
                self.assertEqual(check_data(op['input_schema'], normalized['payload']), [])

    def test_out_of_range_selection_is_a_schema_error(self):
        schema = response_schema('task/compact_000', '', {'records': [{}, {}]})
        self.assertEqual(check_data(schema, {'selected_indices': [0, 1], 'reason': ''}), [])
        self.assertTrue(check_data(schema, {'selected_indices': [0, 2], 'reason': ''}))
        self.assertTrue(check_data(schema, {'selected_indices': [True], 'reason': ''}))

    def test_transport_fits_actual_12453_token_calibration_without_dropping_input(self):
        with tempfile.TemporaryDirectory() as folder:
            study = object.__new__(Study)
            study.run = Path(folder); study.context = 16384; study.generation_calls = 0
            body = {'evidence': [{'text': 'kept in full'}], 'available_tools': {}}
            requests = []
            def api(endpoint, request):
                if endpoint == 'apply-template':
                    return {'prompt': 'unchanged prompt'}
                if endpoint == 'tokenize':
                    return {'tokens': [0] * 12453}
                requests.append(request)
                return {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"tool":null,"payload":null,"reason":"not applicable"}'}}]}
            study.api = api
            study.ask('calibration/tool_plan', 'You are the fixed Executor choosing reusable tools', body, 4096)
            self.assertEqual(requests[0]['max_tokens'], 3675)
            self.assertEqual(json.loads(requests[0]['messages'][1]['content']), body)
            self.assertIn('response_format', read(Path(folder) / 'api/calibration/tool_plan/attempt_0/request.json'))

    def test_false_ascii_review_is_not_a_counterexample(self):
        cases = [{'input': {}, 'expected': ['Z-Element', 'a-Element']}]
        review = {'approve': False, 'issues': [{'case_index': 0, 'path': '/expected',
                   'observed': ['Z-Element', 'a-Element'], 'computed': sorted(['Z-Element', 'a-Element']),
                   'rule': 'Standard ASCII sort'}], 'ambiguities': []}
        result = assess_review(review, cases, {'requirements': 'Standard ASCII sort'})
        self.assertFalse(result['veto'])
        self.assertEqual(len(result['invalid_claims']), 1)

    def test_true_differing_expectation_still_blocks_build(self):
        cases = [{'input': {}, 'expected': ['a', 'Z']}]
        review = {'approve': False, 'issues': [{'case_index': 0, 'path': '/expected',
                   'observed': ['a', 'Z'], 'computed': ['Z', 'a'], 'rule': 'Standard ASCII sort'}], 'ambiguities': []}
        self.assertTrue(assess_review(review, cases, {})['veto'])

    def test_invented_case_value_cannot_veto(self):
        claim = {'case_index': 0, 'path': '/expected', 'observed': ['invented'], 'computed': [], 'rule': 'Rule'}
        self.assertFalse(assess_review({'issues': [claim]}, [{'expected': ['A']}], {})['veto'])

    def test_quoted_true_ambiguity_still_blocks(self):
        review = {'issues': [], 'ambiguities': [{'rule_quote': 'sort alphabetically',
                   'interpretation_a': 'case sensitive', 'interpretation_b': 'case insensitive'}]}
        self.assertTrue(assess_review(review, [], {'requirements': 'sort alphabetically'})['veto'])

    def test_boolean_is_not_mistaken_for_numeric_counterexample(self):
        review = {'issues': [{'case_index': 0, 'path': '/expected', 'observed': {'ok': True},
                             'computed': {'ok': 1}, 'rule': 'Return a boolean'}]}
        self.assertTrue(assess_review(review, [{'expected': {'ok': True}}], {})['veto'])

    def test_rule_quotes_are_checked_as_text_not_json_escaped_text(self):
        review = {'ambiguities': [{'rule_quote': 'sort by "name"', 'interpretation_a': 'case sensitive',
                                   'interpretation_b': 'case insensitive'}]}
        self.assertTrue(assess_review(review, [], {'requirements': 'sort by "name"'})['veto'])

    def test_expression_only_gain_cannot_enter_trial(self):
        gate = pilot.base.candidate_gate(0, 0.5, 0.5, {'source_binding_complete': True},
                                         {'supported': True, 'change_kind': 'expression_only'})
        self.assertFalse(gate['enter_trial'])
        self.assertIn('no_supported_capability_repair', gate['reasons'])

    def test_bound_real_answer_repair_can_enter_trial(self):
        gate = pilot.base.candidate_gate(0, 0.5, 0.5, {'source_binding_complete': True},
                                         {'supported': True, 'change_kind': 'missing_supported_item'})
        self.assertTrue(gate['enter_trial'])

    def test_long_view_keeps_all_records_and_exact_spans_once(self):
        study = object.__new__(ReliableStudy)
        records = [{'name': 'A', 'quote': 'exact alpha', 'evidence_id': 'e1'},
                   {'name': 'B', 'quote': 'exact beta', 'evidence_id': 'e2'},
                   {'name': 'C', 'quote': 'exact alpha', 'evidence_id': 'e1'}]
        task = {'question': 'list?', 'evidence': [{'evidence_id': 'e1', 'text': 'x' * 20000}]}
        view = study.evidence_view(task, {'records': records, 'invalid_record_indices': [], 'coverage': {'complete': True}})
        self.assertEqual(len(view['Qwen_records']['records']), 3)
        self.assertEqual([e['text'] for e in view['evidence']], ['exact alpha', 'exact beta'])
        self.assertEqual([r['name'] for r in view['Qwen_records']['records']], ['A', 'B', 'C'])

    def test_remote_references_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'local references'):
            schema_contract({'$ref': 'https://example.org/schema'})

    def test_empty_library_cannot_name_a_repair_target(self):
        schema = response_schema('task/manager', 'You are the Qwen3.5-27B capability-gap Manager', {'active_tools': {}})
        decision = {'action': 'repair', 'reason': '', 'failure_kind': '', 'missing_operation': '',
                    'repair_target': 'nonexistent_tool', 'operation': None, 'exploration_payload': None}
        self.assertTrue(check_data(schema, decision))

    def test_runtime_error_finalizes_candidate_instead_of_leaving_functional_pass(self):
        code = {'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': True},
                'output_schema': {'type': 'array', 'items': {'type': 'string'}},
                'algorithm': 'Return a lexicographically sorted array of the supplied string records without adding new values.',
                'invariants': ['Never invent input values'], 'edge_cases': ['Empty inputs return an empty array']}
        operation = {'name': 'generic_record_sort', 'description': 'Sort prepared records', 'when_to_use': 'Prepared records',
                     'limitations': 'No semantic inference', 'code_contract': code}
        with tempfile.TemporaryDirectory() as folder:
            study = object.__new__(ReliableStudy)
            study.run = Path(folder); study.registry = Path(folder) / 'registry'; study.registry.mkdir()
            study.state = {'builds': 0, 'stage': 'pilot100', 'candidates': [], 'events': []}; study.status = {}
            study.catalog = MagicMock(return_value={}); study.save = MagicMock(); study.event = MagicMock(); study.progress = MagicMock()
            study.evidence_view = MagicMock(return_value={'question': 'q', 'evidence': []})
            study.ask = MagicMock(side_effect=([{'classification': 'coverage_gap', 'create_tool_justified': True, 'problems': [{'answer_item': 'B', 'evidence_id': 'e1', 'quote': 'B', 'description': 'Missing requested item'}], 'reason': ''}] if assess_failure else []) + [{'action': 'create', 'operation': operation, 'missing_operation': 'sort', 'reason': '', 'failure_kind': 'operation'},
                                               {'approve': True, 'cases': [{'input': {'x': i}, 'expected': []} for i in range(6)]}])
            study.mounted = MagicMock(side_effect=ValueError('Runtime payload rejected'))
            initial = {'items': [], 'supports': [], 'score': {'f1': 0}, 'source_binding_complete': True}
            with patch.object(pilot.base, 'build_candidate', return_value=Path(folder) / 'manifest.json'):
                with self.assertRaisesRegex(ValueError, 'Runtime payload rejected'):
                    study.propose({'id': 'deadbeefdeadbeefdeadbeef', 'question': 'q', 'evidence': [{'source': 'source1', 'evidence_id': 'e1', 'text': 'A and B'}]}, initial, initial,
                                  {'records': []}, None, 'task', Path(folder))
            self.assertEqual(study.state['candidates'][0]['status'], 'rejected_runtime_validation_error')

    @unittest.skipIf(assess_failure is None, 'Authenticity refinement module absent')
    def test_source_correct_answer_does_not_trigger_tool_discovery(self):
        task = {'evidence': [{'evidence_id': 'e1', 'text': 'A and B'}]}
        decision = {'classification': 'no_content_failure', 'create_tool_justified': True, 'problems': []}
        self.assertFalse(assess_failure(task, decision)['allow_tool_discovery'])

    @unittest.skipIf(assess_failure is None, 'Authenticity refinement module absent')
    def test_representation_only_is_not_an_executable_medical_failure(self):
        task = {'evidence': [{'evidence_id': 'e1', 'text': 'A and B'}]}
        decision = {'classification': 'representation_only', 'create_tool_justified': True,
                    'problems': [{'evidence_id': 'e1', 'quote': 'A', 'description': 'Different wording'}]}
        self.assertFalse(assess_failure(task, decision)['allow_tool_discovery'])

    @unittest.skipIf(assess_failure is None, 'Authenticity refinement module absent')
    def test_real_bound_coverage_failure_reaches_manager(self):
        task = {'evidence': [{'evidence_id': 'e1', 'text': 'A and B'}]}
        decision = {'classification': 'coverage_gap', 'create_tool_justified': True,
                    'problems': [{'evidence_id': 'e1', 'quote': 'B', 'description': 'Missing requested item'}]}
        self.assertTrue(assess_failure(task, decision)['allow_tool_discovery'])

    @unittest.skipIf(assess_failure is None, 'Authenticity refinement module absent')
    def test_invented_failure_quote_cannot_trigger_builder(self):
        task = {'evidence': [{'evidence_id': 'e1', 'text': 'A and B'}]}
        decision = {'classification': 'coverage_gap', 'create_tool_justified': True,
                    'problems': [{'evidence_id': 'e1', 'quote': 'C', 'description': 'Unsupported claim'}]}
        self.assertFalse(assess_failure(task, decision)['allow_tool_discovery'])

    @unittest.skipIf(assess_failure is None, 'Authenticity refinement module absent')
    def test_missing_evidence_is_not_solved_by_inventing_code(self):
        self.assertFalse(assess_failure({'evidence': []}, {'classification': 'missing_evidence',
                         'create_tool_justified': True, 'problems': []})['allow_tool_discovery'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

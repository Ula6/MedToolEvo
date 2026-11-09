"""Enforce the semantic/code boundary and audit generated test contracts."""
import copy
import hashlib
import json
import re

from closed_loop_core_v5_1 import public, validate_spec as legacy_validate, validate_cases

CONTRACT_FIELDS = {'input_schema', 'output_schema', 'algorithm', 'invariants', 'edge_cases'}
SCHEMA_KEYS = {'type', 'properties', 'required', 'items', 'additionalProperties', 'enum', 'description', 'title',
               'minItems', 'maxItems', 'minLength', 'maxLength', 'minimum', 'maximum'}


def identifier(name):
    slug = re.sub('[^a-z0-9_]+', '_', name.casefold()).strip('_')
    if not slug or not slug[0].isalpha():
        slug = 'tool_' + slug
    if len(slug) < 3:
        slug += '_op'
    if len(slug) > 64:
        slug = slug[:51] + '_' + hashlib.sha256(name.encode()).hexdigest()[:12]
    return slug


from schema_support import schema_contract, check_data, assess_review
from output_contracts import AUDIT_SCHEMA


def validate_spec(operation):
    operation = copy.deepcopy(operation)
    public(operation)
    original_name = operation.get('name')
    if not isinstance(original_name, str) or not original_name.strip():
        raise ValueError('Missing operation name')
    operation['name'] = identifier(original_name)
    operation.setdefault('display_name', original_name)
    for field in ('description', 'when_to_use', 'limitations'):
        value = operation.get(field)
        if isinstance(value, list) and value and all(isinstance(item, str) and item.strip() for item in value):
            operation.setdefault('original_text_metadata', {})[field] = copy.deepcopy(value)
            operation[field] = '\n'.join(value)
    code = operation.get('code_contract')
    if not isinstance(code, dict) or not CONTRACT_FIELDS.issubset(code):
        raise ValueError('Separate code_contract required: input_schema, output_schema, algorithm, invariants, edge_cases')
    if not isinstance(code['algorithm'], str) or len(code['algorithm']) < 60:
        raise ValueError('Code algorithm must define the actual transformation')
    if any(not isinstance(code[k], list) or not code[k] for k in ('invariants', 'edge_cases')):
        raise ValueError('Explicit invariants and edge cases required')
    for key in ('input_schema', 'output_schema'):
        schema_contract(code[key], 'code_contract.' + key)
    if code['input_schema']['type'] == 'array':
        # Tool calls take an object; preserve an array transformation via an
        # explicit, generic argument wrapper before generating any code/tests.
        original_schema = copy.deepcopy(code['input_schema'])
        operation['code_input_adapter'] = {'kind': 'object_wrapper', 'field': 'records', 'original_schema': original_schema}
        code['input_schema'] = {'type': 'object', 'properties': {'records': original_schema},
                                'required': ['records'], 'additionalProperties': False}
        semantic = operation.get('semantic_preprocessor')
        if isinstance(semantic, dict) and isinstance(semantic.get('instruction'), str):
            semantic['instruction'] += '\nOUTPUT ADAPTER: Preserve the same annotations but wrap the input array as {"payload":{"records":[...]}}. This object format replaces the earlier flat-array output format.'
        code['algorithm'] = "Python receives a JSON object payload. The original input array is payload['records']; apply every following array transformation to that records array, never to the wrapper object. " + code['algorithm']
    if code['input_schema'].get('type') != 'object':
        raise ValueError('Python input must be a JSON object or explicitly wrapped array')
    operation['input_schema'] = code['input_schema']
    operation['output_schema'] = code['output_schema']
    operation['requirements'] = code['algorithm'] + '\nInvariants: ' + json.dumps(code['invariants']) + '\nEdge cases: ' + json.dumps(code['edge_cases'])
    return legacy_validate(operation)


def code_projection(operation):
    op = validate_spec(operation)
    return {k: op[k] for k in ('name', 'when_to_use', 'requirements', 'input_schema', 'output_schema', 'limitations')} | {
        'description': 'Deterministic transformation of supplied structured annotations. Semantic processing has already finished outside this Python function.'}


def audit_cases(operation, cases):
    validate_cases(cases)
    op = validate_spec(operation)
    errors = []
    for i, case in enumerate(cases):
        if 'expected' in case and 'expected_error' in case:
            errors.append('case%d: choose a value assertion OR an error assertion' % i)
        if 'expected' in case:
            errors.extend('case%d input: %s' % (i, e) for e in check_data(op['input_schema'], case['input']))
            errors.extend('case%d expected: %s' % (i, e) for e in check_data(op['output_schema'], case['expected']))
            text = json.dumps(case['expected'], ensure_ascii=False).casefold()
            if any(s in text for s in ('let\'s assume', 'assuming sum', 'assuming max', 'contract implies', 'if max:', 'if aggregation')):
                errors.append('case%d: expected output contains unresolved assumptions' % i)
    def prose_fields(schema, path='output'):
        for key, value in schema.get('properties', {}).items():
            if key in ('reasoning_chain', 'explanation', 'rationale') and value.get('type') == 'string' and 'enum' not in value:
                errors.append(path + '.' + key + ': free-form model prose is not a deterministic code assertion')
            prose_fields(value, path + '.' + key)
        if isinstance(schema.get('items'), dict):
            prose_fields(schema['items'], path + '[]')
    prose_fields(op['output_schema'])
    return errors


CODE_VERIFY = '''Verify ONLY the Python code contract. Its input is ALREADY PREPARED structured annotations, not original biomedical prose; a separate fixed Qwen procedure produced them. Return JSON {approve:boolean,reason:string,cases:[{input:object,expected:JSON_value} or {input:object,expected_error:"ValueError"}]}. Produce exactly 6 to 8 compact distinct synthetic cases from this exact code input schema. Expected outputs must satisfy the exact schema and algorithm, with no hidden rules. Cover empty input, normalization, alias precedence, ordering, duplicate handling, validation and nonmutation as applicable. Never assert a free-form explanation string, infer medical facts, or silently choose between undefined sum/max/precedence rules. Reject ambiguous contracts. Use fictional symbols and IDs only. Do not implement or execute code.'''
CONSISTENCY = '''Audit the independent synthetic test suite against the Python-only contract. Return JSON {approve:boolean,issues:[{case_index:integer,path:string,observed:JSON,computed:JSON,rule:string}],ambiguities:[{rule_quote:string,interpretation_a:string,interpretation_b:string}]}. An issue MUST identify an actual zero-based case index and JSON pointer into that test case (for example /expected/items/0 or /expected_error), copy its observed value exactly, and provide the DIFFERENT value computed from the stated rule. Identical observed and computed values are not contradictions. Never invent records or report mere missing coverage as an incorrect expectation. Reject only a demonstrated mismatch or a genuinely ambiguous quoted rule with two distinct interpretations. Standard Python string ordering is case-sensitive Unicode/ASCII ordering unless the contract says otherwise: uppercase Z precedes lowercase a. Test assertion expected_error=ValueError asserts the exception class, not its message. No code. At most4 issues and3 ambiguities.'''

COMPILER = '''Compile this operation into a precise interface boundary. Return JSON {operation:object}. Retain name, description, when_to_use, limitations, optional semantic_preprocessor:{instruction}, and add code_contract:{input_schema:object,output_schema:object,algorithm:string,invariants:[string],edge_cases:[string]}. The input_schema describes ONLY the structured JSON actually consumed by Python AFTER Qwen preprocessing. It must include every map, score, condition or relevance annotation the code needs; it must not instead describe raw prose when semantic extraction is required. The output_schema describes only deterministic results, no free-form reasoning_chain/explanation/rationale. Define alias precedence, case rendering vs grouping, alias-list inclusion, map chains/cycles, ordering, duplicates, unknowns and invalid types whenever relevant. Unknown medical semantics belong to Qwen and runtime data, never Python constants. Use valid JSON Schema. Prefer explicit types; nullable type arrays and default annotations are valid. Default annotations do not fill missing values. Prefer a compact mechanical operation. All nonlocal references are forbidden. When revising after feedback, actively change the rejected rules; do not reproduce a rejected contract unchanged. Do not copy legacy test expectations. Map cycles have no terminal value: reject them with ValueError rather than selecting an undefined final value. Self-maps may terminate if explicitly stated. Define deterministic output ordering. Keep the operation small; semantic equivalence and relevance are supplied annotations, not substring heuristics. Top-level input_schema/output_schema must mirror code_contract's schemas. No real entity names or task IDs.'''


def install(base):
    if getattr(base, '_contract_guard_installed', False):
        return
    base._contract_guard_installed = True
    original_build = base.build_candidate
    base.validate_spec = validate_spec
    base.MANAGER += '\nMANDATORY: operation must include a separate code_contract with input_schema, output_schema, algorithm, invariants and edge_cases. Python receives prepared annotations, not raw prose. Use a compact mechanical operation, avoid arbitrary confidence/ranking scales and free-form output explanations.'

    def guarded_build(root, run, build_dir, spec, cases, parent=None):
        full = validate_spec(spec)
        issues = audit_cases(full, cases)
        if issues:
            raise ValueError('Invalid independent test suite: ' + '; '.join(issues))
        manifest_path = original_build(root, run, build_dir, code_projection(full), cases, parent)
        if manifest_path:
            manifest = base.load(manifest_path)
            manifest['operation'] = full
            manifest['code_only_specification'] = str(build_dir / 'spec.json')
            base.atomic(build_dir / 'full_operation.json', full)
            base.atomic(manifest_path, manifest)
        return manifest_path
    base.build_candidate = guarded_build

    if hasattr(base, 'call_tool'):
        original_call = base.call_tool
        def typed_call(manifest_path, payload, directory):
            manifest = base.load(manifest_path)
            operation = manifest.get('operation', {})
            if operation.get('code_contract'):
                op = validate_spec(operation)
                issues = check_data(op['input_schema'], payload)
                if issues:
                    raise ValueError('Prepared code input violates schema: ' + '; '.join(issues))
                output = original_call(manifest_path, payload, directory)
                issues = check_data(op['output_schema'], output)
                if issues:
                    raise ValueError('Actual code output violates schema: ' + '; '.join(issues))
                return output
            return original_call(manifest_path, payload, directory)
        base.call_tool = typed_call


class GuardMixin:
    def ask(self, key, system, body, max_tokens=3072):
        verifier = '/independent_verifier_' in key
        if verifier:
            full = validate_spec(body['operation'])
            request = {'operation': code_projection(full)}
            for revision in range(3):
                case_key = key if revision == 0 else key + '_fixture_revision_' + str(revision)
                result = super().ask(case_key, CODE_VERIFY, request, max_tokens)
                if not result.get('approve'):
                    return result
                try:
                    issues = audit_cases(full, result.get('cases'))
                except ValueError as exc:
                    issues = [str(exc)]
                if not issues:
                    critic = super().ask(case_key + '_test_consistency', CONSISTENCY,
                                         {'operation': code_projection(full), 'cases': result['cases']}, 2048)
                    assessment = assess_review(critic, result['cases'], code_projection(full))
                    if hasattr(self, 'run'):
                        from pathlib import Path
                        directory = self.run / 'api' / (case_key + '_test_consistency')
                        directory.mkdir(parents=True, exist_ok=True)
                        (directory / 'counterexample_assessment.json').write_text(json.dumps(assessment, ensure_ascii=False, indent=2), encoding='utf-8')
                    issues.extend(json.dumps(claim, ensure_ascii=False) for claim in assessment['blocking_issues'])
                    issues.extend('Contract ambiguity: ' + json.dumps(claim, ensure_ascii=False) for claim in assessment['ambiguities'])
                if not issues:
                    return result
                request = {'operation': code_projection(full), 'rejected_cases': result.get('cases'),
                           'review_issues': issues,
                           'instruction': 'Keep the code contract unchanged. Correct test expectations that conflict with it. Recompute every result including case rendering and alias precedence. If the contract is truly ambiguous, return approve:false with the exact ambiguity; never guess.'}
            return {'approve': False, 'reason': 'Test suite rejected before Coder: ' + '; '.join(issues), 'cases': result.get('cases')}
        result = super().ask(key, system, body, max_tokens)
        if isinstance(result.get('operation'), dict):
            operation = result['operation']
            if 'code_contract' not in operation:
                operation = super().ask(key + '_compile_code_boundary', COMPILER, {'operation': operation}, 6144)['operation']
            try:
                result['operation'] = validate_spec(operation)
            except ValueError as exc:
                repaired = super().ask(key + '_repair_code_boundary', COMPILER, {'operation': operation, 'boundary_error': str(exc)}, 6144)
                result['operation'] = validate_spec(repaired['operation'])
        return result

"""Native JSON response shapes for the existing fixed Qwen roles."""
import copy


def text(limit=800):
    return {'type': 'string', 'maxLength': limit}


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


def array(items, maximum=100, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


ANSWER_SCHEMA = obj({
    'items': array(text(512)),
    'supports': array(obj({'item': text(512), 'evidence_id': text(128), 'quote': text(800)}), 200),
    'limitations': text(800)}, ['items', 'supports'])

OPERATION_SCHEMA = obj({
    'name': text(100), 'description': text(800), 'when_to_use': text(800),
    'limitations': text(1200), 'requirements': text(3000),
    'input_schema': {'type': 'object'}, 'output_schema': {'type': 'object'},
    'semantic_preprocessor': {'anyOf': [obj({'instruction': text(2200)}), {'type': 'null'}]},
    'code_contract': obj({'input_schema': {'type': 'object'}, 'output_schema': {'type': 'object'},
                          'algorithm': text(3000), 'invariants': array(text(400), 12, 1),
                          'edge_cases': array(text(400), 12, 1)})},
    ['name', 'description', 'when_to_use', 'limitations', 'code_contract'])

CASE_SCHEMA = obj({'input': {'type': 'object'}, 'expected': {},
                   'expected_error': {'type': 'string', 'enum': ['ValueError']}}, ['input'])
CASE_SCHEMA['anyOf'] = [{'required': ['expected']}, {'required': ['expected_error']}]
VERIFY_SCHEMA = obj({'approve': {'type': 'boolean'}, 'reason': text(1200),
                     'cases': array(CASE_SCHEMA, 8)}, ['approve', 'reason', 'cases'])

AUDIT_SCHEMA = obj({
    'approve': {'type': 'boolean'},
    'issues': array(obj({'case_index': {'type': 'integer', 'minimum': 0, 'maximum': 7},
                         'path': text(256), 'observed': {}, 'computed': {}, 'rule': text(600)}), 4),
    'ambiguities': array(obj({'rule_quote': text(600), 'interpretation_a': text(600),
                             'interpretation_b': text(600)}), 3)})

REVIEW_SCHEMA = obj({'supported': {'type': 'boolean'},
                     'change_kind': {'type': 'string', 'enum': ['missing_supported_item',
                                     'unsupported_item_removed', 'condition_corrected',
                                     'expression_only', 'operation_only', 'none']},
                     'reason': text(1200), 'changed_items': array(text(512))})

FACT_SCHEMA = obj({'records': array(obj({
    'name': text(512), 'aliases': array(text(256), 20), 'relation': text(600),
    'eligible': {'type': 'boolean'}, 'group': text(256),
    'qualifiers': array(text(300), 16), 'evidence_id': text(128), 'quote': text(800)}), 60),
    'limitations': text(800)}, ['records'])


def response_schema(key, system, body):
    if key.endswith('/failure_authenticity'):
        return obj({'classification': {'type': 'string', 'enum': [
                        'factual_error', 'coverage_gap', 'condition_error', 'missing_operation',
                        'representation_only', 'no_content_failure', 'missing_evidence', 'uncertain']},
                    'create_tool_justified': {'type': 'boolean'},
                    'problems': array(obj({'answer_item': text(512), 'evidence_id': text(128),
                                           'quote': text(800), 'description': text(800)}), 8),
                    'reason': text(1600)})
    if system.startswith('Audit the independent synthetic test suite'):
        return copy.deepcopy(AUDIT_SCHEMA)
    if system.startswith('Verify ONLY the Python code contract'):
        return copy.deepcopy(VERIFY_SCHEMA)
    if system.startswith('Review this proposed answer change'):
        return copy.deepcopy(REVIEW_SCHEMA)
    if system.startswith('You are the fixed biomedical evidence Executor'):
        return copy.deepcopy(ANSWER_SCHEMA)
    if '/facts_' in key:
        return copy.deepcopy(FACT_SCHEMA)
    if '/semantic_preprocessor' in key and 'input_schema' in body:
        return obj({'payload': copy.deepcopy(body['input_schema'])})
    if '/compact_' in key and isinstance(body.get('records'), list):
        count = len(body['records'])
        indices = array({'type': 'integer', 'minimum': 0, 'maximum': max(0, count - 1)}, count)
        return obj({'selected_indices': indices, 'reason': text(500)})
    if system.startswith('You are the fixed Executor choosing reusable tools'):
        names = sorted(body.get('available_tools', {}))
        choice = {'anyOf': [{'type': 'string', 'enum': names}, {'type': 'null'}]} if names else {'type': 'null'}
        return obj({'tool': choice, 'payload': {'type': ['object', 'null']}, 'reason': text(800)})
    if system.startswith('Compile this operation') or system.startswith('Rewrite the contract generically'):
        return obj({'operation': copy.deepcopy(OPERATION_SCHEMA)})
    if 'capability-gap Manager' in system or 'failure-driven reusable TOOL learning' in system:
        targets = sorted(body.get('active_tools', {}))
        return obj({'action': {'type': 'string', 'enum': ['create', 'repair', 'reuse', 'defer']},
                    'reason': text(1200), 'failure_kind': text(160), 'missing_operation': text(300),
                    'repair_target': {'anyOf': [{'type': 'string', 'enum': targets}, {'type': 'null'}]} if targets else {'type': 'null'},
                    'operation': {'anyOf': [copy.deepcopy(OPERATION_SCHEMA), {'type': 'null'}]},
                    'exploration_payload': {'type': ['object', 'null']}},
                   ['action', 'reason', 'failure_kind', 'missing_operation', 'repair_target', 'operation', 'exploration_payload'])
    return {'type': 'object'}

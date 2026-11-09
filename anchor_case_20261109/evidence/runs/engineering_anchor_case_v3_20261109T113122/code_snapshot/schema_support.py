"""Standard JSON Schema validation, without filling defaults or fetching references."""
import copy
import json
import sys
from functools import lru_cache
from pathlib import Path

deps = Path(__file__).resolve().parent / 'deps'
if deps.is_dir():
    sys.path.insert(0, str(deps))
from jsonschema import Draft202012Validator, SchemaError
from jsonschema.validators import validator_for


def _schema_nodes(schema):
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise ValueError('A JSON schema must be an object or boolean')
    yield schema
    for key in ('properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas'):
        for child in schema.get(key, {}).values():
            yield from _schema_nodes(child)
    for key in ('items', 'additionalProperties', 'contains', 'not', 'if', 'then', 'else',
                'propertyNames', 'unevaluatedProperties', 'unevaluatedItems'):
        child = schema.get(key)
        if isinstance(child, (dict, bool)):
            yield from _schema_nodes(child)
    for key in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
        for child in schema.get(key, []):
            yield from _schema_nodes(child)


@lru_cache(maxsize=256)
def _validator(serialized):
    schema = json.loads(serialized)
    cls = validator_for(schema, default=Draft202012Validator)
    try:
        cls.check_schema(schema)
    except SchemaError as exc:
        raise ValueError('Invalid JSON Schema: ' + exc.message) from exc
    nodes = list(_schema_nodes(schema))
    if len(nodes) > 2048:
        raise ValueError('Schema is too large for the declared tool interface')
    for node in nodes:
        if '$ref' in node and not node['$ref'].startswith('#'):
            raise ValueError('Tool schemas require local references')
    return cls(schema)


def schema_contract(schema, path='schema'):
    try:
        _validator(json.dumps(schema, sort_keys=True, ensure_ascii=False))
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError(path + ': ' + str(exc)) from exc


def check_data(schema, value, path='$'):
    validator = _validator(json.dumps(schema, sort_keys=True, ensure_ascii=False))
    try:
        return [path + '/' + '/'.join(map(str, e.absolute_path)) + ': ' + e.message
                for e in validator.iter_errors(value)]
    except Exception as exc:
        raise ValueError('Schema could not be evaluated: ' + str(exc)) from exc


def normalize_payload(result, schema):
    """Normalize envelopes only when exactly one interpretation validates."""
    if not isinstance(result, dict):
        raise ValueError('Semantic procedure must return a JSON object')
    if isinstance(result.get('payload'), dict) and not check_data(schema, result['payload']):
        return {'payload': copy.deepcopy(result['payload'])}, 'declared_payload_envelope'
    candidates = []
    if isinstance(result.get('payload'), dict):
        candidates.append(('payload', result['payload']))
    candidates.append(('direct_object', result))
    properties = schema.get('properties', {})
    required = schema.get('required', [])
    if len(required) == 1 and required[0] in properties:
        field = required[0]
        raw = result.get('payload')
        if isinstance(raw, list) and properties[field].get('type') == 'array':
            candidates.append(('array_argument_wrapper', {field: raw}))
    valid = {}
    for adapter, value in candidates:
        if not check_data(schema, value):
            valid.setdefault(json.dumps(value, sort_keys=True, ensure_ascii=False), (adapter, value))
    if len(valid) != 1:
        raise ValueError('Semantic payload has %d schema-valid interpretations' % len(valid))
    adapter, value = next(iter(valid.values()))
    return {'payload': copy.deepcopy(value)}, adapter


def pointer(document, path):
    if path == '':
        return document
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('Expected a JSON pointer')
    value = document
    for component in path[1:].split('/'):
        key = component.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def json_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(json_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def assess_review(review, cases, operation):
    """A review veto needs a concrete differing value or a quoted ambiguity."""
    issues, invalid = [], []
    for claim in review.get('issues', []):
        try:
            case = cases[claim['case_index']]
            actual = pointer(case, claim['path'])
            if not json_equal(actual, claim['observed']):
                raise ValueError('The cited expected value is absent from that case')
            if json_equal(claim['observed'], claim['computed']):
                raise ValueError('The expected and computed values are identical')
            if not claim.get('rule', '').strip():
                raise ValueError('No contract rule supplied')
            issues.append(claim)
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            invalid.append({'claim': claim, 'reason': str(exc)})
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for child in value.values():
                yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)
    text = '\n'.join(strings(operation))
    ambiguities = []
    for claim in review.get('ambiguities', []):
        if (claim.get('rule_quote') and claim['rule_quote'] in text and
                claim.get('interpretation_a') != claim.get('interpretation_b')):
            ambiguities.append(claim)
        else:
            invalid.append({'claim': claim, 'reason': 'No quoted rule with two distinct interpretations'})
    return {'blocking_issues': issues, 'ambiguities': ambiguities, 'invalid_claims': invalid,
            'veto': bool(issues or ambiguities)}

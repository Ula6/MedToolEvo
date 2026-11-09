"""Trusted acceptance arithmetic, never supplied as candidate implementation."""
from decimal import Decimal, localcontext
import math

KEYS = ('weighted_mean', 'weighted_population_variance', 'weighted_population_sd', 'weighted_geometric_mean')


def oracle(payload):
    if not isinstance(payload, dict) or set(payload) != {'rows'}:
        raise ValueError('Expected exactly rows')
    rows = payload['rows']
    if not isinstance(rows, list) or not rows:
        raise ValueError('Nonempty rows required')
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'value', 'weight'}:
            raise ValueError('Expected value/weight pair')
        for k in ('value', 'weight'):
            if type(row[k]) not in (float, int) or not math.isfinite(row[k]):
                raise ValueError('Finite JSON number required; bool is not a number')
        if row['value'] <= 0 or row['weight'] < 0:
            raise ValueError('Positive values, nonnegative weights required')
    with localcontext() as ctx:
        ctx.prec = 60
        pairs = [(Decimal(str(r['value'])), Decimal(str(r['weight']))) for r in rows]
        total = sum(w for x, w in pairs)
        if total <= 0:
            raise ValueError('Positive total weight required')
        mean = sum(x * w for x, w in pairs) / total
        variance = sum(w * (x - mean) ** 2 for x, w in pairs) / total
        geometric = (sum(w * x.ln() for x, w in pairs) / total).exp()
        values = (mean, variance, variance.sqrt(), geometric)
        return {k: float(v.quantize(Decimal('0.000001'))) for k, v in zip(KEYS, values)}


def evaluate(answer, expected, tolerance=0.0000005):
    checks = {}
    for key in KEYS:
        value = answer.get(key) if isinstance(answer, dict) else None
        valid = type(value) in (int, float) and math.isfinite(value)
        error = abs(value - expected[key]) if valid else None
        checks[key] = {'predicted': value, 'expected': expected[key], 'absolute_error': error,
                       'pass': bool(valid and error <= tolerance)}
    return {'pass': all(v['pass'] for v in checks.values()),
            'correct': sum(v['pass'] for v in checks.values()), 'total': len(KEYS),
            'accuracy': sum(v['pass'] for v in checks.values()) / len(KEYS), 'checks': checks}

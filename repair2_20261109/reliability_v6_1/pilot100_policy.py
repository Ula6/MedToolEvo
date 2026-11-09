"""Fixed100-item selection and evidence-based pilot admission; no model calls."""
import random


def choose_tasks(parts):
    rng = random.Random(20261108)
    quotas = {'development_seen': 10, 'discovery': 25, 'admission': 20, 'evaluation': 45}
    chosen = []
    for part, size in quotas.items():
        pool = list(parts[part])
        rng.shuffle(pool)
        if part == 'discovery':
            known = [t for t in pool if t['id'] == '624f0813e764a5320400000a']
            pool = known + [t for t in pool if t not in known]
        chosen.extend(pool[:size])
    assert len(chosen) == len({t['id'] for t in chosen}) == 100
    return chosen


def evaluate_pilot(rows, candidates, coverage_failures):
    reasons = []
    ids = [r['task_id'] for r in rows]
    if len(rows) != 100 or len(set(ids)) != 100:
        reasons.append('100_distinct_tasks_not_completed')
    failures = [r['task_id'] for r in rows if r.get('errors')]
    if failures:
        reasons.append('unresolved_task_execution_errors')
    if coverage_failures:
        reasons.append('incomplete_evidence_processing')
    repairs = []
    post_registration_reuse = []
    for c in candidates:
        gate = c.get('gate', {})
        if c.get('status') != 'stable' or not gate.get('enter_trial') or not gate.get('genuine_answer_repair') or not c.get('review', {}).get('supported'):
            continue
        passes = [t for t in c.get('trials', []) if t.get('result') == 'pass']
        if len(passes) < 3 or not c.get('calibration_pass'):
            continue
        repairs.append(c['name'])
        preceding = {c['discovery_task']} | {t['task_id'] for t in c.get('trials', [])}
        for r in rows:
            final, control = r['tool_augmented_final'], r['same_evidence_Qwen']
            if (r['task_id'] not in preceding and c['name'] in r.get('used_tools', [])
                    and final.get('source_binding_complete') and final['score']['f1'] >= control['score']['f1'] - 1e-12
                    and not (r.get('tool_trace') or {}).get('error')):
                post_registration_reuse.append({'tool': c['name'], 'task_id': r['task_id']})
    if not repairs:
        reasons.append('no_verified_answer_repair_and_stable_registration')
    if not post_registration_reuse:
        reasons.append('no_successful_post_registration_reuse')
    return {'pass': not reasons, 'reasons': reasons, 'pilot_completed': len(rows), 'distinct_tasks': len(set(ids)),
            'execution_error_tasks': failures, 'coverage_failures': coverage_failures,
            'verified_repair_tools': repairs, 'post_registration_reuse': post_registration_reuse,
            'interpretation': 'Engineering lifecycle acceptance, not100% medical accuracy or proof of absence of all defects.'}

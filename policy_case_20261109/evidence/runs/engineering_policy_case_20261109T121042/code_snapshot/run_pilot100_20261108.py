"""Run exactly100 pilot questions before considering full continuous evolution."""
import argparse
import fcntl
import html
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path('/home/supervisor/project/sy/MedToolEvo')
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_closed_loop_v5_1_20261108 as base
from pilot100_policy import choose_tasks, evaluate_pilot


class PilotStudy(base.OpenStudy):
    def __init__(self, run, resume=False):
        super().__init__(run, resume)
        self.pilot_tasks = choose_tasks(self.parts)
        config = {'version': 'pilot100-v1', 'pilot_total': 100, 'pilot_ids': [t['id'] for t in self.pilot_tasks],
                  'selection': 'fixed seed20261108, part quotas10/25/20/45; known failed admission included; not blind',
                  'early_full_transition_disabled': True,
                  'full_transition': 'all100 distinct tasks complete AND pilot_acceptance.pass=true; otherwise stop and report',
                  'models': {'semantics': 'Qwen3.5-27B', 'code': 'Qwen3-Coder-30B'},
                  'base_protocol_sha256': base.sha(run / 'protocol.json'),
                  'pilot_code_sha256': base.sha(Path(__file__)),
                  'policy_sha256': base.sha(Path(__file__).resolve().parent / 'pilot100_policy.py'),
                  'format_recovery': 'bounded concise JSON retry; facts/preprocessor up to6144 tokens when context permits; never remove evidence',
                  'acceptance': 'no unhandled task/coverage errors; supported original answer repair, tests/calibration/stable registration;3 later trials and a further actual use after registration'}
        target = run / 'pilot_protocol.json'
        if resume:
            assert base.load(target) == config, 'Pilot protocol changed'
        else:
            base.atomic(target, config)
            self.state.update(stage='pilot100', development_limit=100, pilot_total=100, pilot_passed=False)
            self.save()
        self.progress()

    def ask(self, key, system, body, max_tokens=3072):
        richer = '/facts_' in key or key.endswith('/semantic_preprocessor')
        allowance = max(max_tokens, 6144) if richer else max_tokens
        try:
            return super().ask(key, system, body, allowance)
        except base.ContextLimit:
            if allowance == max_tokens:
                raise
            return super().ask(key + '_context_fit', system, body, max_tokens)
        except ValueError as exc:
            if 'Incomplete generation' not in str(exc) and 'Model operation failed' not in str(exc):
                raise
            self.event('format_recovery', operation=key, reason=str(exc))
            compact = system + '\nReturn compact JSON only. No explanations or repeated prose. Preserve every required field and supported answer; use minimal exact source quotes. Do not invent or silently omit evidence. No Markdown.'
            try:
                return super().ask(key + '_compact_recovery', compact, body, max(6144, max_tokens))
            except base.ContextLimit:
                return super().ask(key + '_compact_context_fit', compact, body, max_tokens)

    def progress(self):
        super().progress()
        if not hasattr(self, 'pilot_tasks'):
            return
        count = len(list((self.run / 'development/tasks').glob('*/result.json')))
        self.status.update(pilot_completed=count, pilot_total=100, development_max=100,
                           pilot_passed=self.state.get('pilot_passed', False), full_requires_100_pilot=True)
        base.atomic(self.run / 'progress.json', self.status)
        path = self.run / 'index.html'
        page = path.read_text(encoding='utf-8')
        replacement = '<pre>' + html.escape(json.dumps(self.status, ensure_ascii=False, indent=2)) + '</pre>'
        page = re.sub(r'<pre>.*?</pre>', lambda _: replacement, page, count=1, flags=re.S)
        page = page.replace('MedToolEvo v5.1', 'MedToolEvo · 100题先行验收').replace('MedToolEvo v5', 'MedToolEvo · 100题先行验收')
        page = re.sub(r'(<h1>.*?</h1>)<p>.*?</p>', lambda m: m.group(1) + '<p>先完整处理100道不同问题，并验证失败诊断、代码生成、原题改善、注册和注册后复用。100题之前禁止进入全量；100题验收通过后才进入1130题连续进化。</p>', page, count=1, flags=re.S)
        page += '<section><h2>100题验收门槛</h2><p>100道不同问题全部处理完，再检查真实失败改善、功能验收、稳定注册和注册后复用。100题之前禁止进入全量；存在未处理故障或缺少闭环证据时停在验收点。</p><a href="pilot_protocol.json">100题协议</a> · <a href="pilot_acceptance.json">验收结果（结束后生成）</a></section>'
        temporary = path.with_name('pilot_index.html.tmp')
        temporary.write_text(page, encoding='utf-8')
        temporary.replace(path)

    def pilot_report(self):
        paths = list((self.run / 'development/tasks').glob('*/result.json'))
        rows = [base.load(p) for p in paths]
        coverage = []
        for r in rows:
            p = Path(r['attempt']) / 'records.json'
            if p.exists():
                c = base.load(p).get('coverage', {})
                if c.get('failed_batches'):
                    coverage.append({'task_id': r['task_id'], 'failed_batches': c['failed_batches']})
        result = evaluate_pilot(rows, self.state['candidates'], coverage)
        result['expected_ids_match'] = {r['task_id'] for r in rows} == {t['id'] for t in self.pilot_tasks}
        if not result['expected_ids_match']:
            result['pass'] = False
            result['reasons'].append('pilot_id_inventory_mismatch')
        official = {}
        jar = ROOT / 'third_party/bioasq-evaluation/flat/BioASQEvaluation/dist/BioASQEvaluation.jar'
        for arm in ('initial_executor', 'same_evidence_Qwen', 'tool_augmented_final'):
            d = self.run / 'pilot_official_evaluation' / arm
            d.mkdir(parents=True, exist_ok=True)
            base.atomic(d / 'golden.json', {'questions': [{'id': r['task_id'], 'type': 'list', 'exact_answer': self.refs[r['task_id']]['exact_answer']} for r in rows]})
            base.atomic(d / 'submission.json', {'questions': [{'id': r['task_id'], 'type': 'list', 'exact_answer': [[n] for n in r[arm]['items']]} for r in rows]})
            cmd = ['java', '-cp', str(jar) + ':' + str(jar.parent / 'lib/*'), 'evaluation.EvaluatorTask1b', '-phaseB', '-e', '5', str(d / 'golden.json'), str(d / 'submission.json'), '-verbose']
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            base.atomic(d / 'output.json', {'command': cmd, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
            if p.returncode:
                result['pass'] = False
                result['reasons'].append('official_scoring_failed_' + arm)
            else:
                official[arm] = base.parse_official_output(p.stdout)
        result['official'] = official
        base.atomic(self.run / 'pilot_acceptance.json', result)
        return result

    def run_pipeline(self):
        if self.state['stage'] == 'pilot100':
            for task in self.pilot_tasks:
                self.process(task, 'development')
            gate = self.pilot_report()
            self.state['pilot_passed'] = bool(gate['pass'])
            self.save()
            self.event('pilot100_completed', passed=gate['pass'], reasons=gate['reasons'])
            if not gate['pass']:
                self.status.update(status='pilot100_needs_fixes', phase='pilot_acceptance_report_ready')
                self.progress()
                return
            self.state.update(stage='full', full_started=True,
                              initial_full_registry={p.stem: base.sha(p) for p in self.registry.glob('*.json')})
            self.event('pilot100_passed_start_full', total=1130)
        if self.state['stage'] == 'full':
            assert self.state.get('pilot_passed') and base.load(self.run / 'pilot_acceptance.json')['pass']
            for task in self.all_tasks:
                self.process(task, 'full')
            self.finish()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    with (ROOT / 'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        study = PilotStudy(args.run_dir, args.resume)
        try:
            base.ensure('qa', study.run / 'services')
            study.run_pipeline()
        except BaseException as exc:
            study.status.update(status='stopped_error', error=type(exc).__name__ + ': ' + str(exc))
            study.save()
            study.progress()
            raise


if __name__ == '__main__':
    main()

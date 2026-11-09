"""Versioned100-question run with typed code boundary and test consistency review."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import sys

ROOT = Path('/home/supervisor/project/sy/MedToolEvo')
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_pilot100_20261108 as pilot
from contract_guard import GuardMixin, install
install(pilot.base)


class GuardedPilot(GuardMixin, pilot.PilotStudy):
    def __init__(self, run, resume=False, seed_api_from=None):
        super().__init__(run, resume)
        imported = []
        record = run / 'guard_protocol.json'
        if resume:
            previous = pilot.base.load(record)
            seed_api_from = previous['seed_api_from']
            imported = previous['imported_public_api']
        elif seed_api_from:
            source = Path(seed_api_from).resolve()
            if not source.is_relative_to(ROOT / 'runs'):
                raise ValueError('Cache source outside runs')
            # Only unchanged initial/read/control operations. No decisions, tests,
            # code, task scores or failed outcomes are carried into this version.
            allowed = ('initial_executor', 'initial_executor_chunked', 'facts_', 'compact_', 'same_evidence_Qwen')
            for p in (source / 'api').rglob('outcome.json'):
                operation = p.parent
                if not operation.name.startswith(allowed) or pilot.base.load(p).get('status') != 'ok':
                    continue
                requests = list(operation.rglob('request.json'))
                if any(str(source) in q.read_text(encoding='utf-8') for q in requests):
                    continue
                target = run / 'api' / operation.relative_to(source / 'api')
                if target.exists():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(operation, target)
                imported.append({'source': str(operation), 'outcome_sha256': pilot.base.sha(p), 'request_count': len(requests)})
        config = {'version': 'guarded-pilot100-v3', 'seed_api_from': str(seed_api_from) if seed_api_from else None,
                  'imported_public_api': imported, 'same100_question_ids': pilot.base.load(run / 'pilot_protocol.json')['pilot_ids'],
                  'guard_sha256': pilot.base.sha(ROOT / 'scripts/contract_guard.py'),
                  'runner_sha256': pilot.base.sha(Path(__file__)), 'parent_pilot_protocol_sha256': pilot.base.sha(run / 'pilot_protocol.json'),
                  'fixes': ['normalize bounded identifiers', 'separate Qwen procedure from Python input schema',
                            'pass only code contract to Builder', 'validate test data against schema', 'independent test consistency review', 'bounded independent fixture repair', 'validate actual code input and output', 'native bounded JSON schema for test review'],
                  'old_failures': 'retained in source run; new version is a re-evaluation, not edited old results'}
        if resume:
            assert config == previous, 'Guard/provenance changed'
        else:
            pilot.base.atomic(record, config)
            snapshot = run / 'code_snapshot'
            for name in ('contract_guard.py', Path(__file__).name, 'run_pilot100_20261108.py', 'pilot100_policy.py'):
                shutil.copy2(ROOT / 'scripts' / name, snapshot / name)
        self.generation_calls = len(list((run / 'api').rglob('request.json')))
        self.progress()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--seed-api-from', type=Path)
    args = parser.parse_args()
    with (ROOT / 'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        study = GuardedPilot(args.run_dir, args.resume, args.seed_api_from)
        try:
            pilot.base.ensure('qa', study.run / 'services')
            study.run_pipeline()
        except BaseException as exc:
            study.status.update(status='stopped_error', error=type(exc).__name__ + ': ' + str(exc))
            study.save()
            study.progress()
            raise


if __name__ == '__main__':
    main()

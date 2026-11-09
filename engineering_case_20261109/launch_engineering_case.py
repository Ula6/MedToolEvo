"""Run the user-authorized development demo serially, then resume original pilot."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path('/home/supervisor/project/sy/MedToolEvo')
CODE = ROOT / 'scripts/engineering_case_20261109'


def write(path, value):
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def main():
    old = json.loads((ROOT / 'runs/repair100_launch.json').read_text())
    assert old.get('phase') == 'pilot100' and 'pilot100_reliable_v61_' in old['run']
    pilot = Path(old['run'])
    before = json.loads((pilot / 'progress.json').read_text())
    assert not before['full_started']
    validation = json.loads((ROOT / 'runs/engineering_case_cpu_validation.json').read_text())
    assert validation['pass']
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
    run = ROOT / 'runs' / ('engineering_weighted_case_' + stamp)
    proc = Path('/proc') / str(old['pid']) / 'cmdline'
    assert proc.exists() and str(pilot).encode() in proc.read_bytes() and b'run_reliable_pilot100.py' in proc.read_bytes()
    write(ROOT / 'runs/engineering_serial_plan.json', {'previous_launch': old, 'pilot_progress': before,
        'scope': 'Human explicitly chose real-source derivative engineering case, development registration and reload/reuse. Not BioASQ result.',
        'case_run': str(run), 'full_authorized': False})
    os.killpg(old['pid'], signal.SIGINT)
    for _ in range(100):
        if not proc.exists(): break
        time.sleep(.1)
    assert not proc.exists(), 'Original worker still present; do not start parallel GPU work'
    command = [sys.executable, '-u', str(CODE / 'engineering_case_pipeline.py'), '--run-dir', str(run),
        '--task-dir', str(ROOT / 'data/engineering_case_20261109'), '--pilot-run', str(pilot),
        '--pilot-completed', str(before['pilot_completed'])]
    log = ROOT / 'logs' / (run.name + '.log')
    code = None
    try:
        with log.open('xb') as stream:
            worker = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream,
                stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        record = {'pid': worker.pid, 'run': str(run), 'log': str(log), 'command': command,
            'phase': 'engineering_case', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'pilot_source_run': str(pilot), 'paused_pilot_completed': before['pilot_completed'],
            'models': {'semantics': 'Qwen3.5-27B', 'code': 'Qwen3-Coder-30B'},
            'scope': 'user-authorized real-source derived engineering development case',
            'full_authorized': False, 'full_requires_100_pilot': True, 'resume_after_case': True,
            'http_pid': old.get('http_pid'), 'http_port': old.get('http_port', 8770)}
        write(ROOT / 'runs/repair100_launch.json', record)
        write(ROOT / 'runs/engineering_case_launch.json', record)
        print(json.dumps(record), flush=True)
        try:
            code = worker.wait(timeout=10800)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid, signal.SIGINT)
            worker.wait(timeout=30)
            code = 'engineering_case_timeout'
    finally:
        with Path(old['log']).open('ab') as stream:
            resumed = subprocess.Popen(old['command'], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream,
                stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        record = {**old, 'pid': resumed.pid, 'resumed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'serial_case_run': str(run), 'serial_case_returncode': code,
            'resume_reason': 'Engineering development case ended; continue unchanged original100-question pilot.'}
        write(ROOT / 'runs/repair100_launch.json', record)
        write(ROOT / 'runs/reliable_pilot100_launch.json', record)
        print('PILOT_RESUMED ' + json.dumps(record), flush=True)


if __name__ == '__main__':
    main()

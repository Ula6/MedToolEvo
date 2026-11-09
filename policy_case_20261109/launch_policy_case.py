"""Checkpoint pilot, execute isolated second capability case, always resume pilot."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path('/home/supervisor/project/sy/MedToolEvo')
CODE=ROOT/'scripts/policy_case_20261109'


def read(path):return json.loads(path.read_text())


def write(path,value):
    tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2));tmp.replace(path)


def main():
    old=read(ROOT/'runs/repair100_launch.json');pilot=Path(old['run']);before=read(pilot/'progress.json')
    assert old.get('phase')=='pilot100' and 'run_reliable_pilot100.py' in ' '.join(old['command'])
    assert before['stage']=='pilot100' and not before['full_started']
    assert read(ROOT/'runs/policy_case_cpu_validation.json')['pass']
    proc=Path('/proc')/str(old['pid'])/'cmdline'
    assert proc.exists() and str(pilot).encode() in proc.read_bytes() and b'run_reliable_pilot100.py' in proc.read_bytes()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
    run=ROOT/'runs'/('engineering_policy_case_'+stamp)
    write(ROOT/'runs/policy_serial_plan.json',{'previous_launch':old,'pilot_progress':before,'case_run':str(run),
        'scope':'Human authorized another completely different typical lifecycle and common failure collection. Policy provenance, not numerical statistics. Development-only.',
        'full_authorized':False})
    os.killpg(old['pid'],signal.SIGINT)
    for _ in range(150):
        if not proc.exists():break
        time.sleep(.1)
    assert not proc.exists(),'Original worker remains; never start parallel GPU work'
    command=[sys.executable,'-u',str(CODE/'policy_pipeline.py'),'--run-dir',str(run),
        '--task-dir',str(ROOT/'data/policy_case_20261109'),'--pilot-run',str(pilot),
        '--pilot-completed',str(before['pilot_completed'])]
    log=ROOT/'logs'/(run.name+'.log');code=None
    try:
        with log.open('xb') as f:worker=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
        record={'pid':worker.pid,'run':str(run),'log':str(log),'command':command,'phase':'policy_case',
            'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pilot_source_run':str(pilot),
            'paused_pilot_completed':before['pilot_completed'],'models':{'semantics':'Qwen3.5-27B','code':'Qwen3-Coder-30B'},
            'scope':'real-prose derived policy-provenance development case','full_authorized':False,'full_requires_100_pilot':True,
            'resume_after_case':True,'http_pid':old.get('http_pid'),'http_port':old.get('http_port',8770)}
        write(ROOT/'runs/repair100_launch.json',record);write(ROOT/'runs/policy_case_launch.json',record)
        print(json.dumps(record),flush=True)
        try:code=worker.wait(timeout=10800)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid,signal.SIGINT);worker.wait(timeout=30);code='policy_case_timeout'
    finally:
        with Path(old['log']).open('ab') as f:resumed=subprocess.Popen(old['command'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
        record={**old,'pid':resumed.pid,'resumed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'serial_case_run':str(run),'serial_case_returncode':code,
            'resume_reason':'Third existing-ledger evolution case ended; continue unchanged original100-question pilot.'}
        write(ROOT/'runs/repair100_launch.json',record);write(ROOT/'runs/reliable_pilot100_launch.json',record)
        print('PILOT_RESUMED '+json.dumps(record),flush=True)


if __name__=='__main__':main()

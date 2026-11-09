"""Read-only remote progress snapshot with bounded output."""
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
REMOTE=r'''
import datetime,json
from pathlib import Path
root=Path('/home/supervisor/project/sy/MedToolEvo'); l=json.loads((root/'runs/policy_case_launch.json').read_text());run=Path(l['run'])
read=lambda p:json.loads(p.read_text())
proc=Path('/proc')/str(l['pid'])/'cmdline';cmd=proc.read_bytes().replace(b'\0',b' ').decode() if proc.exists() else ''
baselines=read(run/'baseline_attempts.json') if (run/'baseline_attempts.json').exists() else []
builds=[]
for p in (run/'builds').rglob('builder_summary.json'):
 b=read(p);builds.append({'path':str(p),'summary':b})
recent=sorted((run/'api').rglob('request.json'),key=lambda p:p.stat().st_mtime,reverse=True)
request={}
if recent:
 p=recent[0];v=read(p);request={'path':str(p.relative_to(run)),'max_tokens':v.get('max_tokens'),'started_utc':datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat(),'finished':(p.parent/'response.json').exists()}
print(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':str(run),'pid':l['pid'],
 'identity_matches':str(run) in cmd and 'policy_pipeline.py' in cmd,'progress':read(run/'progress.json'),
 'events':read(run/'state.json')['events'][-6:],'baselines':[{'source':b['source'],'evaluation':b['evaluation'],'retry_evaluation':b.get('retry_evaluation')} for b in baselines],
 'builds':builds,'request':request,'acceptance':read(run/'case_acceptance.json') if (run/'case_acceptance.json').exists() else None,
 'log_tail':Path(l['log']).read_text(errors='replace').splitlines()[-4:]},ensure_ascii=True))
'''

if __name__=='__main__':
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15','sy-supervisor',
        '/home/supervisor/project/sy/MedToolEvo/envs/medtoolevo/bin/python -'],input=REMOTE.encode(),capture_output=True,timeout=50)
    if p.returncode:
        print(p.stderr.decode(errors='replace'));raise SystemExit(p.returncode)
    data=json.loads(p.stdout)
    (HERE/'observation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=True))

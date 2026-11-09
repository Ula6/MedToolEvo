"""Replay original immutable candidate tests on Linux/bubblewrap, without models."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
REMOTE=Path('/home/supervisor/project/sy/MedToolEvo')
CASES={'numeric':('engineering_case_20261109','engineering_weighted_case_20261109T095954'),
       'anchors':('anchor_case_20261109','engineering_anchor_case_v3_20261109T113122'),
       'policy':('policy_case_20261109','engineering_policy_case_20261109T121042')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=['all',*CASES],default='all')
    parser.add_argument('--original-root',type=Path,help='Optional original server project root; otherwise replay bundled evidence.')
    args=parser.parse_args()
    if sys.platform!='linux' or not shutil.which('bwrap'):
        raise SystemExit('Requires Linux and bubblewrap; no host-execution fallback is used.')
    reports={}
    for key in CASES if args.case=='all' else [args.case]:
        folder,rid=CASES[key]
        run=args.original_root/'runs'/rid if args.original_root else ROOT/folder/'evidence/runs'/rid
        a=read(run/'case_acceptance.json');build=read(run/'builds/candidate/builder_summary.json')
        def locate(remote):return Path(remote) if args.original_root else ROOT/folder/'evidence'/Path(remote).relative_to(REMOTE)
        manifest=read(locate(a['manifest']));code=locate(manifest['code_path']);tests=run/'builds/candidate/independent_tests.py'
        assert sha(code)==manifest['sha256'] and sha(tests)==build['test_sha256']
        cmd=['/usr/bin/timeout','--kill-after=2s','30s',shutil.which('bwrap'),'--unshare-all','--unshare-user',
             '--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--setenv','PATH','/usr/bin:/bin',
             '--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64',
             '--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache','--proc','/proc','--dev','/dev',
             '--tmpfs','/tmp','--dir','/work','--ro-bind',str(code.resolve()),'/work/candidate.py',
             '--ro-bind',str(tests.resolve()),'/work/tests.py','--chdir','/work','/usr/bin/python3','-I','-B','/work/tests.py']
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
        if p.returncode:raise RuntimeError(key+': '+p.stderr[-1200:]+' '+p.stdout[-1200:])
        result=json.loads(p.stdout.strip().splitlines()[-1]);assert result['failed']==0
        reports[key]={'passed':result['passed'],'failed':result['failed'],'code_sha256':sha(code),'test_sha256':sha(tests)}
    print(json.dumps({'model_calls':0,'sandbox':'bubblewrap','replay':reports},indent=2))


if __name__=='__main__':main()

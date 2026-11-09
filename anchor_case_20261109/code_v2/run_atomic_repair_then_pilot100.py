"""One serial GPU job: verify real failed contracts, then recheck the fixed100 IDs."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

R=Path('/home/supervisor/project/sy/MedToolEvo');sys.path.insert(0,str(R/'scripts'))
from probe_atomic_contract_repairs import main as repair
from run_guarded_pilot100_20261108 import GuardedPilot,pilot


def main():
    p=argparse.ArgumentParser();p.add_argument('--probe-dir',type=Path,required=True);p.add_argument('--pilot-dir',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--seed-api-from',type=Path,required=True);args=p.parse_args()
    with (R/'runs/autonomous_pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            summary=repair(args.probe_dir)
        except BaseException as exc:
            status=pilot.base.load(args.probe_dir/'progress.json')
            status.update(status='stopped_error',phase='focused_repair_failed',error=type(exc).__name__+': '+str(exc))
            pilot.base.atomic(args.probe_dir/'progress.json',status)
            raise
        if not summary['all_functional_pass']:
            status=pilot.base.load(args.probe_dir/'progress.json');status.update(status='contract_repairs_need_fixes',phase='focused_report_ready');pilot.base.atomic(args.probe_dir/'progress.json',status)
            return
        study=GuardedPilot(args.pilot_dir,seed_api_from=args.seed_api_from)
        old_ids=pilot.base.load(args.seed_api_from/'pilot_protocol.json')['pilot_ids']
        assert [t['id'] for t in study.pilot_tasks]==old_ids,'The agreed100 IDs changed'
        info=pilot.base.load(args.record);info.update(run=str(args.pilot_dir),phase='pilot100',contract_repair_summary=str(args.probe_dir/'focused_summary.json'))
        pilot.base.atomic(args.record,info)
        try:
            study.event('real_contract_repairs_passed_resume100',source=str(args.probe_dir))
            study.run_pipeline()
        except BaseException as exc:
            study.status.update(status='stopped_error',error=type(exc).__name__+': '+str(exc));study.save();study.progress();raise


if __name__=='__main__':main()

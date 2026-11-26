"""Windowless stdlib bootstrap; restart a crashed supervisor with backoff."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def run(plan_path, *, sleep=time.sleep):
    plan_path=Path(plan_path);plan=json.loads(plan_path.read_text(encoding="utf-8"))
    state=Path(plan["state_dir"]);started=time.time_ns();attempt=0
    while not (state/"DISABLE_AUTOSTART").exists():
        attempt+=1
        with (state/f"bootstrap_{started}_{attempt}.log").open("xb") as log:
            process=subprocess.Popen([plan["python"],str(Path(__file__).with_name("supervise.py")),"--plan",str(plan_path)],
                cwd=plan["root"],stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            result=process.wait()
        if result==0:return 0
        sleep(15)
    return 0


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--plan",type=Path,required=True);args=parser.parse_args()
    raise SystemExit(run(args.plan))

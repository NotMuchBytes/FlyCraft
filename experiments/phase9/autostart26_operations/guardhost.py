"""Label shutdown STOPs so a new boot can resume without clearing manual STOP."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tools.power_guard import WindowsGuard,request_stop,run


def factory(paths):
    return lambda unused_callback: WindowsGuard(lambda:request_stop(paths,reason="system_shutdown"))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--state-dir",type=Path,required=True);parser.add_argument("--stop-file",type=Path,action="append",required=True)
    args=parser.parse_args();paths=[p.resolve() for p in args.stop_file]
    run(args.state_dir.resolve(),paths,guard=factory(paths))

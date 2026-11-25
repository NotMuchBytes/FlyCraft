#!/usr/bin/env python3
"""Bounded development orchestration. Official 10,000-world launch is disabled."""

import argparse
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import Campaign, CampaignLock, atomic_json, replace_file, RESOURCE_GOALS


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def brain_sample(results):
    """Read actual logged readout output; no synthetic activity or animation."""
    try:
        with (Path(results) / "bridge.jsonl").open("rb") as handle:
            handle.seek(0, 2)
            handle.seek(max(0, handle.tell()-65536))
            lines = handle.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            try:
                row = json.loads(line)
                response = row["response"]
                if response.get("neural_features") is not None:
                    return {"timestamp_unix": row["timestamp_unix"], "requested_action": response["action"],
                            "command_id": response["command_id"], "features": response["neural_features"],
                            "probabilities": response["action_probabilities"], "mode": response["feature_mode"],
                            "policy_inputs": response.get("policy_neural_inputs"),"intervention": response.get("feature_intervention"),
                            "peak_active_neurons": response["peak_global_active"],
                            "neural_steps": response["neural_steps"], "reward": response["cumulative_reward"]}
            except (ValueError, KeyError, TypeError):
                continue
    except OSError:
        pass
    return None


def dashboard(campaign, status="idle", results=None):
    summary = campaign.summary()
    live = read_json(Path(results) / "status.json") if results else None
    brain = brain_sample(results) if results else None
    data = {"status": status, "summary": summary, "live_worker": live, "brain": brain}
    atomic_json(campaign.folder / "dashboard.json", data)
    escape = html.escape
    cards = "".join(f"<div><small>{escape(str(key).replace('_',' '))}</small><strong>{escape(str(value))}</strong></div>"
                    for key,value in summary.items() if key in {"training_episodes","training_updates","evaluation_episodes",
                    "generated_world_instances","distinct_generated_seeds","recent_training_success_rate",
                    "mean_training_reward","measured_training_worlds_per_hour","estimated_remaining_seconds"})
    rows = "".join(f"<tr><td>{a['episode_number']}</td><td>{escape(a['split'])}</td><td>{escape(a['condition'])}</td>"
                   f"<td>{escape(str(a.get('success',a['status'])))}</td><td>{a.get('actions','—')}</td>"
                   f"<td>{a.get('total_reward','—')}</td><td>{escape(a['run_id'])}</td></tr>"
                   for a in campaign.state["attempts"][-20:])
    bars = ""
    if brain:
        bars = f"<p>Requested action: {escape(brain['requested_action'])}; command {brain['command_id']}. Execution needs a game acknowledgment.</p>"
        for key,value in brain["probabilities"].items():
            bars += f"<label>{escape(key)} {value:.4f}<span style='width:{min(100,max(0,value*100)):.3f}%'></span></label>"
        bars += f"<pre>{escape(json.dumps(brain['features'],indent=2))}</pre><p>Fixed neural window: {brain['neural_steps']} steps; peak active neurons: {brain['peak_active_neurons']}. Feature mode: {escape(brain['mode'])}.</p>"
    page = f"""<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="5">
<title>FlyCraft {escape(summary['stage'])} dashboard</title><style>
body{{font:16px system-ui;background:#101722;color:#e5efff;margin:32px;max-width:1200px}}h1{{color:#71aaff}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.cards div,section{{padding:16px;background:#1a2536;border-radius:10px;margin-bottom:12px}}
small,strong{{display:block}}small{{color:#a9bfdc}}strong{{font-size:22px;overflow-wrap:anywhere}}table{{width:100%;font-size:13px}}td,th{{padding:7px;text-align:left;border-bottom:1px solid #334}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}label{{display:block;margin:7px}}label span{{display:block;height:5px;background:#55a7ff}}</style>
<h1>FlyCraft · {escape(summary['stage'])}</h1><p>Status: {escape(status)}. Official training worlds: {summary['official_training_worlds']}. Goal: {escape(summary['goal'])}, curriculum level 1.</p>
<div class="cards">{cards}</div><p>Throughput is observed worker wall time including startup and filming. Remaining seconds are an estimate. Training outcomes are not held-out evaluation results.</p>
<section><h2>Observed worker resources</h2><pre>{escape(json.dumps(live,indent=2))}</pre><p>CPU temperature unavailable. Samples may be absent during startup. Resource timestamps are Unix seconds.</p></section>
<section><h2>Actual policy readout</h2>{bars or '<p>No neural decision sample yet.</p>'}<p>Activity comes from the fixed connectome. Only the linear softmax readout is learned. Bias is not neural activity. Bars show action probabilities, not neuron firing animations.</p></section>
<section><h2>Recent episodes</h2><table><tr><th>Episode</th><th>Split</th><th>Policy</th><th>Outcome</th><th>Actions</th><th>Reward</th><th>Run</th></tr>{rows}</table></section>
<section><h2>Safe stop and checkpoint</h2><p>Create the file <code>{escape(str(campaign.folder/'STOP'))}</code> or run the CLI stop command. The worker interrupts safely and preserves evidence. Use clear-stop before a later resume.</p><pre>{escape(json.dumps(summary['checkpoint'],indent=2))}</pre><pre>{escape(json.dumps(summary['recent_errors'],indent=2))}</pre></section>"""
    # Replace only our own derived dashboard, never gameplay evidence.
    temporary = campaign.folder / "dashboard.html.tmp"
    temporary.write_text(page,encoding="utf-8",newline="\n")
    replace_file(temporary,campaign.folder/"dashboard.html")
    return data


def worker_command(campaign, attempt, args, seconds):
    profile = campaign.runtime_profile(attempt["goal"])
    command = [sys.executable, str(ROOT/"tools/run_phase8_live.py"), "--run-id", attempt["run_id"],
        "--headless",
        "--checkpoint",attempt["checkpoint"]["path"],"--frozen-checkpoint",campaign.config.get("frozen_checkpoint",campaign.config["initial_checkpoint"])["path"],
        "--goals",attempt["goal"],"--conditions",attempt["condition"],"--trials","1",
        "--world-seed",str(attempt["world_seed"]),"--layout-start",str(attempt["layout_seed"]),
        "--policy-seed",str(attempt["policy_seed"]),"--seconds",str(seconds),"--trial-ticks","400",
        "--camera-mode","bounded","--graphics-backend","opengl",
        "--forward-ticks",str(profile.get("forward_ticks",5)),
        "--server-heap-mib",str(profile["server_heap_mib"]),"--client-heap-mib",str(profile["client_heap_mib"]),
        "--capture-width",str(profile["width"]),"--capture-height",str(profile["height"]),
        "--work-dir",str(args.work_dir),"--build-dir",str(args.build_dir),"--obs-control-dir",str(args.obs_control_dir),
        "--stop-file",str(campaign.folder/"STOP"),"--parent-pid",str(os.getpid()),
        "--parent-created",str(psutil.Process().create_time())]
    if attempt.get("video_required", True):
        command += ["--spectator", "--milestone", str(attempt["episode_number"])]
    if profile.get("pitch_actions"):
        command += ["--pitch-actions", "--turn-degrees", str(profile["turn_degrees"]),
                    "--spectator-view", "first_person"]
        command[command.index("--trial-ticks") + 1] = str(profile["trial_ticks"])
    if profile.get("three_tree_fixture"):
        command.append("--three-tree-fixture")
    if profile.get("terrain_actions"):
        command += ["--terrain-actions", "--policy-label", "foundation338_terrain_transfer",
                    "--frozen-label", "foundation338_terrain_frozen_reference"]
    if profile.get("terrain_step_fixture"):
        command.append("--terrain-step-fixture")
    if profile.get("natural_world"):
        command.append("--natural-world")
    if profile.get("remember_mined_columns"):
        command.append("--remember-mined-columns")
    if args.video_export_dir:
        command += ["--video-export-dir",str(args.video_export_dir)]
    if attempt["train"]:
        command.append("--train")
    if profile.get("launch_cache"):
        command += ["--launch-cache", profile["launch_cache"]["path"],
                    "--launch-cache-sha256", profile["launch_cache"]["sha256"]]
    if campaign.official:
        command += ["--campaign-manifest", str(campaign.folder / "config.json"),
                    "--official-world-number", str(attempt["official_world_number"])]
    return command


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    init=sub.add_parser("init")
    init.add_argument("--name",required=True)
    init.add_argument("--goal",choices=tuple(RESOURCE_GOALS),default="one_log")
    init.add_argument("--checkpoint",type=Path,required=True)
    init.add_argument("--frozen-checkpoint",type=Path,help="Explicit preserved reference for the frozen condition")
    init.add_argument("--worlds",type=int,default=3)
    init.add_argument("--master-seed",type=int,default=20261029)
    init.add_argument("--compact",action="store_true",help="Development profile: 384/512 MiB server/client heaps, 854x480 capture")
    init.add_argument("--checked",action="store_true",help="Independent evidence gate and validated pitch/four-goal interface; development only")
    init.add_argument("--launch-cache",type=Path)
    init.add_argument("--continuous-readiness",action="store_true")
    init.add_argument("--forward-ticks",type=int,default=5,choices=range(1,11),help="Fixed input duration; freeze before paired evaluation")
    init.add_argument("--recording-policy",choices=("milestones","all"),default="milestones")
    init.add_argument("--recording-milestones",help="Optional comma-separated episode numbers; default Phase 9 schedule")
    for name in ("run","status","stop","clear-stop","freeze-final"):
        command=sub.add_parser(name)
        command.add_argument("--campaign",type=Path,required=True)
        if name=="run":
            command.add_argument("--split",choices=("pilot","eval_a","eval_b"),default="pilot")
            command.add_argument("--condition",choices=("trained","frozen","uniform","no_neural","shuffled"),default="trained")
            command.add_argument("--max-episodes",type=int,default=1)
            command.add_argument("--seconds",type=int,default=300)
            command.add_argument("--worker-seconds",type=int,default=240)
            command.add_argument("--work-dir",type=Path,required=True)
            command.add_argument("--build-dir",type=Path,required=True)
            command.add_argument("--obs-control-dir",type=Path,required=True)
            command.add_argument("--video-export-dir",type=Path)
    args=parser.parse_args()
    if args.command=="init":
        milestones=None
        if args.recording_milestones is not None:
            try:
                milestones=tuple(int(n) for n in args.recording_milestones.split(","))
            except ValueError:
                parser.error("recording-milestones must be comma-separated integers")
        campaign=Campaign.create(ROOT/"experiments/phase9"/args.name, project_root=ROOT,name=args.name,
            checkpoint=args.checkpoint,master=args.master_seed,worlds=args.worlds,compact=args.compact,frozen_checkpoint=args.frozen_checkpoint,
            forward_ticks=args.forward_ticks,recording_policy=args.recording_policy,recording_milestones=milestones,goal=args.goal,checked=args.checked,
            launch_cache=args.launch_cache,continuous_readiness=args.continuous_readiness)
        campaign.save(); dashboard(campaign)
        print(campaign.folder)
        return
    campaign=Campaign(args.campaign,project_root=ROOT)
    if args.command=="stop":
        (campaign.folder/"STOP").touch(exist_ok=True)
        print("Stop requested; evidence and the last committed checkpoint are preserved.")
        return
    if args.command=="status":
        print(json.dumps(campaign.summary(),indent=2))
        return
    with CampaignLock(campaign.folder):
        if args.command=="clear-stop":
            stop=campaign.folder/"STOP"
            if stop.exists():
                stop.rename(campaign.folder/f"STOP.ack.{time.time_ns()}")
            dashboard(campaign,"ready to resume")
            return
        if args.command=="freeze-final":
            campaign.freeze_final(); dashboard(campaign,"final policy frozen")
            return
        if not 1<=args.max_episodes<=5 or not 120<=args.seconds<=900 or not 120<=args.worker_seconds<=300:
            parser.error("use 1-5 episodes, 120-900 total seconds and 120-300 seconds per worker")
        # A previous coordinator may have died after the worker saved all evidence.
        campaign.recover()
        deadline=time.monotonic()+args.seconds
        for _ in range(args.max_episodes):
            if (campaign.folder/"STOP").exists():
                dashboard(campaign,"stopped by request"); break
            remaining=int(deadline-time.monotonic())-10
            if remaining<120:
                dashboard(campaign,"bounded wall budget reached"); break
            attempt=campaign.begin(args.split,args.condition,runtime_root=args.work_dir)
            results=ROOT/"experiments/phase9"/attempt["run_id"]
            try:
                with (campaign.folder/(attempt["run_id"]+".log")).open("x",encoding="utf-8") as log:
                    worker=subprocess.Popen(worker_command(campaign,attempt,args,min(remaining,args.worker_seconds)),
                        cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    owner=psutil.Process(worker.pid)
                    campaign.state["attempts"][campaign.state["active_attempt"]].update(worker_pid=worker.pid,worker_created=owner.create_time())
                    campaign.save()
                    while worker.poll() is None:
                        if time.monotonic()>=deadline:
                            (campaign.folder/"STOP").touch(exist_ok=True)
                        dashboard(campaign,"running",results)
                        time.sleep(2)
                outcome=campaign.recover()
                dashboard(campaign,outcome["status"],results)
                print(json.dumps(outcome),flush=True)
                if outcome["status"]!="committed":
                    break  # preserve failure and stop, never churn retries unattended
            except KeyboardInterrupt:
                (campaign.folder/"STOP").touch(exist_ok=True)
                worker.wait(timeout=30)
                campaign.recover(); dashboard(campaign,"interrupted safely",results)
                raise


if __name__=="__main__":
    main()

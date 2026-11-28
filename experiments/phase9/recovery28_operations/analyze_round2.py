"""Preserve a read-only diagnosis of completed round-2 native evidence."""
import collections
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
OPS = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    state_path = ROOT / 'experiments/phase9/fc9_stage25/state.json'
    state = json.loads(state_path.read_text())
    episodes = []
    for row in state['attempts']:
        if row.get('curriculum_round', 0) != 2 or row['split'] != 'eval_a' or row['status'] != 'committed':
            continue
        folder = Path(row['results'])
        native = folder / 'headless.jsonl'
        bridge = folder / 'bridge.jsonl'
        ends = [r['data'] for line in native.read_text().splitlines()
                if (r := json.loads(line))['event'] == 'action_end']
        telemetry = []
        for line in bridge.read_text().splitlines():
            request = json.loads(line)['request']
            if isinstance(request, str):
                request = json.loads(request)
            if request.get('control', {}).get('active'):
                telemetry.append(request['telemetry'])
        actions = collections.Counter(r['ack']['action'] for r in ends)
        breaks = sum(bool(r['ack'].get('block_changed')) for r in ends)
        visible = sum(bool(t.get('visible')) for t in telemetry)
        final_inventory = telemetry[-1].get('inventory') if telemetry else None
        failure = ('success' if row['success'] else 'broke_without_goal'
                   if breaks else 'saw_but_no_break' if visible else 'no_visible_log')
        episodes.append(dict(run_id=row['run_id'], task=row['evaluation_task'],
            condition=row['condition'], seed=row['world_seed'], success=row['success'],
            failure=failure, actions=dict(actions), breaks=breaks,
            visible_samples=visible, samples=len(telemetry), final_active_inventory=final_inventory,
            elapsed_seconds=row['wall_seconds'], ticks=row['ticks'],
            checker_status=row['checker_status'], evidence_sha256={
                'headless.jsonl': digest(native), 'bridge.jsonl': digest(bridge)}))
    summaries = []
    for task, condition in sorted({(r['task'], r['condition']) for r in episodes}):
        rows = [r for r in episodes if (r['task'], r['condition']) == (task, condition)]
        failures = [r for r in rows if not r['success']]
        successes = sum(r['success'] for r in rows)
        n = len(rows)
        z = 1.959963984540054
        phat = successes / n
        center = (phat + z*z/(2*n))/(1+z*z/n)
        half = z*((phat*(1-phat)/n+z*z/(4*n*n))**.5)/(1+z*z/n)
        summaries.append(dict(task=task, condition=condition, trials=n, successes=successes,
            wilson95=[center-half, center+half],
            median_actions=statistics.median(sum(r['actions'].values()) for r in rows),
            median_elapsed_seconds=statistics.median(r['elapsed_seconds'] for r in rows),
            failures=dict(collections.Counter(r['failure'] for r in failures)),
            median_failure_turn_fraction=statistics.median(
                (r['actions'].get('TURN_LEFT',0)+r['actions'].get('TURN_RIGHT',0)) /
                max(1,sum(r['actions'].values())) for r in failures) if failures else None))
    assert len(episodes) == 270 and all(r['checker_status'] == 'verified' for r in episodes)
    destination = OPS / 'round2_diagnosis.json'
    if destination.exists():
        raise FileExistsError('Preserve the existing diagnosis; do not overwrite it')
    destination.write_text(json.dumps(dict(scope='Completed round 2 is now development evidence; not future held-out data.',
        state_sha256=digest(state_path), gate=state['gates']['terrain'], summaries=summaries,
        episodes=episodes),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summaries,indent=2))


if __name__ == '__main__':
    main()

"""Preserve independently checked first-episode proof for recovery round 2."""
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.experiment import atomic_json,digest,source_manifest
from learning import LinearSoftmaxPolicy


def main():
    folder=ROOT/'experiments/phase9/fc9_stage25';ops=Path(__file__).resolve().parent
    state=json.loads((folder/'state.json').read_text())
    a=next(a for a in state['attempts'] if a['run_id']=='fc9_stage25_terrain_00637')
    assert a['status']=='committed' and a['official_world_number']==435 and a['curriculum_round']==2
    assert a['success'] and a['checker_status']=='verified' and a['training_applied']
    assert digest(a['checkpoint_after']['path'])==a['checkpoint_after']['sha256']
    assert digest(a['checkpoint']['path'])==a['checkpoint']['sha256']
    before,_=LinearSoftmaxPolicy.load(a['checkpoint']['path']);after,_=LinearSoftmaxPolicy.load(a['checkpoint_after']['path'])
    delta=float(np.linalg.norm(after.weights-before.weights))
    assert delta>0 and np.isclose(delta,a['update']['weight_delta_norm'])
    results=Path(a['results']);native=[json.loads(l) for l in (results/'headless.jsonl').read_text().splitlines()]
    breaks=[r for r in native if r['event']=='action_end' and r['data']['ack'].get('block_changed')]
    assert breaks
    terminal=json.loads((results/'server.jsonl').read_text().splitlines()[0])
    assert terminal['inventory']['log']>=1 and terminal['success']
    config=json.loads((folder/'config.json').read_text())
    graph=config['checker']['graph'];assert digest(graph['path'])==graph['sha256']
    assert source_manifest(ROOT)['implementation_sha256']==config['implementation_sha256']
    output=ops/'first_episode';output.mkdir(exist_ok=True)
    for name in ('server.jsonl','server.jsonl.initial.jsonl','headless.jsonl','controller.jsonl','run.json','status.json'):
        shutil.copy2(results/name,output/name)
    shutil.copy2(Path(a['checker_report']),output/'checker.json')
    atomic_json(ops/'first_episode_audit.json',dict(run_id=a['run_id'],official_world_number=435,
        independent_checker_verified=True,success=True,native_block_breaks=len(breaks),terminal_inventory=terminal['inventory'],
        actions=a['actions'],wall_seconds=a['wall_seconds'],checkpoint_before=a['checkpoint'],checkpoint_after=a['checkpoint_after'],
        measured_weight_delta_norm=delta,reported_update=a['update'],graph=graph,graph_unchanged=True,
        implementation_sha256=config['implementation_sha256'],episode=a,
        evidence_files={p.name:digest(p) for p in output.iterdir() if p.is_file()}))
    print(json.dumps(dict(success=True,world=435,actions=a['actions'],weight_delta_norm=delta,graph_unchanged=True)))


if __name__=='__main__':main()

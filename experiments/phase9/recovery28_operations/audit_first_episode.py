"""Freeze the first round-3 outcome, including failure if that is the result."""
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.evidence import audit_run
from autonomy.experiment import atomic_json,digest,source_manifest
from learning import LinearSoftmaxPolicy


def main():
    folder=ROOT/'experiments/phase9/fc9_stage25'
    ops=Path(__file__).resolve().parent
    state=json.loads((folder/'state.json').read_text())
    row=next(a for a in state['attempts'] if a.get('curriculum_round')==3)
    assert row['status']=='committed' and row['official_world_number']==531
    assert row['checker_status']=='verified'
    assert digest(row['checkpoint']['path'])==row['checkpoint']['sha256']
    assert digest(row['checkpoint_after']['path'])==row['checkpoint_after']['sha256']
    before,_=LinearSoftmaxPolicy.load(row['checkpoint']['path'])
    after,_=LinearSoftmaxPolicy.load(row['checkpoint_after']['path'])
    delta=float(np.linalg.norm(after.weights-before.weights))
    assert np.isclose(delta,row['update']['weight_delta_norm'])
    assert delta>0 if row['training_applied'] else delta==0
    report=audit_run(row['results'],expected=dict(world_seed=row['world_seed'],train=True))
    episode=report['episodes'][0]
    assert episode['success']==row['success']
    config=json.loads((folder/'config.json').read_text())
    assert source_manifest(ROOT)['implementation_sha256']==config['implementation_sha256']
    graph=config['checker']['graph']
    assert digest(graph['path'])==graph['sha256']
    destination=ops/'first_episode'
    destination.mkdir(exist_ok=False)
    for name in ('server.jsonl','server.jsonl.initial.jsonl','headless.jsonl','controller.jsonl','run.json','status.json'):
        shutil.copy2(Path(row['results'])/name,destination/name)
    shutil.copy2(row['checker_report'],destination/'checker.json')
    atomic_json(ops/'first_episode_audit.json',dict(episode=row,independently_reverified=True,
        native_inventory=episode['inventory'],confirmed_breaks=episode['confirmed_breaks'],
        measured_weight_delta_norm=delta,graph_unchanged=True,
        evidence_files={p.name:digest(p) for p in destination.iterdir()}))
    print(json.dumps(dict(world=531,success=row['success'],actions=row['actions'],
        inventory=episode['inventory'],confirmed_breaks=episode['confirmed_breaks'],
        measured_weight_delta_norm=delta)))


if __name__=='__main__':main()

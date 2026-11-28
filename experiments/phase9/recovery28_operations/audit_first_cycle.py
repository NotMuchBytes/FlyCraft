"""Preserve the first eight fixed training slots, including every failure."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.evidence import audit_run
from autonomy.experiment import atomic_json,digest
from learning import LinearSoftmaxPolicy


def main():
    folder=ROOT/'experiments/phase9/fc9_stage25'
    ops=Path(__file__).resolve().parent
    state=json.loads((folder/'state.json').read_text())
    rows=[a for a in state['attempts'] if a.get('curriculum_round')==3][:8]
    assert len(rows)==8 and all(a['status']=='committed' for a in rows)
    assert [a['official_world_number'] for a in rows]==list(range(531,539))
    expected=[('one_log',False),('one_log',True),('planks',True),('one_log',False),
              ('one_log',True),('planks',True),('three_logs',True),('wooden_pickaxe',True)]
    assert [(a['goal'],a['retention']) for a in rows]==expected
    output=[]
    for a in rows:
        original=json.loads(Path(a['checker_report']).read_text())
        for name,sha in original['evidence_sha256'].items():
            assert digest(Path(a['results'])/name)==sha
        report=audit_run(a['results'],expected=dict(world_seed=a['world_seed'],train=True))
        episode=report['episodes'][0]
        assert episode['success']==a['success']
        for record in (a['checkpoint'],a['checkpoint_after']):
            assert digest(record['path'])==record['sha256']
        before,_=LinearSoftmaxPolicy.load(a['checkpoint']['path'])
        after,_=LinearSoftmaxPolicy.load(a['checkpoint_after']['path'])
        delta=float(np.linalg.norm(after.weights-before.weights))
        assert np.isclose(delta,a['update']['weight_delta_norm'])
        output.append(dict(world=a['official_world_number'],run_id=a['run_id'],goal=a['goal'],
            retention=a['retention'],success=a['success'],actions=a['actions'],
            worker_seconds=a['wall_seconds'],ticks=a['ticks'],
            confirmed_breaks=episode['confirmed_breaks'],inventory=episode['inventory'],
            training_applied=a['training_applied'],weight_delta_norm=delta,
            checker_report_sha256=digest(Path(a['checker_report']))))
    destination=ops/'first_cycle_audit.json'
    if destination.exists():raise FileExistsError('Preserve the existing first-cycle audit')
    atomic_json(destination,dict(scope='Training outcomes only; not held-out reliability scores.',
        trials=8,successes=sum(a['success'] for a in rows),
        verified_updates=sum(a['training_applied'] for a in rows),episodes=output))
    print(json.dumps(dict(trials=8,successes=sum(a['success'] for a in rows),
        verified_updates=sum(a['training_applied'] for a in rows))))


if __name__=='__main__':main()

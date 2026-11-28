"""Recheck sealed round-2 scores and original evidence without changing them."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.evidence import audit_run, file_sha256
from autonomy.staged import gate_report

OPS = Path(__file__).resolve().parent


def main():
    folder = ROOT/'experiments/phase9/fc9_stage25'
    state = json.loads((folder/'state.json').read_text())
    config = json.loads((folder/'config.json').read_text())
    rows = [a for a in state['attempts'] if a.get('curriculum_round')==2
            and a['split']=='eval_a' and a['status']=='committed']
    reports = []
    for a in rows:
        original = json.loads(Path(a['checker_report']).read_text())
        for name,sha in original['evidence_sha256'].items():
            assert file_sha256(Path(a['results'])/name)==sha, (a['run_id'],name)
        report = audit_run(a['results'],expected={'world_seed':a['world_seed'],
            'train':False,'implementation_sha256':a['implementation_sha256']})
        assert report['status']=='verified' and len(report['episodes'])==1
        e=report['episodes'][0]
        assert e['success']==a['success'] and not e['training_applied'] and e['weight_delta_norm']==0
        reports.append(dict(run_id=a['run_id'],success=e['success'],
            actions=e['actions'],confirmed_breaks=e['confirmed_breaks'],
            inventory=e['inventory'],original_evidence_hashes_unchanged=True))
    gate=gate_report(rows,'terrain')
    assert len(reports)==270 and gate==state['gates']['terrain']
    for record in (state['current_checkpoint'],config['frozen_checkpoint'],config['checker']['graph']):
        assert file_sha256(record['path'])==record['sha256']
    path=OPS/'round2_reaudit.json'
    if path.exists():raise FileExistsError('Preserve the existing re-audit')
    path.write_text(json.dumps(dict(finished_unix=time.time(),verified_episodes=len(reports),
        gate=gate,checkpoint=state['current_checkpoint'],graph=config['checker']['graph'],
        reports=reports),indent=2)+'\n')
    print('270 episodes reverified; zero evaluation updates; hashes and scores unchanged.')


if __name__=='__main__':main()

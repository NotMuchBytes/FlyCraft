"""Record actual match limits without changing any completed score."""
import collections
import json
from pathlib import Path

OPS=Path(__file__).resolve().parent


def main():
    state=json.loads((OPS/'before_round3_at530/state.json').read_text())
    rows=[a for a in state['attempts'] if a.get('curriculum_round')==2
          and a['split']=='eval_a' and not a['retention']]
    groups=[]
    for index in range(30):
        group=[a for a in rows if a['evaluation_index']==index]
        assert len(group)==5
        starts={a['condition']:json.loads((Path(a['results'])/'server.jsonl.initial.jsonl').read_text().splitlines()[0]) for a in group}
        reference=starts['trained']
        expected={tuple(b['position']):b['state'] for b in reference['fixture_blocks']}
        differences={}
        for condition,start in starts.items():
            actual={tuple(b['position']):b['state'] for b in start['fixture_blocks']}
            diff=[dict(position=p,trained=expected.get(p),control=actual.get(p))
                  for p in sorted(expected.keys()|actual.keys()) if expected.get(p)!=actual.get(p)]
            if diff:differences[condition]=diff
            assert start['position_xyz_yaw_pitch']==reference['position_xyz_yaw_pitch']
            assert start['inventory']==reference['inventory']
            # Every log and terrain-step block must match; disclose all foliage differences.
            assert {p:v for p,v in actual.items() if 'leaves' not in v} == {p:v for p,v in expected.items() if 'leaves' not in v}
        for key in ('world_seed','layout_seed','policy_seed'):
            assert len({a[key] for a in group})==1
        assert len({json.dumps(a['profile'],sort_keys=True) for a in group})==1
        groups.append(dict(evaluation_index=index,full_fixture_match=not differences,
            differences=differences,successes={a['condition']:a['success'] for a in group}))
    exact=[g for g in groups if g['full_fixture_match']]
    output=dict(scope='Retrospective match audit; official scores preserved, no rescoring or reruns.',
        matched_pose_inventory_seed_policy_rng_profile_groups=30,
        matched_resource_and_step_blocks_groups=30,full_fixture_match_groups=len(exact),
        exact_subset_descriptive_scores={c:sum(g['successes'][c] for g in exact)
                                       for c in ('trained','frozen','uniform','no_neural','shuffled')},
        exact_subset_denominator=len(exact),groups=groups,
        limitation='Two groups differ by one nonpersistent leaf; cause not isolated. No exact full-world or entity RNG replay is claimed.')
    destination=OPS/'round2_match_audit.json'
    if destination.exists():raise FileExistsError('Preserve the existing match audit')
    destination.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k!='groups'},indent=2))


if __name__=='__main__':main()

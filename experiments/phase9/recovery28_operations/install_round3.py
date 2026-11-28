"""One-shot, evidence-gated migration to a fixed retention-focused recovery."""
import collections
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from autonomy.experiment import CampaignLock, atomic_json, digest, seed_catalog, source_manifest
from autonomy.staged import StagedCampaign, gate_report, RETENTION_MINIMUMS

OPS = Path(__file__).resolve().parent


def main():
    baseline = json.loads((OPS/'baseline_status.json').read_text())
    assert {r['checkout'] for r in baseline} == {'curriculum','development'}
    assert all(r['returncode'] == 0 for r in baseline)
    for label, count in [('curriculum',183),('development',187)]:
        text = (OPS/(label+'_baseline_tests.txt')).read_text()
        assert f'Ran {count} tests' in text and text.rstrip().endswith('OK')
    diagnosis = json.loads((OPS/'round2_diagnosis.json').read_text())
    assert len(diagnosis['episodes']) == 270
    reaudit = json.loads((OPS/'round2_reaudit.json').read_text())
    assert reaudit['verified_episodes'] == 270 and reaudit['gate'] == diagnosis['gate']
    folder = ROOT/'experiments/phase9/fc9_stage25'
    with CampaignLock(folder):
        config,state,catalog = [json.loads((folder/name).read_text()) for name in ('config.json','state.json','seeds.json')]
        assert digest(folder/'state.json') == diagnosis['state_sha256']
        assert digest(folder/'config.json') == state['config_sha256']
        assert digest(folder/'seeds.json') == config['catalog_sha256']
        assert state['active_attempt'] is None and state['status'] == 'stage_gate_failed'
        assert state['curriculum_rounds'] == {'terrain':2}
        assert config['execution_revision'] == 4 and len(state['attempts']) == 1002
        assert all(a['status']=='committed' or a.get('unscored_technical_retry') for a in state['attempts'])
        rows = [a for a in state['attempts'] if a.get('curriculum_round') == 2]
        gate = gate_report(rows,'terrain')
        assert gate == state['gates']['terrain'] == diagnosis['gate']
        assert gate['complete'] and not gate['passed']
        assert gate['primary_successes'] == dict(trained=28,frozen=14,uniform=2,no_neural=0,shuffled=14)
        assert gate['retention_successes'] == dict(one_log=20,three_logs=30,planks=18,wooden_pickaxe=27)
        assert gate['retention_minimums'] == RETENTION_MINIMUMS and gate['minimum_successes'] == 24
        assert source_manifest(ROOT)['implementation_sha256'] == config['implementation_sha256']
        assert digest(state['current_checkpoint']['path']) == state['current_checkpoint']['sha256']
        assert digest(config['checker']['graph']['path']) == config['checker']['graph']['sha256']
        assert digest(config['runtime_profile']['launch_cache']['path']) == config['runtime_profile']['launch_cache']['sha256']
        assert not (folder/'STOP').exists() and not (folder/'fix_request.json').exists()
        campaign = StagedCampaign(folder,project_root=ROOT)
        assert campaign.training_worlds() == 530
        archive = OPS/'before_round3_at530'
        archive.mkdir(exist_ok=False)
        preserved = {}
        for name in ('config.json','state.json','summary.json','source_manifest.json','seeds.json','executor.json'):
            shutil.copy2(folder/name,archive/name)
            preserved[name] = digest(archive/name)
        excluded = {9172501}
        for values in catalog.values():
            if isinstance(values,list):
                excluded.update(v for v in values if type(v) is int)
        for a in state['attempts']:
            excluded.update((a['world_seed'],a['layout_seed']))
        # Also exclude every locally recorded diagnostic seed in both checkouts.
        for root in (ROOT,Path(r'C:/Users/anass/Documents/FlyCraft')):
            for path in (root/'experiments').rglob('run.json'):
                run=json.loads(path.read_text())
                for key in ('world_seed','layout_start'):
                    if type(run.get(key)) is int: excluded.add(run[key])
                excluded.update(v for v in run.get('layout_seeds',[]) or [] if type(v) is int)
        fresh = seed_catalog(2026112803,training=1,pilot=1,evaluation=150,exclude=excluded)['eval_a']
        assert not set(fresh)&excluded and len(set(fresh)) == 150
        catalog['repair_terrain_3'] = fresh
        schedule = ['primary','retention_one_log','retention_planks','primary',
                    'retention_one_log','retention_planks','retention_three_logs','retention_wooden_pickaxe']
        mix = dict(collections.Counter(schedule*16))
        assert mix == dict(primary=32,retention_one_log=32,retention_planks=32,
                           retention_three_logs=16,retention_wooden_pickaxe=16)
        repair = dict(training_worlds=128,training_schedule=schedule,evaluation_catalog='repair_terrain_3',
            authorization='User: carry on then; do not stop for routine decisions; PC left on for extended periods, 2026-11-28',
            authorized_date='2026-11-28',
            rationale='Round 2 passes terrain but flat one-log/planks regress before resource acquisition. Increase short-flat rehearsal while retaining terrain and long-goal practice.',
            predeclared_training_mix=mix,evaluation_episodes=270,automatic_gate_bypass=False)
        config['repair_rounds']['terrain']['3'] = repair
        config['execution_revisions'].append(dict(execution_revision=4,
            implementation_sha256=config['implementation_sha256'],config_sha256=state['config_sha256'],
            archive=str(archive),retired_after_world=530,
            reason='Completed failed round 2 preserved; user authorized reviewed retention-focused recovery; unchanged actor/reward/interface/budgets/thresholds'))
        config['execution_revision'] = 5
        state.setdefault('round_history',[]).append(dict(stage='terrain',round=2,gate=gate,
            checkpoint=dict(state['current_checkpoint']),archive=str(archive)))
        state['curriculum_rounds']['terrain'] = 3
        state['status'] = 'repair_ready'
        atomic_json(OPS/'round3_protocol.json',dict(created_unix=time.time(),repair=repair,
            previous_gate=gate,preserved_files=preserved,archive=str(archive),
            checkpoint_before=dict(state['current_checkpoint']),graph=config['checker']['graph'],
            implementation_sha256=config['implementation_sha256'],actor_reward_interface_changed=False,
            thresholds_changed=False,training_catalog_unchanged=True,fresh_evaluation_seeds_disjoint=True,
            final_evaluation_untouched=True,worlds_before=530,maximum_worlds_after_round=658))
        # Publish dependencies before the ready ledger. Intermediate hash mismatch fails closed.
        atomic_json(folder/'seeds.json',catalog)
        config['catalog_sha256'] = digest(folder/'seeds.json')
        atomic_json(folder/'config.json',config)
        state['config_sha256'] = digest(folder/'config.json')
        atomic_json(folder/'state.json',state)
        campaign = StagedCampaign(folder,project_root=ROOT)
        campaign.save()
        assert campaign.training_worlds() == 530
        assert campaign.next_cell() == dict(split='training',condition='trained',goal='one_log',retention=False)
        for name in ('config.json','seeds.json','source_manifest.json'):
            shutil.copy2(folder/name,OPS/('round3_'+name))
        print('Frozen round 3: 128 training slots; then 270 fresh evaluation episodes. All gates unchanged.')


if __name__ == '__main__':
    main()

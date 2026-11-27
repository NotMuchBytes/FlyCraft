"""Freeze a bounded joint-rehearsal recovery; never erase a failed gate."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from autonomy.experiment import CampaignLock,atomic_json,digest,seed_catalog,source_manifest
from autonomy.staged import StagedCampaign,gate_report,RETENTION_MINIMUMS


def main():
    folder=ROOT/'experiments/phase9/fc9_stage25';ops=Path(__file__).resolve().parent
    tests=ops/'baseline_tests.txt'
    assert 'Ran 183 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    with CampaignLock(folder):
        config,state,catalog=[json.loads((folder/name).read_text()) for name in ('config.json','state.json','seeds.json')]
        assert digest(folder/'config.json')==state['config_sha256']
        assert digest(folder/'seeds.json')==config['catalog_sha256']
        assert state['active_attempt'] is None and state['status']=='stage_gate_failed'
        assert state['curriculum_rounds']=={'terrain':1}
        assert config['execution_revision']==3 and len(state['attempts'])==636
        assert all(a['status']=='committed' or a.get('unscored_technical_retry') for a in state['attempts'])
        rows=[a for a in state['attempts'] if a.get('curriculum_round')==1]
        gate=gate_report(rows,'terrain')
        assert gate==state['gates']['terrain'] and gate['complete'] and not gate['passed']
        assert gate['primary_successes']['trained']==19 and gate['retention_successes']==dict(one_log=26,three_logs=27,planks=21,wooden_pickaxe=25)
        assert source_manifest(ROOT)['implementation_sha256']==config['implementation_sha256']
        assert digest(state['current_checkpoint']['path'])==state['current_checkpoint']['sha256']
        assert digest(config['runtime_profile']['launch_cache']['path'])==config['runtime_profile']['launch_cache']['sha256']
        assert not (folder/'STOP').exists() and not (folder/'fix_request.json').exists()
        archive=ops/'before_round2_at434';archive.mkdir(exist_ok=False)
        preserved={}
        for name in ('config.json','state.json','summary.json','source_manifest.json','seeds.json','executor.json'):
            shutil.copy2(folder/name,archive/name);preserved[name]=digest(archive/name)
        excluded={9172501}
        for values in catalog.values():
            if isinstance(values,list):excluded.update(v for v in values if type(v) is int)
        for a in state['attempts']:excluded.update((a['world_seed'],a['layout_seed']))
        fresh=seed_catalog(2026112702,training=1,pilot=1,evaluation=150,exclude=excluded)['eval_a']
        assert not (set(fresh)&excluded) and len(set(fresh))==150
        catalog['repair_terrain_2']=fresh
        schedule=[]
        for goal in RETENTION_MINIMUMS:schedule.extend(('primary','primary','retention_'+goal))
        # Eight fixed twelve-world cycles: 64 terrain and eight of each wood goal.
        repair=dict(training_worlds=96,training_schedule=schedule,evaluation_catalog='repair_terrain_2',
            authorization='User: carry on, after stage_gate_failed status, 2026-11-27',authorized_date='2026-11-27',
            rationale='Practice the seen-but-unmined terrain failures while rehearsing all retained skills; previous one-log-heavy repair restored retention but did not pass terrain.',
            predeclared_training_mix=dict(primary=64,retention_one_log=8,retention_three_logs=8,retention_planks=8,retention_wooden_pickaxe=8),
            evaluation_episodes=270,automatic_gate_bypass=False)
        config['repair_rounds']['terrain']['2']=repair
        config['execution_revisions'].append(dict(execution_revision=3,implementation_sha256=config['implementation_sha256'],
            config_sha256=state['config_sha256'],archive=str(archive),retired_after_world=434,
            reason='User requested continuation after completed round-1 failed gate; bounded joint rehearsal with fresh evaluation, unchanged actor/reward/thresholds'))
        config['execution_revision']=4
        state.setdefault('round_history',[]).append(dict(stage='terrain',round=1,gate=gate,
            checkpoint=dict(state['current_checkpoint']),archive=str(archive)))
        state['curriculum_rounds']['terrain']=2;state['status']='repair_ready'
        atomic_json(folder/'seeds.json',catalog);config['catalog_sha256']=digest(folder/'seeds.json')
        atomic_json(folder/'config.json',config);state['config_sha256']=digest(folder/'config.json')
        atomic_json(folder/'state.json',state)
        campaign=StagedCampaign(folder,project_root=ROOT);campaign.save()
        assert campaign.training_worlds()==434
        assert campaign.next_cell()==dict(split='training',condition='trained',goal='one_log',retention=False)
        atomic_json(ops/'round2_protocol.json',dict(created_unix=time.time(),authorization=repair['authorization'],
            repair=repair,previous_gate=gate,preserved_files=preserved,archive=str(archive),
            graph=config['checker']['graph'],checkpoint_before=dict(state['current_checkpoint']),
            implementation_sha256=config['implementation_sha256'],actor_reward_interface_changed=False,
            thresholds_changed=False,training_catalog_unchanged=True,fresh_evaluation_seeds_disjoint=True,
            final_evaluation_untouched=True,worlds_before=434,maximum_worlds_after_round=530))
        for name in ('config.json','seeds.json','source_manifest.json'):shutil.copy2(folder/name,ops/('round2_'+name))
        print('Frozen recovery round 2: 96 training worlds; 270 fresh evaluation episodes; all gates unchanged.')


if __name__=='__main__':main()

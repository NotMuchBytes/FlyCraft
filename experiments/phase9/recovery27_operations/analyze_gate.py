"""Read-only diagnosis of the two completed terrain evaluations."""
import collections
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[3]
state=json.loads((ROOT/'experiments/phase9/fc9_stage25/state.json').read_text())
output=[]
for row in state['attempts']:
    if row['split']!='eval_a' or row.get('evaluation_task')!='primary' or row['status']!='committed':continue
    folder=Path(row['results'])
    initial=json.loads((folder/'server.jsonl.initial.jsonl').read_text().splitlines()[0])
    logs=sorted({tuple(b['position'][:1]+b['position'][2:]) for b in initial['fixture_blocks'] if 'oak_log' in b['state']})
    steps=sorted(tuple(b['position']) for b in initial['fixture_blocks'] if 'stone' in b['state'])
    records=[json.loads(line) for line in (folder/'headless.jsonl').read_text().splitlines()]
    ends=[r['data'] for r in records if r['event']=='action_end']
    actions=collections.Counter(r['ack']['action'] for r in ends)
    blocked=collections.Counter(r['ack']['action'] for r in ends if r['ack'].get('error')=='blocked')
    breaks=sum(bool(r['ack'].get('block_changed')) for r in ends)
    requests=[]
    for line in (folder/'bridge.jsonl').read_text().splitlines():
        request=json.loads(line)['request']
        if isinstance(request,str):request=json.loads(request)
        if request.get('control',{}).get('active'):requests.append(request)
    telemetry=[r['telemetry'] for r in requests]
    initial_position=initial['position_xyz_yaw_pitch']
    distance=max(((t['position'][0]-initial_position[0])**2+(t['position'][1]-initial_position[2])**2)**.5 for t in telemetry) if telemetry else 0
    latest=telemetry[-1] if telemetry else {}
    visible=sum(t.get('visible',False) for t in telemetry)
    failure='success' if row['success'] else 'broke_without_pickup' if breaks else 'never_saw_log' if not visible else 'saw_but_no_break'
    output.append(dict(run_id=row['run_id'],round=row.get('curriculum_round',0),condition=row['condition'],seed=row['world_seed'],
        evaluation_index=row['evaluation_index'],success=row['success'],failure=failure,logs=logs,steps=steps,
        actions=dict(actions),blocked=dict(blocked),breaks=breaks,visible_samples=visible,samples=len(telemetry),
        max_displacement=distance,final_inventory=latest.get('inventory'),elapsed_seconds=row['wall_seconds']))
summary=[]
for round_number in (0,1):
    for condition in ('trained','frozen','uniform','no_neural','shuffled'):
        rows=[r for r in output if r['round']==round_number and r['condition']==condition]
        summary.append(dict(round=round_number,condition=condition,n=len(rows),successes=sum(r['success'] for r in rows),
            failures=dict(collections.Counter(r['failure'] for r in rows if not r['success'])),
            median_actions=statistics.median(sum(r['actions'].values()) for r in rows),
            median_elapsed_seconds=statistics.median(r['elapsed_seconds'] for r in rows),
            geometry_counts=dict(collections.Counter(str((r['logs'],r['steps'])) for r in rows))))
destination=Path(__file__).with_name('gate_diagnosis.json')
destination.write_text(json.dumps(dict(scope='Completed evaluations are now development evidence; thresholds unchanged',summary=summary,episodes=output),indent=2),newline='\n')
print(json.dumps([{k:v for k,v in row.items() if k!='geometry_counts'} for row in summary],indent=2))
print('latest trained failures',json.dumps([r for r in output if r['round']==1 and r['condition']=='trained' and not r['success']],indent=2))

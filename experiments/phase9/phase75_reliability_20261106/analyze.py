"""Summarize preserved local traces; no gameplay, policy or result modification."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUNS = [
    'p75_observation_20261106_a', 'p75_observation_20261106_b', 'p75_observation_20261106_c',
    'p75_mining_interrupt_20261106_a', 'p75_bridge_stall_20261106_a', 'p75_bridge_stall_20261106_b',
]


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


summary = {'kind': 'bounded_development_reliability_checks_not_heldout_evaluation',
           'review_date': '2026-11-06', 'training_updates': 0, 'runs': {}}
for name in RUNS:
    folder = ROOT/'experiments/phase9'/name
    metadata = json.loads((folder/'run.json').read_text(encoding='utf-8'))
    scores, controller = rows(folder/'server.jsonl'), rows(folder/'controller.jsonl')
    trace, bridge = rows(folder/'headless.jsonl'), rows(folder/'bridge.jsonl')
    starts = [event['data'] for event in trace if event['event'] == 'action_start']
    ends = [event['data'] for event in trace if event['event'] == 'action_end']
    issued = [event['response'] | {'response_logged_unix': event['timestamp_unix']}
              for event in bridge if event.get('response', {}).get('command_id', 0) > 0]
    started_ids = {event['command_id'] for event in starts}
    unstarted = [event for event in issued if event['command_id'] not in started_ids]
    result = {'stop_reason': metadata['stop_reason'], 'generated_world_instances': metadata['generated_world_instances'],
              'world_seed': metadata['world_seed'], 'server_results': scores, 'controller_results': controller,
              'action_start_count': len(starts), 'unique_started_command_ids': len(started_ids),
              'issued_but_not_started': unstarted,
              'interrupted_acknowledgments': [event['ack'] for event in ends if event['ack']['status'] == 'interrupted'],
              'operator_faults': metadata.get('operator_fault_events', []),
              'maximum_sampled_gpu_c': metadata['maximum_sampled_gpu_c'],
              'minimum_available_ram_mib': metadata['minimum_sampled_available_ram_mib'],
              'client_exited_cleanly': metadata['client_exited_cleanly'],
              'server_exited_cleanly': metadata['server_exited_cleanly'],
              'video_status': metadata['milestone_video_status'], 'video': metadata.get('milestone_video'),
              'implementation_sha256': metadata['implementation_sha256']}
    if 'visual_review' in metadata:
        result['visual_review'] = metadata['visual_review']
    if name == 'p75_bridge_stall_20261106_a':
        result['fault_valid'] = False
        result['fault_limitation'] = 'Only venv launcher paused; serving child continued. Exclude from bridge recovery claims.'
    if name == 'p75_bridge_stall_20261106_b':
        fault = result['operator_faults'][0]
        result['measured_process_tree_stall_seconds'] = fault['resumed_unix'] - fault['requested_unix']
        result['bridge_records_during_stall'] = sum(fault['requested_unix'] < event['timestamp_unix'] < fault['resumed_unix'] for event in bridge)
        result['subsequent_request_ack_ids'] = [json.loads(event['request']).get('ack', {}).get('command_id') for event in bridge[2:]]
    summary['runs'][name] = result
summary['generated_world_instances'] = sum(run['generated_world_instances'] for run in summary['runs'].values())
summary['distinct_world_seeds'] = len({run['world_seed'] for run in summary['runs'].values()})
summary['scored_episodes'] = sum(len(run['server_results']) for run in summary['runs'].values())
summary['missing_startup_recordings'] = [name for name, run in summary['runs'].items() if run['video_status'] == 'missing']
summary['graph_sha256'] = hashlib.sha256((ROOT/'data/processed/connectome_raw_csr.npz').read_bytes()).hexdigest()
summary['checkpoint_sha256'] = hashlib.sha256((ROOT/'checkpoints/phase9/dev_pilot_20261029_b_pilot_trained_00002_a0003/trial_0000.npz').read_bytes()).hexdigest()
(HERE/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
print(json.dumps({key: value for key, value in summary.items() if key != 'runs'}, indent=2))

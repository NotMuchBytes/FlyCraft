"""Retain automated metadata, then add the manual review of actual MP4 frames."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
NAME = 'p75_bridge_stall_20261106_b'
review = {
    'review_date': '2026-11-06', 'playable_mp4': True,
    'visual_coverage': 'partial_game_menu_obscures_gameplay',
    'observed_gameplay_frame_seconds': 14,
    'observed_menu_frame_seconds': [18, 22],
    'cause': 'Menu origin not established; no desktop input was injected by the runner',
    'original_actions_and_game_logs_unchanged': True,
    'full_visual_reconstruction': 'Unavailable: original interval was obscured and exact world/entity RNG replay is unverified',
}
for path in [ROOT/'experiments/phase9'/NAME/'run.json', ROOT/'recordings/phase9/youtube'/(NAME+'.json')]:
    original = path.with_name(path.stem+'.pre_visual_review.json')
    if original.exists():
        raise SystemExit('Review backup already exists; preserve the existing assessment')
    shutil.copy2(path, original)
    value = json.loads(path.read_text(encoding='utf-8'))
    review['automated_metadata_backup_sha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
    value['visual_review'] = dict(review)
    if path.name == 'run.json':
        value['milestone_video_status'] = 'partial_visual_coverage'
        value['milestone_video']['episode_coverage_complete'] = False
    else:
        value['status'] = 'partial_visual_coverage'
        value['video']['episode_coverage_complete'] = False
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
print('Preserved originals and marked partial visual coverage; MP4 bytes unchanged')

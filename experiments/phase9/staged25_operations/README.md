# Staged curriculum handoff and first milestone

Revision 2 is installed after verified slot 350, with the old config, source
and state preserved under `revision_0001_at350`. All **166 tests pass**. It
matches natural control starting poses to native reference records and gates
all four wood skills at 24/30, 21/30, 21/30 and 15/30, alongside the primary
24/30 goal. It changes no actor, reward, checkpoint, training seed or budget.
`revision2_review.json` records the exact four changed production modules.

The first twelve new training episodes scored **6/12** (terrain 4/9, retention
2/3), with 11 verified updates. Both original milestone MP4s, 339 and 350,
passed complete decode and sampled review. A separate five-condition natural
pilot reproduced the same actual starting pose, RNG and 600-tick budget.
Every condition scored **0/1**, with zero learning updates and no visible
target. It demonstrates matched execution and persistent exploration weakness,
not improved reliability. See `through350_audit.json`,
`natural_interface_pilot.json` and `natural_pilot_exploration_audit.json`.
The report-aggregation exception after its trained trial was repaired by
auditing that already completed episode; its actions were never rerun.
Its source is retained separately from the final retention-gate revision.

The user authorized switching the remaining 9,662 training slots to a broader
curriculum, preserving the first 338 foundation world instances. The active
ledger is in the isolated real checkout at
`C:/Users/anass/Documents/Codex/FlyCraft-curriculum/experiments/phase9/fc9_stage25`.
The original wood-only ledger remains stopped and unchanged.

`frozen_config.json`, `frozen_seeds.json` and `frozen_source_manifest.json`
preserve the executable terrain/exploration protocol. Later skill interfaces
are explicitly pending. Full details: `docs/phase9_staged_curriculum.md`.

The release suite passed **163 tests**. Two evaluation-only matched teaching
probes both failed collection and are retained with hash-verified source
reconstructions. The first four actual training episodes passed independent
audits, checkpoint-delta and chain checks: **2/4** successes, terrain **1/3**,
one-log retention **1/1**, four verified updates. These are training scores,
not held-out reliability or a causal learning advantage. See
`first4_audit.json` for intervals, actions, times and complete evidence hashes.

Official milestone 339 is an original synchronized spectator recording:
`C:/Users/anass/Documents/Codex/FlyCraft-curriculum/recordings/phase9/FlyCraft_Phase9_Milestone_00339_fc9_stage25_terrain_00001.mp4`.
Export:
`C:/Users/anass/Documents/Codex/2026-11-17/continue-developing-the-actual-flycraft-minecraft/outputs/FlyCraft_Phase9_Milestone_00339_fc9_stage25_terrain_00001.mp4`.
It is 25.1 seconds, Minecraft-window-only OBS capture on the RTX 4050.
It passed independent capture preflight, complete decode twice and sampled
manual review. The success used 13 actions and 264 ticks, two policy-selected
jumps, two actual breaks and one log received. It is not a replay or a neural
learning comparison. The transferred foundation already supplied the behavior.

`finish_when_staged_verified.py` replaces the cancelled wood-only shutdown
watcher. It requires the full 10,000-world combined lineage, completed skills
and gates, final checkpoint and freshly verified evidence/videos. Pending
skills, a failed gate, STOP or error cannot shut the PC down. The original
60-second cancellable shutdown uses no forced-close flag. The native power
guard watches both the original and staged STOP files, retains the critical
battery release and permits screen locking. No fan-speed change is verified.

The hidden bounded launcher for the first four episodes exited successfully.
The continuation uses the frozen source and a checked background runner.
Routine worlds are reclaimed only after independent evidence verification;
recorded milestones, episode logs and checkpoints are retained.

# Phase 7.5 reliability checks — November 6, 2026

The [follow-up](phase75_rejection_recovery_20261106.md) fixes the delayed-response
defect reproduced below and documents the recorded retry.

Phase 7.5, Phase 8 and Phase 9 remain incomplete. Work stopped at a reproduced
bridge-recovery defect, as requested. No official campaign or training started.

## Observation accounting fix

The resource controller committed inventory and mining acknowledgments before
validating position and target geometry. A packet with a valid inventory revision
but NaN geometry raised an error after mutating the ledger. Retrying its same
acknowledgment counted one block twice. This corrupted a metric; it did not
double actual inventory or independently prove collection.

Pose/visible geometry now validate before ledger mutation. A rejected packet
retains its pending command and returns an observation-only response. Five
invalid observations terminate rather than replaying an action. The same two
regression tests against `19f16e5` produced five subcase errors; the corrected
implementation passes. A separate identical-ack diagnostic measured block counts
**1 after rejection / 2 after retry** before the fix, versus **0 / 1** afterward,
for one acknowledged action in both cases. These are injected protocol tests.

Baseline: 101 tests passed in 25.137 seconds. Final: **104 tests passed in
20.999 seconds**, including existing Phase 7 simulation, inventory, checkpoint,
recovery, camera and recording regressions. New tests cover rejected-packet
accounting, bounded invalid geometry and detection of unfinished mining. Real
Minecraft 26.2 launch preparation compiled successfully.

## Real Minecraft checks

All runs use the preserved checkpoint, strict crosshair interactions, bounded
camera, two-tick movement and 400-tick episode budgets, with learning disabled.
The policy selects gameplay actions. The harness supplies a controlled flat
survival tree fixture. Operator faults are disruptive tests, not observations
or goal-completing assistance. Fault mode defaults off and rejects training or
multiple-episode requests.

| Attempt | Actual outcome | Actions / ticks | MP4 |
| --- | --- | --- | --- |
| `p75_observation_20261106_a` | Startup RAM guard; zero actions/trials | 0 / unscored | Missing |
| `p75_observation_20261106_b` | AMD renderer rejected; zero actions/trials | 0 / unscored | Missing |
| `p75_observation_20261106_c` | One log confirmed in inventory | 2 / 76 | Verified, 19.633 s |
| `p75_mining_interrupt_20261106_a` | Interrupted, recovered, collected log | 22 / 358 | Verified, 33.700 s |
| `p75_bridge_stall_20261106_a` | Collected log; intended fault not exercised | 10 / 185 | Verified, 26.033 s |
| `p75_bridge_stall_20261106_b` | Bridge stalled; mined but collected no log | 1 / 400 | Playable, partial visual coverage, 36.433 s |

The mining fault rotates the NPC +90 degrees once through the server console
after its mining-start event. The game acknowledged command 1 as
`interrupted/mining_aim_lost` after 17 ticks, with `block_changed=false` and no
inventory log. The existing learned controller recorded one interruption
recovery/replan; a later mining action changed a block and final inventory
contained a log. It also encountered one blocked movement. No successful
action sequence was scripted or model update made.

The first bridge test paused only the Windows virtual-environment launcher;
its interpreter child continued serving. Its gameplay is real but excluded
from bridge-recovery evidence. The corrected harness pauses the owned process
tree, resumes after a bounded interval, and resumes during cleanup if interrupted.
The retry recorded **6.464 seconds** of suspension with zero bridge response
records within that interval.

Six generated instances reuse **one world seed and one layout seed**, with
four scored episodes. They are not six unseen worlds or a multi-seed evaluation.
Relative fixtures/policy seeds match; initial global coordinates and world/entity
RNG are not completely matched. Do not pool fault or launcher-only tests into
ordinary success rates. One check per genuine fault cannot establish reliability.

## Reproduced blocker: discarded command has no rejection acknowledgment

The real bridge-stall retry broke a log normally. A post-mining observation at
tick 775 waited while the bridge was suspended. On resume the controller issued
`FORWARD`, command 2. The adapter's existing 40-tick age guard discarded this
outdated response. That branch cancels local input without acknowledging that
command 2 was not executed; subsequent packets still acknowledge command 1.

The controller consequently waits for command 2 until `acknowledgment_timeout`.
The trace has only command 1 starting/ending, while the bridge log contains an
issued command 2 that never starts. Inventory is zero logs at 400 ticks. Both
game processes exited with code zero: a protocol recovery failure, not a crash
or infinite loop. Its early controller result lacks a terminal inventory snapshot;
final inventory comes from server scoring, so this run cannot support a
transactional training commit.

This diagnosis follows recorded command IDs/timestamps and the adapter's stale
response branch. The defect is **not fixed** here. Next repair should acknowledge
non-execution, reconcile/discard the pending policy decision, and resume sampling
without replay or learning from an invented execution. Repeat this recorded
fault before broader trials or training. A six-second stall is not a full
Minecraft disconnect or checkpoint-restoration test; those remain pending.

## Recording, resources and preservation

Every scored session has a playable, full-decode-verified H.264 MP4, independent
Minecraft/OBS capture preflight and retained checksums. Final review found the
bridge-failure video shows gameplay at 14 seconds but a game menu at 18 and
22 seconds. Its visual coverage is **partial**; menu origin is unestablished.
Automated temporal-coverage metadata was backed up, then amended to disclose
the review. The obscured interval cannot be reconstructed faithfully: exact
world/entity RNG replay is unverified. No replacement or fabricated footage
was produced. This remains a recording limitation despite a playable container.
Original videos were
copied without synthesizing frames or changing actions. The game rendered at
**854x480**, and OBS exported a scaled 1920x1080 stream at 30 fps; this is not
native 1080p or 60 fps. The normal collection footage was inspected during
mining. Both preflight failures have no gameplay to recover and stay explicitly
missing. Retries are new executions, not replays. Earlier missing-footage
disclosures remain unchanged.

The first run reached 690.30 MiB free RAM and stopped at the three-sample
768 MiB guard. The idle CurseForge launcher was closed under existing user
authorization. The NVIDIA preference was absent; restoring only FlyCraft's
Java `GpuPreference=2;` selected RTX 4050 in the next actual renderer log.
No global GPU preference or another application's setting changed. Scored
sessions retained at least 909.80 MiB free RAM in samples. Maximum sampled GPU
temperature across attempts was 53 C; CPU temperature was unavailable.
No extended or overnight training ran.

The graph remains 139,255 neurons. Graph SHA-256:
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.
Checkpoint SHA-256:
`acdde37f8d3288764bcaad9dc9eea7c4f916c9894f54a019684fc3f555dd37f5`.
There were **zero new training updates**; no neural contribution or learning
gain is established. Historical 27/30 log and 21/30 plank results stay separate.
Three-log/pickaxe, broader neural controls, natural-terrain collection, companion
stop/respawn and full disconnect restoration remain pending.

Portable evidence/reproducible analysis:
`experiments/phase9/phase75_reliability_20261106/`. Each attempt retains a source
manifest and run/recording metadata. Raw JSONL, worlds, logs, MP4s and screenshots
remain local. Media mappings are in `recordings/phase9/youtube/`; the chat
workspace's `outputs/` contains exports. No raw failure was relabeled a pass.

Repair rejected-command recovery first, then repeat faults and restoration.
Only afterward expand strict longer-goal motor affordances/crafting and matched
learning/retention tests. The original Phase 9 requirement calls for explicit
full-campaign authorization after readiness; the 10,000-world run has not started.

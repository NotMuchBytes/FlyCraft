# FlyCraft Phase 9 development report

**November 26 — automatic resume and retention repair:** execution revision 3
preserves the failed stage at world 402 and starts a reviewed 32-world repair
round with a new evaluation seed set. It keeps the original checkpoint chain,
actor, reward, budgets and gate thresholds. The first repair trial succeeded
in six actions with a verified update. All 183 tests pass. Windows sign-in
startup, supervisor crash recovery and duplicate-owner protection are verified;
pre-login boot registration was denied by Windows permissions. Quality failures
still park, and later Minecraft skills remain unimplemented. The completed
stage's 334 episodes were independently re-audited without changed scores.
[Setup, results and operational limits](docs/phase9_auto_resume.md).

**November 25 — staged revision 2:** through world 350, the new course scored
6/12 training successes (terrain 4/9; retention 2/3), with 11 independently
verified updates. Milestones 339 and 350 passed full decode and sampled
review. A separate five-condition natural interface pilot used identical
recorded native poses, seed, RNG and budget; every condition scored 0/1 and
made zero updates. All 166 tests pass. Revision 2 preserves the source and
ledger at 350, rejects unmatched natural starts and requires all four wood
retention gates. It changes no actor, reward, readout, training seeds or
training budgets. Natural exploration and later skills remain unfinished.
[Results, limits and source lineage](docs/phase9_staged_curriculum.md).

**November 25 — broader curriculum started:** the original campaign is
preserved and paused at 338 generated worlds and 337 scored episodes. The
remaining training budget is allocated to validated stages rather than a
10,000-world wood-only schedule. All 163 tests pass. The first new curriculum
world (slot 339) collected one log in 13 actions and 264 ticks, with a verified
readout update and Minecraft-only RTX 4050 milestone footage that passed full
decode. Two prior matched development probes both failed collection, despite
verified jump execution. No broader held-out success rate or neural advantage
has been established. Terrain and natural exploration have explicit training,
five-condition evaluation and retention gates; stone tools, food/shelter,
combat and later progression still require implemented, validated interfaces.
[Protocol, evidence and operational limits](docs/phase9_staged_curriculum.md).

**November 25 — faster execution revision 2:** after 320 scored worlds
(280 successes), world 321 exposed a Windows atomic-publication sharing race
and remained unscored. The failure and all prior results were preserved. A
bounded publication retry, hash-verified launch cache and continuous unchanged
resource window passed **155 tests** and eight fresh live evaluation episodes
with no learning updates. Warmed time outside a worker fell from 32.4 to 2.1
seconds; routine worker overhead fell from 27.7 to 20.1 seconds. The versioned
campaign resumed at world 322 with the same checkpoint chain and seed catalog.
[Complete timing pilot, source history and recording evidence](experiments/phase9/fc9_20261125_operations/performance_revision_0002.md).
The user has also selected a broader staged curriculum for the remaining
budget; additional skills require their own implemented interfaces and live
validation before training. These are not yet supported by the four wood goals.

**November 25 — 274-world audited snapshot:** the original frozen campaign is
still running. A read-only re-audit reproduced all **274 scores (238 successes)**
and the checkpoint chain with zero discrepancies. Training counts are one-log
66/69, three-log 59/69, planks 65/68 and pickaxe 48/68; these are not held-out
evaluation scores. All **149 tests pass**. Nine milestone MP4s through world 250
passed another full decode, with sampled manual review of the newer recordings.
The original source/graph/checkpoints, guards and pending final evaluation are
unchanged. [Counts, action/time statistics, failures and recording paths](experiments/phase9/fc9_20261125_operations/progress_00274.md).

**November 25, 2026 — official launch authorized:** the user explicitly said
“start the 10000”, requested milestone recordings and authorized a temporary
shutdown guard. The official executor now supports a frozen balanced four-goal
schedule over 10,000 distinct generated training-world slots. All **145 tests
pass**; this includes interrupted-world accounting, worker-plan binding and
safe disposable-world cleanup. The original graph, actor and prior checkpoints
are preserved. [Official design, limits and recording schedule](docs/phase9_official_campaign.md).
The official campaign **has started**. Its first four scheduled milestones scored
**3/4**: one-log 1/1, three-log 1/1, planks 1/1 and pickaxe 0/1. The pickaxe
failure reached sticks but missed the fixed tick budget; it remains a scored
failure. All four training updates and Minecraft-only RTX 4050 MP4s passed the
independent gate, full decode and sampled manual review. Training continues in
the background; routine verified world cleanup is working. These small training
counts are not final evaluation or a reliability estimate.
[Verified launch audit and video paths](experiments/phase9/fc9_20261125_operations/launch_audit.json),
[host operations, shutdown condition and fan limitation](experiments/phase9/fc9_20261125_operations/README.md).
Live counters are in the local campaign ledger. Historical authorization
and usage-cap statements below are superseded by the explicit instructions.
The untouched final 100-world evaluation remains separate from training.

**November 24 checker development verified:** the local checked supervisor and
Codex repair handoffs are implemented. The frozen functional pilot completed eight
verified successes across all four goals, including two verified development
readout updates. STOP interrupted mining without a successful acknowledgment;
its fresh resumed attempt succeeded. Nine disposable worlds include that
unscored interruption. The preselected pickaxe milestone passed full playback
and manual review. This small pilot establishes neither reliability nor a
learning/neural advantage.

All 136 tests pass after hardening malformed-evidence handling and preserving
valid game outcomes when video verification fails. A fresh smoke trial of the
hardened version also succeeded, giving **nine successful functional episodes
across ten generated disposable worlds**, including the unscored interruption.
The two training episodes produced verified readout changes; all seven new
evaluation episodes have zero weight updates. The minimum sampled available
RAM was 1,874.43 MiB and maximum GPU temperature 53°C. The 768 MiB RAM,
2,048 MiB disk and 75°C GPU guards stayed enabled; CPU temperature is unavailable.
Original graph/checkpoints and actor
source remain unchanged; only coordination/validation/recorder lifecycle code
changed. The 10,000-world campaign remains unauthorized and unstarted.
[Protocol and verified pilot evidence](experiments/phase9/checker_development_20261124/README.md),
[release audit](experiments/phase9/checker_development_20261124/release_audit.json),
[checker operation and limits](docs/phase9_checker.md)

The final source hash is
`1f66c63d78e288ddc042a9cffeb845bba688ee207d56ef557d767321cc35bb7e`.
The original graph hash remains
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.
The validated Phase 8 checkpoint remains the default; the two newly saved
training checkpoints are development artifacts, not a replacement selected
for reliability. Re-auditing with the hardened checker reproduces all 152
archived Phase 8 scores and the frozen pilot records exactly.

The preselected recorded pickaxe succeeded in 89 actions, 67.737 wall seconds
and 67.9 game seconds. Its Minecraft-only first-person RTX 4050 recording is
82.833 seconds and passed full decode and manual review. The original footage
is unedited, includes ordinary loading/tutorial UI, and is a fresh development
execution rather than an exact replay. Its export is
`C:\Users\anass\Documents\Codex\2026-11-17\continue-developing-the-actual-flycraft-minecraft\outputs\FlyCraft_Development_Milestone_00001_checker24_pick_eval_a_trained_00001_a0001.mp4`.
[Recording metadata](recordings/phase9/youtube/checker24_pick_eval_a_trained_00001_a0001.json),
[manual review and functional audit](experiments/phase9/checker_development_20261124/pilot_audit.json)

Fix requests pause execution and preserve evidence hashes plus a local Markdown
handoff for Codex. During a Codex-managed batch the attention result returns to
the agent. Standalone execution does not wake an idle chat; no external AI
service or automatic code patching is configured. Long-run/parallel operation,
natural-terrain reliability, stronger neural controls and official campaign
authorization remain separate work. The checker is ready for bounded
development use, not a completed or authorized 10,000-world experiment.
[Clearly labeled corrupted-copy handoff example](experiments/phase9/checker_development_20261124/handoff_example/attention/request_0001.md)

**Earlier November 24, 2026:** [Phase 8 controlled validation](PHASE_8_REPORT.md)
is complete at 27/30 one-log, 27/30 three-log, 27/30 four-plank and 19/30
wooden pickaxe, with matched controls and verified milestone footage.
Natural-terrain generalization and neural advantage remain unestablished.
Work is paused for the user's AI-checker discussion. The 10,000-world Phase 9
campaign remains pending separate authorization; no new campaign or checker
implementation was started during this closeout. Historical development
evidence below is preserved.

November 6: the Phase 7.5 reliability increment passed 104 automated tests and
recorded successful strict collection/mining-interruption recovery. A real
bridge process-tree stall exposed a command-rejection acknowledgment defect
and failed pickup; development stopped at that problem. Zero new training
updates or official experiment worlds. See
[the evidence and blocker](docs/phase75_reliability_20261106.md).

Updated: 2026-10-29. Status: **in progress; not a completed 10,000-world experiment**.
The later strict evaluations scored one-log 27/30 and four-plank 21/30 in
controlled fixtures. Three-log/pickaxe targets and broader Phase 7.5 recovery/integration validation
remain incomplete. Earlier reports, checkpoints and experimental data are kept.

## October 28 development increment (preserved history)

- A real dedicated-server survival actor can run without a graphical agent
  client, using the existing 139,255-neuron controller and frozen readout.
  Optional spectator rendering is separate from policy decisions.
- Bounded camera movement and crosshair-only mining are preserved. The actor
  uses ordinary mining progress, player physics and inventory item pickup.
  Headless plank transactions existed but were not yet validated live.
- Terminal snapshots, inventory-ledger sealing and acknowledgment prevent
  delayed observations or late pickups from changing an expired episode.
  Missing/unexecuted terminal actions do not update the readout.
- Direct JVM launch after Gradle preparation removes concurrent build-runtime
  overhead. Bounded heaps and RAM/temperature guards remain active.
- Memory use after controlled neural initialization fell from 242.613 to
  88.180 MiB, with exact matching neural outputs over six tested windows.
  Graph architecture, normalization, population indices and checkpoints are
  unchanged. Diagnostic raw graph access is lazy.
- The latest supplied `Skin.png` is installed unchanged as a local actor skin
  (SHA256 `5f078360e27e104e3ca626996adb6f88f547bad440a72c8b4be966534ac8713c`).
  It is visibly present in the accepted recording; it is not an online account
  skin upload.
- Mandatory milestone video validation now includes actual-window image
  preflight, complete MP4 decode, checksums and preserved failed attempts.
  No footage is generated from synthetic AI actions.

## Real Minecraft results

These are small flat survival fixtures near prepared trees. They do not test
natural forest exploration or 30 independent unseen environments. All completed
initial headless trials used a frozen Phase 8 policy. A subsequent development
trial enabled learning: **one real training world/episode and one readout update**.
This is not an official experiment counter or a demonstrated learning curve.

| Attempt | Completed episodes | Actual result | Recording status |
| --- | ---: | --- | --- |
| `headless_smoke_01` | 1 | 0/1; incorrect initial spawn left the actor falling away from its fixture | Missing MP4; original data retained |
| `headless_recorded_redo_01` | 0 | RAM guard; no scored trial | No confirmed milestone MP4 |
| `headless_recorded_redo_02` | 1 | 1/1 log; block and inventory confirmed | Rejected: MP4 showed wallpaper |
| `headless_recorded_redo_03` | 0 | Client compilation failed before world launch | No MP4; launcher evidence retained |
| `headless_recorded_redo_04` | 1 | 1/1 log; block and inventory confirmed | Accepted: real Minecraft MP4, full decode and visual inspection |
| `headless_learning_pilot_01` | 1 | 1/1 log; real readout training update | Accepted: real Minecraft MP4, full decode and visual inspection |
| `headless_checkpoint_restore_01` | 1 | 1/1 log after loading the new checkpoint; learning disabled | Accepted: real Minecraft MP4, full decode and visual inspection |

The initial attempts reuse development seed/layout 44556777 and differ in implementation
while debugging. Do not pool their outcomes into a generalization success rate.
Each successful worker generated one world instance and ran one episode;
these are not distinct unseen seeds. No official cumulative counter is started.

The accepted redo used two sampled actions, COLLECT_LOG and FORWARD. The game
ended after 75 ticks (3.75 game seconds), with one confirmed block change and
one inventory log. Controller elapsed time was 3.747 seconds and terminal
acknowledgment arrived one tick after scoring. Both game JVMs exited with code
0. The whole supervised job, including preparation and connection, took
85.957 seconds. Peak sampled GPU temperature was 47 C; minimum available RAM
was 2355.906 MiB. Peak sampled process-tree RSS was 114.676 MiB for the bridge,
622.781 MiB for the server and 988.559 MiB for the spectator client. CPU
temperature was unavailable.

The 20.4-second accepted video contains 612 decoded H.264 frames at 30 FPS,
1920x1080 output from a 1280x720 Minecraft window. SHA256:
`a0d46504b199dc49e68d67fe068db216d6aa6e314f352e10ee74010039e26ec6`.
The recording was active before the start gate and retained through terminal
results and shutdown. A manually inspected frame shows the supplied skin in
Minecraft. Initial game tutorial/chat-warning overlays are visible; they have
not been edited out. This is a new execution, **not a replay** of the failed
original. Original missing/rejected footage remains explicitly reported.

The frozen checkpoint SHA256 was
`51f9593274dbbd87c4c9ab2877a0fc2ebd1573ae31831b8957b3b01601e427ca`.
Per-run source manifests and gameplay/action/observation logs remain local at
`experiments/phase9/<run-id>/`. The accepted MP4 and metadata are under
`recordings/phase9/`. Large runtime files, videos and raw logs are Git-ignored.

## Root causes fixed and verification

The headless prototype initially used the player's constructor position rather
than Minecraft's adjusted spawn. It now places the player at vanilla spawn
before fixture setup. The observation sector boundaries were aligned with the
graphical adapter. Terminal lifecycle checks and explicit boundary delivery
prevent stale actions/late inventory packets from being credited to a trial.

The previous recording used OBS Automatic capture with fallback window
matching. It could record wallpaper for this background OpenGL window. The
replacement uses Windows Graphics Capture and an exact unique window title.
Before AI actions, the runner compares an actual game-frame screenshot with an
independent OBS screenshot. The accepted run's normalized RGB error was 0.03066
against a 0.10 threshold. A correct preflight is not continuous frame-content
verification; exported video is also decoded and visually inspected.

The October 28 full suite passed **74 tests in 17.153 seconds**. Tests cover
terminal delivery, late/inconsistent inventory, missing acknowledgments,
unexecuted actions, Java launch argument handling, OBS ownership/framing and
capture configuration, real codec decode/remux/copy, image mismatch rejection,
existing autonomy/learning/checkpoint behavior, and camera kinematics.
Fabric preparation and client/server compilation passed in the accepted run.
Unit tests alone are not evidence of autonomous Minecraft success.

## Learning and neural contribution

At this historical stage there was no Phase 9 matched learning comparison or
causal neural-contribution result. A frozen checkpoint's two-action episode does
not establish learning. Phase 8's assisted 29/30 one-log result and tiny strict
camera comparison remain separate in `PHASE_8_REPORT.md`; assistance differs.
The architecture still uses semantic rays, engineered goals/recovery, prepared
fixtures and bounded action transactions. These are not learned components.
The recording camera follows the actor, but never aims or moves the actor.

The subsequent real-feedback check `headless_learning_pilot_01` trained on
development world/layout seed 44556778: one log, 98 ticks, four actions, reward
9.388307792 and no failed actions. Readout gradient norm was 0.723062489 and
measured weight-change norm 0.036153124, exactly matching the saved session.
Only the readout updates; the fixed connectome is not trained. The new immutable
checkpoint loaded through `AutonomousAgent.load`, with SHA256
`06e41aca4e12b62ae191e22d9214779783485adccc9374f6cd7ddbd2b35c741f`.
Its metadata is at `headless_learning_pilot_01/checkpoint_verification.json`.
This seed is now training data and must not enter any held-out benchmark.
The corresponding 19.633-second MP4 passed full decode, actual-image preflight
and visual frame inspection; GPU maximum was 47 C. The complete job lasted
77.971 seconds. A nonzero policy update is not evidence of better generalization.

`headless_checkpoint_restore_01` loaded that exact saved checkpoint in a new
process and world (development seed 44556779), with learning disabled. Actual
inventory confirmed one log after 106 ticks; four actions were acknowledged.
The checkpoint SHA256 remained unchanged after evaluation. Client/server exited
0; maximum sampled GPU temperature was 49 C. Its 21.733-second MP4 decoded 652
frames, passed actual-image preflight and was visually inspected. This is a
restoration smoke test, not an untouched final benchmark or a matched learning
comparison. A policy response arrived after the scoring boundary and was
correctly rejected as unexecuted. The conservative controller suppressed any
learning and still confirmed success from terminal inventory. Its reward and
subgoal-completion counters omit that passive terminal pickup; this bookkeeping
limitation must be resolved before interpreting training learning curves.

## October 29 implementation and validation

The serial development coordinator now provides frozen source/configuration,
checkpoint and seed-catalog hashes; disjoint pilot, reserved training, Set A
and Set B seeds; durable attempt records; OS-backed coordinator/worker leases;
bounded jobs; STOP/clear-stop; checkpoint validation; and atomic commit/resume.
An interrupted attempt consumes a generated world instance but does not replace
the committed policy. A retry has a fresh attempt ID. The official 10,000-world
executor is deliberately absent. Creating its seed catalog creates no worlds.

The dashboard presents actual resources, inventory, fixed-network activity,
readout inputs/probabilities and separately labeled requested actions. Exported
PNG/SVG figures and CSV use retained observations. A static brain figure selects
the maximum-activity recorded window and discloses that selection; it is not
synthetic neural activity. The live dashboard uses the latest observed window.

Additional bugs fixed:

- Passive terminal pickup now updates inventory memory and goal progress, with
  unassignable reward logged separately and unsafe learning suppressed. It does
  not invent an executed action or accept pickups after the sealed scoring tick.
- Both adapters recheck episode identity before applying asynchronous replies.
  A successful terminal cancellation no longer creates a spurious failed action
  or recovery event. Unsuccessful terminal boundaries remain failures.
- Windows reader-sharing could reject an atomic status-file replacement. A
  bounded retry now preserves the previous complete file instead of aborting
  immediately. Final status is written after owned-process cleanup.
- A one-shot game screenshot could capture an early sky frame while OBS already
  showed the correct scene. Preflight now retries real render-thread screenshots
  before the AI start gate, compares recent independent frames and preserves the
  exact compared bytes. It does not bypass content verification.
- The old shuffled control left central features unchanged. The new control
  permutes the actual window's activity channels; raw and intervened inputs are
  both logged. Historical results using the old control remain separate.

### Automated and build verification

The final full suite passed **90 tests in 16.376 seconds**, including prior
Phase 7 behavior, terminal inventory, action acknowledgments, checkpoint
restoration, camera handling, leases, hash/seed separation, interrupted/resumed
commitment, Windows replacement retries, recording validation and worker cleanup.
Fabric preparation/compilation passed and the final live plank run used the
updated implementation. Tests do not establish Minecraft task reliability.

The 139,255-neuron architecture, 18-step neural window and earlier checkpoints
are preserved. Raw graph SHA256 was reverified as
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.
Only the existing learned readout changes during training.

### Real training and interruption/recovery

Campaign `dev_pilot_20261029_b` committed two new real one-log training episodes:

| Pilot episode | Actions | Game ticks | Reward | Readout change norm |
| --- | ---: | ---: | ---: | ---: |
| 1, attempt a0001 | 15 | 240 | 10.2394853 | 0.0151496 |
| 2, retry a0003 | 5 | 116 | 8.9815853 | 0.0127544 |

Between them, attempt a0002 was stopped after three acknowledged actions. Its
partial MP4 and candidate checkpoint were preserved. The candidate's 0.25 update
was **not promoted**. Resume loaded episode 1's committed checkpoint, generated
a new instance of episode 2's seed, and committed only after real inventory,
terminal acknowledgment, clean exits and verified video agreed. There are now
**three committed Phase 9 real training episodes/updates** including October 28,
plus one discarded candidate update; official experiment count remains zero.
Nonzero updates alone do not establish improved performance.

The latest committed checkpoint SHA256 is
`acdde37f8d3288764bcaad9dc9eea7c4f916c9894f54a019684fc3f555dd37f5`.
The two completed training workers took 153.407 seconds combined, excluding the
interrupted attempt. Throughput estimates now also account for interrupted
attempt wall time and spent generated-world slots; neither measure predicts a
natural-terrain or parallel 10,000-world run reliably.

### Matched real Minecraft policy controls

Campaign `dev_controls_20261029_c` evaluated all five conditions on the same two
development seeds, policy RNG seeds, 400-tick budgets, observations, bounded
15-degree camera commands and crosshair-only interactions. Each episode used a
new world instance; learning was disabled and checkpoint hashes stayed fixed.
Seeds: 810842654367122139 and 5267432988167438838. The frozen reference is the
preserved original Phase 7 policy. Trained uses the latest committed checkpoint.

| Condition | One-log success | 95% Wilson interval | Mean actions | Mean game seconds |
| --- | ---: | --- | ---: | ---: |
| Trained | 1/2 | 9.5%-90.5% | 16 | 11.850 |
| Frozen Phase 7 | 2/2 | 34.2%-100% | 7 | 7.300 |
| Uniform action | 1/2 | 9.5%-90.5% | 19 | 14.175 |
| Neural features removed | 0/2 | 0%-65.8% | 27 | 20.000 |
| Neural features shuffled | 1/2 | 9.5%-90.5% | 19 | 13.975 |

Means include timed-out episodes. All paired exact comparisons to trained give
p=1.0; this tiny sample establishes neither a learning gain nor a causal neural
benefit. No-neural retains bias, planning, memory, masks and context but zeros
three activity inputs. Shuffled retains bias and permutes those inputs to
`[total, left, right]`. Engineered planning remains available to every condition.

The trained failure broke no blocks: repeated unproductive yaw/movement reached
the bounded deadline, with stagnation detection at step 25 and one replan.
Recovery did not solve the task. All failures terminated; no infinite loop was
observed in these bounded trials. Full failure/action data and intervals are in
`experiments/phase9/validation_20261029.json`. Earlier campaign B compared against
its starting policy and a different shuffle definition; do not pool its 1/1
trained and 1/1 frozen checks with this table. Full 100-seed A and final B remain
unrun. Set A is development data, not an untouched final benchmark.

### Real plank collection/crafting milestone

`headless_planks_validation_20261029` began with an actually empty inventory,
broke one log, collected it and crafted four planks through normal vanilla 2x2
inventory-menu clicks. The learned policy selected COLLECT_LOG, FORWARD, FORWARD
and CRAFT_PLANKS. Server inventory confirmed log 1 followed by log 0/planks 4;
there were zero failed actions or recovery events. Result: **1/1**, four actions,
93 ticks (4.65 game seconds), learning disabled and checkpoint unchanged.
Both game JVMs exited 0. Complete job time was 82.566 seconds.

The verified MP4 is
`recordings/phase9/FlyCraft_Development_Milestone_00001_headless_planks_validation_20261029.mp4`:
20.867 seconds, 625 decoded frames, SHA256
`14f512bfa50476d67252abadb2d0ec01174434f9525c988db16d129df5a0c8fb`.
The recipe-click macro is engineered; selecting that action is learned. This
one prepared fixture does not meet the 30-trial plank target. Headless sticks,
tables and wooden pickaxes remain unimplemented; graphical transactions remain.

### Simulation retention and controlled rehearsal

These experiments generated **zero Minecraft worlds**. A 1,800-episode World2D
retention check compared three checkpoints across six goals, 100 seeds per goal.
Before/after the two new live updates, four simple goals stayed 100/100;
multi-log changed 74 to 73 (paired p=1.0), pickaxe 65 to 61 (p=0.481).
This raises a retention question without establishing forgetting statistically.

A separate episode-matched experiment trained 48 focused find/collect episodes
and 48 mixed-rehearsal episodes from the same checkpoint, followed by 1,800
simulation evaluations on separate development seeds. Frozen/focused/mixed
multi-log scores were 76/69/67; pickaxe 62/66/70, each out of 100. Relevant paired
p-values ranged 0.150-0.585. Focused/mixed training used 1,233/1,724 actions, so
compute and action budgets were not matched. Return variance was 0.436/2.158.
Neither candidate was promoted or evaluated live. Rehearsal is not a demonstrated
fix; task tradeoffs and reward variance need larger controlled experiments.

### Recording availability and resource evidence

All ten scored control episodes, both committed new training episodes and the
plank milestone have fully decoded verified MP4s. Interrupted training has a
playable partial MP4 labeled incomplete. Early RAM-guard and Windows-I/O attempts
have no confirmed complete task video. The old uniform preflight attempt has
partial footage but no scored episode or accepted complete coverage. The initial
terminal-fix RAM failure has a short raw MP4, not usable complete task footage.
Original data and missing/rejected recording declarations are preserved.
Every rerun is a new execution; full RNG-faithful episode replay is absent.

The ten controls took 828.275 worker seconds, with maximum sampled GPU 46 C and
minimum free RAM 2,225.926 MiB. Planks reached 47 C with at least 2,618.137 MiB
free. Early RAM-blocked startup reached 52 C. NVIDIA OpenGL was verified; CPU
temperature was unavailable. Compact heaps/source capture reduced requested
limits but did not eliminate native client memory use. No overnight jobs or
global graphics-driver changes were made. All live workers have finished.

## October 29 continuation: movement precision and recording scope

An audit of the retained failed strict trial found two forward choices taking
the actor past a visible log, followed by repeated policy-selected turns while
the resource was mostly unseen. Acknowledged turn endpoints matched the requested
15 degrees; this trace does not show queued-turn overshoot. Five-tick forward
input moved roughly one block between decision/ack observations. These distances
include drift and observation delay, so they are not pure motor displacements.

Both adapters now accept a fixed `motor.forwardTicks` duration, exposed as
`--forward-ticks` (1-10, compatible default 5). It is frozen in the campaign
profile and identical across conditions. It never varies with target position,
angle or distance. The policy remains responsible for every action and aiming.
The neural architecture, 63-by-10 readout schema and existing checkpoints remain.

The new audit tool matches episode, command and action acknowledgments, rejects
duplicate/unexecuted/cross-episode credit, and reports translation, visible-target
loss, unseen-decision streaks and wrapped turn endpoint error. Endpoint measurements
do not establish per-tick overshoot. See `docs/movement_validation.md`.

Two reused development layouts were tested with the same frozen trained policy,
source, initial relative tree geometry/inventory/orientation, policy RNG seeds,
camera limits and 400-tick deadlines. Absolute spawn locations can translate;
complete world/entity RNG is not matched. All four episodes have verified MP4s,
clean game exits and zero updates. These are fresh executions, not replays.

| Fixed forward input | Success | Actions per trial | Ticks per trial | Mean game seconds, failures included |
| --- | ---: | --- | --- | ---: |
| 5 ticks | 1/2 | 30, 4 | 400, 102 | 12.55 |
| 2 ticks | 2/2 | 7, 7 | 136, 142 | 6.95 |

The formerly failed layout collected a log with two-tick input; median observed
forward displacement changed from about 1.039 to 0.423 blocks and forward target
losses from two to zero in that pair. The other successful layout took longer
with shorter presses (102 versus 142 ticks). Two seeds cannot establish general
improvement or a causal neural benefit. Results and fixture checks are retained
in `experiments/phase9/movement_comparison_20261029.json`.

The full suite then passed **95 tests in 16.334 seconds**, including the new
navigation audit and recording-scope safeguards. The user changed recording
scope to **milestones only**. New CLI campaigns now default to the Phase 9
milestone schedule; explicit milestones may include a final reliability trial.
Routine trials keep real observations, actions, acknowledgments, rewards,
inventory and checkpoint evidence without a spectator or video. Required
milestones still cannot commit without verified complete footage; a recording
failure cannot be relabeled as intentionally event-only. Legacy campaigns keep
their previous all-episode requirement. Headless status no longer calls event-log
readiness an active video recording.

The first 30-trial plan (`dev_log30_stride2_20261029`) had two already-launched
trials when recording scope changed: one failure (400 ticks, 27 actions) and
one success (103 ticks, four actions). Both recordings and results remain.
The source-freeze guard prevented the next launch after this configuration
change. That superseded plan is not pooled into the replacement evaluation.
The replacement (`dev_log30_milestones_20261029`) fixes 30 new seeds before
execution, learning off, two-tick input, 400-tick deadlines, and recordings only
at trials 1, 10, 25 and 30. No actor, policy or runtime-parameter tuning occurs
during this run. One result-validator repair was needed, as described below.

Trial 11 exposed an early-result ordering bug: the controller had observed a
real inventory log and written success before the server's terminal snapshot
was attached to its result row. The server independently scored success and
the raw bridge log contained the exact terminal inventory and acknowledgment.
The coordinator rejected the incomplete row and stopped before trial 12.

The validator now accepts an otherwise incomplete **evaluation** result only
when the retained bridge log has a matching inactive episode boundary, valid
server tick, successful same-episode terminal acknowledgment, and inventory
agreeing with the server score. Missing, mismatched or unacknowledged proof is
rejected. Training still requires its ordinary sealed terminal result. No
success flag is used to invent an inventory snapshot.

Trial 11 was revalidated from its original files without rerunning Minecraft.
Its original rejection and state remain archived. The development evaluation
continued on the same 30 seeds after an explicit validation-only amendment;
only `autonomy/experiment.py` differed in the source manifest. Previous config,
source manifest, state and the amendment reason are retained. Actor, controller,
runner, policy checkpoint, motor settings, deadlines and seed plan stayed fixed.
This is an audited mixed-validation-version development run, not a claim of
unchanged complete source or an untouched final benchmark. The full suite after
this repair passed **97 tests in 20.020 seconds**.

### Completed strict 30-seed one-log evaluation

The fixed plan completed **27/30 (90%)**, meeting the 80% point target in this
controlled setting. The 95% Wilson interval is **74.4%-96.5%**; the lower bound
does not establish population success of at least 80% at 95% confidence.
All 30 seeds were selected before this evaluation, distinct from previously
generated development seeds. They produced only **seven distinct relative
fixture snapshots** because block placement is quantized near prepared trees.
This tests repeated collection near a tree, not natural forest exploration.

| Measurement | Actual result |
| --- | --- |
| Inventory-confirmed one-log success | 27/30 |
| Distinct seeds / generated world instances | 30 / 30 |
| Mean acknowledged actions, all trials | 11.83 |
| Mean acknowledged actions, successes | 9.89 |
| Mean game time, failures included | 9.845 seconds |
| Worker wall time, including startup/recording | 1,585.294 seconds |
| Required recorded milestones | 1, 10, 25, 30; all verified |
| Intentional event-only trials | 26 |
| Maximum sampled GPU / minimum available RAM | 49 C / 2,107.070 MiB |
| Policy/checkpoint updates | 0; checkpoint hash unchanged |

Failures were trials 9, 16 and 17, all bounded at 400 ticks. Trial 9 broke a
log without collecting it; its trace includes three successful-input forward
acknowledgments with near-zero displacement, pointing to insufficient blocked-
movement feedback/recovery. Trials 16 and 17 broke no confirmed block. A turn
or successful mining acknowledgment alone never counted as goal completion.
One successful trial reached its inventory goal at the deadline; scoring uses
the frozen boundary inventory, not later item pickup.

All terminal deliveries were acknowledged and game servers exited cleanly.
Milestone clients exited cleanly and their complete MP4s passed decode and
checksum checks. No milestone MP4 is missing in this evaluation. Routine trials
were intentionally unrecorded under the user's revised preference. The original
trial 11 JSON remains intact; its terminal inventory is independently verified
from the acknowledged raw boundary, with the original rejection archived.
Eleven trials used the original validator source and 19 the audited repaired
validator; the actor/controller/runner and policy were unchanged throughout.

Full per-trial outcomes, source provenance, intervals, failure categories and
navigation audits are in `experiments/phase9/log30_validation_20261029.json`.
CSV and an actual-outcome figure are under
`recordings/phase9/youtube/figures/log30_validation_20261029/`. This new result
is separate from assisted Phase 8 results and the tiny matched neural-control
comparison. It is not evidence that the neural features caused success or that
the three earlier real training updates improved generalization.

## Plank coordinator extension

After preserving and pushing the complete one-log result, the coordinator was
extended to select either `one_log` or `planks` explicitly. Each goal has its
own actual inventory predicate: log >= 1 or planks >= 4. Full terminal inventory
agreement is checked; a collected log cannot be mislabeled as plank success.
The same goal is forwarded to the Minecraft harness and learned controller.
This is operator-selected evaluation, not automatic curriculum promotion.

The full suite passed **98 tests in 15.016 seconds**, including rejection of
a false plank success with only a log. The actor, neural architecture, learned
readout and vanilla recipe implementation were unchanged. A separate 30-seed
plan was fixed before any plank trial, with fresh seeds, empty starting
inventory, learning disabled, two-tick forward input, a 400-tick deadline and
recordings only at trials 1,10,25,30. Its source is frozen separately from the
earlier one-log evaluation. The recipe click macro remains engineered and the
policy remains responsible for selecting it.

### Completed strict 30-seed plank evaluation

Result: **21/30 (70%)**, meeting the requested plank point target. Wilson 95%
interval is **52.1%-83.3%**; this does not establish population success of at
least 70% at 95% confidence. Thirty distinct fresh seeds produced nine relative
prepared-tree fixture snapshots. All 30 initial inventories were checked empty.

| Measurement | Actual result |
| --- | --- |
| Inventory-confirmed four-plank success | 21/30 |
| Trials with log pickup observed | 21 |
| Acknowledged crafts / successful craft acknowledgments | 21 / 21 |
| Mean actions, all trials / successes | 17.33 / 11.86 |
| Mean game time, failures included | 12.398 seconds |
| Total worker wall time | 1,563.244 seconds |
| Maximum sampled GPU / minimum available RAM | 46 C / 2,613.926 MiB |
| Required milestone MP4s | 1,10,25,30; all verified |
| Intentional event-only trials | 26 |
| Policy updates / validation-source amendments | 0 / 0 |

Failures were trials 1,7,8,9,13,18,19,24,26: six mined without pickup and three
had no confirmed block break. All ended at the 400-tick deadline. Every trial
with an observed log pickup went on to confirm four planks; there were no
failed craft acknowledgments in this set. This is a conditional observation
under an inventory-masked recipe macro, not unrestricted crafting accuracy.
Both server and controller inventory agreed, terminal deliveries were
acknowledged, and all game processes exited cleanly. The source and checkpoint
hashes remained fixed throughout all 30 trials.

The final recorded trial collected a log and crafted four planks in four actions
and 96 ticks (4.8 game seconds). Milestone 1 instead shows a genuine failed
collection attempt; its complete recording is kept and not presented as success.
There are no missing required milestone MP4s. The 26 unrecorded routine trials
are intentional under the user's preference. Full outcomes, conditional craft
counts, empty-inventory checks, source provenance and navigation audits are in
`experiments/phase9/planks30_validation_20261029.json`; figures/CSV are under
`recordings/phase9/youtube/figures/planks30_validation_20261029/`.

The log and plank sets used different seeds; their percentages do not establish
a causal effect of goal length. Neither this evaluation nor the 27/30 result
establishes a neural benefit or a learning improvement. All 60 trials evaluated
the same preserved checkpoint with learning disabled. There remain three prior
committed Phase 9 real training updates, and zero official experiment worlds.

The original and repaired validator source modules for the one-log amendment
are retained alongside their manifests. The original bytes were reconstructed
from the isolated patch and independently matched to the pre-existing SHA256;
the verification record states that provenance. No game logs or actions changed.
The raw connectome SHA256 was reverified unchanged, and all 30 one-log initial
inventories were separately checked empty in a supplementary audit.

## Remaining work and recommendations

A subsequent Phase 7.5 increment added own-pose blocked-movement feedback in
both adapters. Its six-episode matched development pilot scored 1/3 in both
modes, with two correctly reported blocked moves but no demonstrated success
gain. All 100 automated tests pass. These are separate from the earlier 30-trial
results and do not establish new learning. See `PHASE_7_5_REPORT.md`.

Broaden strict collection/crafting to natural terrain and powered matched
policy controls before expanding claims. Validate interrupted mining,
connection-loss recovery and checkpoint restoration in repeated real sessions.
The serial transactional coordinator, separate seed sets, dashboard and small
five-condition comparison are implemented; parallel throughput and long-run
memory/recovery validation remain absent. A complete faithful replay mechanism
is still absent; operator
fixture snapshots are not enough to reconstruct full game RNG state.

The 10,000-world experiment, untouched 100-world final benchmark and official
milestones have not begun. No overnight training was launched. Obtain explicit
authorization only after the development pilot and frozen configuration are
reviewable. Continue to respect the 60% weekly limit and stop starting new
development around 55%; report only actual usage telemetry.

The strict one-log and plank point targets are met in controlled fixtures.
Three-log/pickaxe gates and repeated integration/recovery stress tests remain incomplete.
Do not declare Phase 7.5, Phase 8 or the Phase 9 experiment complete. Continue
with powered strict evaluation and retention-controlled training before scaling.
Later work should test policy-selected pitch/finer camera actions and natural
terrain, with the same assistance disclosures and inventory-based scoring.

See `docs/phase9_architecture.md`, `docs/phase9_training.md`,
`docs/phase9_recording.md` and `docs/phase9_evaluation.md` for the current
implementation boundaries.

## November 27: verified failed gate and bounded continuation

The completed terrain retention-repair evaluation scored 19/30 trained,
12/30 frozen transfer, 0/30 uniform, 0/30 no-neural and 13/30 shuffled-neural.
Wood retention scored 26/30 one log, 27/30 three logs, 21/30 planks and 25/30
wooden pickaxe. All wood thresholds passed; terrain missed its unchanged
24/30 threshold, so progression stopped. There were 434 authorized training
worlds including the 338-world foundation, and 540 separate stage evaluation
episodes. The previous 25/30 primary score used a different seed catalog;
the frozen-control score also fell, so the raw difference is not a direct
measure of forgetting.

On the user's "carry on" instruction, the failed gate and all evidence were
archived. A predeclared 96-world joint terrain/wood rehearsal round was
installed, followed by a locked candidate and 270 fresh evaluation episodes.
The original graph, actor, reward, policy interface, training-seed order,
thresholds, original final evaluation and live resource guards are preserved.
The campaign implementation's 183-test baseline passes.
[Failure diagnosis, archived gate and frozen continuation protocol](experiments/phase9/recovery27_operations/README.md)

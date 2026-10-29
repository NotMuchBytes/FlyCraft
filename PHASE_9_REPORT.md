# FlyCraft Phase 9 development report

Updated: 2026-10-29. Status: **in progress; not a completed 10,000-world experiment**.
The later strict one-log evaluation scored 27/30 in controlled fixtures. Phase
8's longer-goal targets and broader Phase 7.5 recovery/integration validation
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

## Remaining work and recommendations

Complete independent multi-seed strict one-log validation before expanding
claims. Expand the one successful headless plank check, interrupted mining,
connection-loss recovery and checkpoint restoration to repeated real sessions.
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

The strict one-log point target is now met in controlled fixtures. Longer-goal
Phase 8 gates and repeated integration/recovery stress tests remain incomplete.
Do not declare Phase 7.5, Phase 8 or the Phase 9 experiment complete. Continue
with powered strict evaluation and retention-controlled training before scaling.
Later work should test policy-selected pitch/finer camera actions and natural
terrain, with the same assistance disclosures and inventory-based scoring.

See `docs/phase9_architecture.md`, `docs/phase9_training.md`,
`docs/phase9_recording.md` and `docs/phase9_evaluation.md` for the current
implementation boundaries.

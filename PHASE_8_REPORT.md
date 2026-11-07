# FlyCraft — Phase 8 progress report

November 6 reliability update: a recorded strict one-log smoke check and
interrupted-mining recovery succeeded. A recorded bridge process-tree stall
exposed an unresolved stale-command rejection/acknowledgment defect and failed
collection. These small development checks reuse one fixture seed; they are
not held-out benchmarks or learning gains. Phase 8 remains incomplete. See
[the Phase 7.5 evidence](docs/phase75_reliability_20261106.md).

Updated: 2026-10-28 (Asia/Amman). **Phase 8 is not complete.**
The one-log target has been demonstrated in controlled real Minecraft fixtures:
29/30 inventory-confirmed successes. Longer-goal evaluation remains underway.
This report will be updated as those bounded evaluation batches finish.

## 1. Implemented features

The Phase 7 baseline was established before changes: 45 automated tests passed.
The original 139,255-neuron graph, sparse dynamics and all earlier checkpoints
are retained. The 63-feature, ten-action learned readout is reused.

The Fabric client now observes visible logs and dropped resources, its own
server-synchronized inventory, visible crafting tables, placement affordances,
and action acknowledgments. Survival mining waits for an actual server block
update. Resource collection requires actual inventory gain. Crafting sends
normal container clicks for planks, sticks, tables and wooden pickaxes, and
waits for server inventory confirmation. Each transaction has a deadline and
an identity; missing acknowledgments do not trigger duplicate commands.

The server observation component echoes only the player's own inventory and
directly interacted blocks. This is necessary because vanilla prediction can
suppress matching slot packets. It does not reveal hidden blocks or choose
actions. See [the complete observation contract](docs/phase8_observation_contract.md).

The live controller supports one-log, three-log, plank, stick, table and pickaxe
goals. The planner supplies dependencies, memory and bounded recovery; the
learned policy samples actions. Recipe slot clicks, aiming at an observed hit,
affordance masks and dependency planning are engineered assistance. They are
not learned motor control or evidence of unscripted natural-world reasoning.
That description of aiming applies to the historical `legacy` interface.
New runs default to bounded camera movement and crosshair-only interactions,
without target aiming or tracking. The original ten actions contain no pitch
action, so strict interaction capability is narrower. Results from the two
interfaces are kept separate.

## 2. Real Minecraft evidence so far

These are actual Minecraft 26.2/Fabric survival transactions in disposable,
controlled flat-world tree fixtures. They are not natural forest-search tests.
Seeds, fixtures and outcomes are logged separately from policy observations.

| Run | Purpose | Actual server result |
|---|---|---|
| `pilot01` | Bootstrap diagnostic | Client initialization failure; no valid trial |
| `pilot02` | One-log development pilot | 1/1 success |
| `obs_one_log_01` | Recorded repeat of the development layout | 1/1 success; four sampled actions, six game seconds |
| `live_train01` | Six live one-log learning episodes | 6/6 success; training data, excluded from held-out scores |
| `craft_pilot01` | Crafting diagnostic before inventory-echo fix | Server planks 1/1; controller inventory inconsistency; three-log and pickaxe 0/1 each |
| `recorded_craft02` | Recorded pilot after inventory-echo fix | Planks 1/1 with controller/server agreement; three-log 0/1; pickaxe 0/1 |
| `heldout_log_a` | First matched held-out attempt | Incomplete after recording confirmation loss during a system stall; retained as partial evidence |

The crafting pilot successfully mined three blocks but spent resources on
inappropriate crafts during the three-log goal. The pickaxe pilot reached
planks and sticks but did not finish within its 30-second trial limit. These
are policy/planning failures, not successful longer goals.

All new live runs now require OBS recording confirmation before trials start.
The separate OBS collection captures only Minecraft; desktop/microphone audio
sources are absent. The client opens without requesting keyboard focus. A
local heartbeat controls recording without desktop input or a remote-control
server. Bounded runs stop if recording confirmation disappears. Original
recordings remain local, and each run records its video path.

## 3. Learning and evaluation

Six live one-log episodes updated the existing readout using the original
REINFORCE pipeline. The final candidate is
`checkpoints/phase8/live_train01/trial_0005.npz`; the frozen reference remains
`checkpoints/phase7/curriculum_v3_seed29.npz`. No original checkpoint is
overwritten. Evaluation weights are frozen.

A separate exploratory simulation experiment compared three 300-episode
training conditions from the same Phase 7 checkpoint. Each was evaluated on
40 development episodes per goal:

| Training condition | Simulated pickaxe success | Mean training return variance |
|---|---:|---:|
| Focused pickaxe training, global baseline | 67.5% | 5.676 |
| Earlier-goal rehearsal, global baseline | 82.5% | 4.294 |
| Rehearsal and goal-specific baseline | 85.0% | 3.986 |

These are single-training-seed development results. They suggest a useful
rehearsal/variance experiment, not a confirmed improvement in live Minecraft.
The simulated candidates are retained separately and are not substituted into
the ongoing live comparison. Raw aggregate metrics are preserved in
`experiments/phase8/learning_experiment.json`.

The live protocol compares the six-episode-trained candidate, frozen Phase 7
transfer, uniform action sampling using the same affordances, and neural
features removed. Conditions see matched layouts. The analyzer uses actual
server inventory, reports action counts and 95% Wilson intervals, and flags
incomplete batches. Longer-goal comparisons remain pending.

The primary held-out comparison uses `eval_log_03`, `eval_log_05` and
`eval_log_06`: 30 reset layouts per condition across world seeds 83002,
8675310 and 17000000, with 15 game seconds per trial. Every success requires
an actual log in the server inventory:

| Condition | Inventory-confirmed success | 95% Wilson interval | Mean successful actions |
|---|---:|---:|---:|
| Trained candidate | **29/30 (96.7%)** | 83.3–99.4% | 3.38 |
| Frozen Phase 7 transfer | 27/30 (90.0%) | 74.4–96.5% | 3.78 |
| Uniform actions, same affordances | 19/30 (63.3%) | 45.5–78.1% | 4.79 |
| Neural features removed | 25/30 (83.3%) | 66.4–92.7% | 3.40 |

Mean successful game time was 6.90 seconds (trained), 6.61 (frozen), 7.79
(uniform) and 5.94 (no-neural). These are conditional on success, not an
unconditional speed comparison. Exact paired McNemar p-values versus trained
are 0.625 (frozen), 0.00195 (uniform) and 0.21875 (no-neural), uncorrected
exploratory comparisons. The learned readout performs better than uniform in
these fixtures; these data do not establish that six live updates improved
the frozen transfer or that neural features provide a reliable causal benefit.

Layout dependence is substantial: uniform succeeded 5/10, 10/10 and 4/10
across the batches. These are 30 reset episodes, not 30 natural-world seeds;
each world uses ten nearby procedural layouts and the policy RNG seed is held
fixed for matching. Wilson intervals are descriptive and do not account for
world/layout clustering or establish natural-world generalization. Five
controller success reports arrived after the server deadline and remain
failures here. Every disagreement is recorded in the summary. Full results:
`experiments/phase8/primary_one_log.json`.

A six-trial longer-goal development comparison at a 40-second deadline tested
the simulator rehearsal/goal-baseline candidate against the six-live-log
candidate. Three-log collection was 1/1 versus 0/1, planks 1/1 versus 1/1,
and full wooden-pickaxe goals 0/1 versus 0/1. These labels are different policy
candidates from the primary frozen Phase 7 comparison; they are not pooled.
Three subsequent prepared-inventory `pickaxe_transaction` diagnostics all
failed after wasteful extra stick crafting. A placement guard now rejects
positions intersecting the player's body. These pilots neither meet a
30-trial gate nor validate a complete pickaxe crafting loop.

## 4. Comparison with Phase 7 and neural contribution

Phase 7's real bridge supported navigation only. Phase 8 has demonstrated
real acknowledged log pickup and plank crafting in development pilots. Phase
7's held-out simulated pickaxe result remains 160/300 (53.33%); that result is
not comparable to a live controlled pilot.

No positive causal neural-contribution claim is established by the 30-trial
comparison (paired no-neural p=0.21875). The full
live controller computes the existing 18-step neural sensory window. The
`no_neural` condition retains the bias and goal/inventory/context features
while removing the three neural readout values. This does not remove the
engineered planner or semantic observations. Successful learned action
selection must not be attributed wholesale to the sparse neural model.

## 5. Reliability checks

The latest full 65-test suite passed in 12.083 seconds. Phase 8 tests cover server
inventory consistency, block acknowledgment versus pickup, failed mining and
recovery, missing acknowledgment timeout, episode/connection interruption,
crafting failure, pending-transaction checkpoint restoration without replay,
neural-feature removal and completed-checkpoint result isolation. The Fabric
main/client sources compile successfully.

A direct regression reran 1,800 simulated episodes: the same 100 worlds for
each of six goals and each of three preserved Phase 7 checkpoints. Successes,
action counts, failed-action counts and recovery counts exactly matched the
earlier baselines. `experiments/phase8/phase7_regression.json` records this.
The source graph SHA-256 remains
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.

Recording setup also exposed a source-resize crop, a Lua alignment-constant
compatibility issue and a Windows command-file sharing violation. Native OBS
bounding-box fitting now preserves the whole frame. Command replacement
retries transient Windows sharing violations for at most one second, and a
failed recorder stop cannot skip owned-process cleanup. Four added tests cover
these control failure paths, and 1,000 actual background command writes
succeeded against the running Lua reader. Setup failures started no trials;
partial development batches remain separate from the primary evaluation.

Unit protocol tests do not replace live mining-interruption, network-loss or
natural-world reliability evaluations. Those live stress tests remain work.
The recording interruption exposed a real fail-closed path. Its metadata's
original `wall_budget` label predates the supervisor error-label fix; the
launcher traceback identifies recording-confirmation loss as the cause.

The recorder also previously treated a temporarily unreadable command file as
an expired heartbeat, and retained ownership after its recording stopped.
The updated handshake retains the last complete command through transient
read failures, validates complete frames without rename/delete races, and
releases ownership after stop. A headless test executes the actual Lua script
using OBS's existing runtime and injects partial/missing commands, asynchronous
startup, watchdog expiry, old tokens and external recordings. Exact future
confirmation-loss snapshots and recording state transitions are logged.

The shared camera now has configurable speed/acceleration/deceleration limits,
bounded per-tick movement, relative versus continuous semantics, stale/duplicate
rejection, safe replacement/cancellation, pitch limits, robust yaw wrap and
requested/body/rendered movement instrumentation. The Java core passes over
300 kinematic cases. Matched live scripted probes passed 11/11 applicable
instant-reference cases and 12/12 bounded cases. The largest measured static
yaw rate fell from 4385.55 to 115.73 degrees/second, while mean settling over
nine static cases increased from 0.097 to 0.675 seconds. Recorded endpoint
overshoot was zero in both conditions; these probes do not demonstrate that
smoothing alone solves policy corrections.

An initial matched strict policy comparison on three layouts scored instant
3/3 versus bounded 2/3 within a 20-second deadline. Both acknowledged all three
issued mining commands, but bounded collected one item after the deadline.
The successful-only mean game times were 10.983 versus 5.175 seconds and cannot
be interpreted as an overall speed improvement. These are development pilots,
not a new 30-trial strict-mode evaluation. Details and limitations are in
`docs/camera_controller.md`.

The Java application crash was traced through Windows Event 1000 to AMD's
`atio6axx.dll`, even during two NVIDIA Vulkan-rendered shutdowns. Setting a
per-application Windows high-performance preference for FlyCraft's dedicated
Java runtime, then using NVIDIA OpenGL, produced two clean client/server exits
across the six policy trials, with maximum sampled GPU temperature 48 C.
This is bounded verification, not proof of universal driver reliability.
No drivers or global GPU preferences were changed. The runner verifies the
actual NVIDIA device before trials, reserves available RAM, and tolerates
inaccessible Windows crash reporters during owned-process cleanup.
A separate disconnected-client lifecycle polling bug was fixed. See
`docs/windows_gpu.md` and the retained event/run evidence.

## 6. Limitations and completion gates

The one-log target is met at 29/30 (96.7%) in the documented assisted fixtures.
The three-log 70%, planks 70% and pickaxe 50% targets remain unestablished.
Development pilots reuse layouts and cannot count toward those targets.
Broader held-out evidence remains pending.
The fixtures begin near small trees, use semantic rays and recipe macros, and
do not test exploration, arbitrary terrain, hostile environments or pixel-only
control. Longer-goal policy errors and curriculum transfer remain substantial.
GPU samples during completed pilots stayed at or below 53 C; CPU temperature
was unavailable. Runs are bounded and supervised; no overnight training is
performed. Weekly and five-hour usage are checked through actual account
telemetry.

## 7. Phase 9 recommendations

An additional bounded Phase 9 development increment now includes a headless
survival actor, terminal inventory acknowledgment, memory reductions and a
verified recorded one-log redo. This does not satisfy Phase 8's remaining
longer-goal or unseen-environment targets. See `PHASE_9_REPORT.md`; all historical
Phase 8 results and their assistance definitions remain preserved below.

Complete matched live evaluations before expanding scope. Improve recovery
from resource-consuming off-goal crafts, then test rehearsal and goal-specific
reward baselines across multiple training seeds. Separate transaction
reliability from policy success, test interrupted actions and reconnects in
real game sessions, and progressively replace nearby flat fixtures with
unseen terrain and natural tree search. Retain all negative results.

## October 29 development follow-up

The preserved headless implementation now has a verified empty-inventory
log-to-four-planks trial: four policy-selected actions, one actual block broken,
inventory log pickup followed by planks=4, 93 ticks, clean game exits and a
fully decoded MP4. Vanilla inventory clicks form an engineered recipe macro;
camera actions remain policy-selected with crosshair-only mining. This 1/1
pilot does not meet the 30-trial plank target. Headless sticks, table and
pickaxe transactions remain absent; existing graphical transactions are kept.

A strict, matched two-seed comparison scored trained 1/2, frozen original
Phase 7 2/2, uniform 1/2, no-neural 0/2 and shuffled 1/2. Every scored episode
has verified footage, but the sample establishes no learning or neural benefit.
Two new real readout updates committed through the bounded serial coordinator;
an interrupted candidate was retained without promotion. All 90 automated tests
pass. Full results, retention experiments and recording gaps are documented in
`PHASE_9_REPORT.md`.

Historical assisted 29/30 results remain separate. At that point strict one-log
reliability and the three-log/plank/pickaxe gates remained unmet.

## Later October 29: strict one-log point target met

A fixed evaluation on 30 new development seeds scored **27/30 (90%)**, meeting
the one-log point target with two-tick forward presses and bounded 15-degree
turns. The 95% Wilson interval is 74.4%-96.5%. These are prepared near-tree flat
fixtures with seven distinct relative snapshots; natural tree search remains
untested. All scores require actual inventory, boundary acknowledgment and clean
server exits. The checkpoint did not change; no learning gain is established.

One failure mined without collecting; two broke no block. Mean actions were
11.83 across all trials and mean game time 9.845 seconds including failures.
Milestones 1,10,25,30 have verified MP4s; 26 routine trials intentionally kept
logs without video. A validator-only amendment recovered one early result's
missing terminal field from its original acknowledged boundary, without replay
or actor/controller changes. Its original rejection and provenance are kept.
The final full suite passed 97 tests. See `PHASE_9_REPORT.md` for all results.

At this stage the three-log, plank and pickaxe 30-trial gates remained unmet.

## Later October 29: repeated real plank crafting

A separately fixed evaluation on 30 fresh seeds scored **21/30 (70%)** from
empty inventory to at least four planks. This meets the plank point target in
prepared near-tree flat fixtures; Wilson 95% interval is 52.1%-83.3%. Seeds
produced nine relative fixture snapshots, not 30 unique terrain types.

The coordinator now validates the selected goal's actual inventory predicate;
one log cannot count as plank success. It checks full terminal inventory
agreement and forwards the same goal to Minecraft and the learned controller.
All 98 automated tests passed in 15.016 seconds. The recipe macro, neural graph
and readout were preserved; no policy was updated during evaluation.

All 21 observed log pickups led to four planks with 21 successful craft
acknowledgments. Six failed trials mined without collecting and three never
broke a block. Mean actions were 17.33 across all trials, mean game time 12.398
seconds including failures. All game processes exited cleanly and terminal
delivery was acknowledged. Milestones 1,10,25,30 have verified MP4s, including
the genuine failure at milestone 1; 26 routine trials intentionally kept logs.

| Current strict controlled-fixture goal | Actual result | Point target |
| --- | --- | --- |
| One log | 27/30 (90%) | Met |
| Four planks | 21/30 (70%) | Met |
| Three logs | No completed 30-trial validation | Unmet |
| Wooden pickaxe | No completed 30-trial validation | Unmet |

The two evaluated goals used different seeds, so their rates do not isolate a
goal-length effect. Neural contribution and learning improvement remain
unestablished. Blocked movement/drop pickup, the missing policy pitch actions,
more complex headless crafting and natural terrain remain limitations. Full
provenance is in `PHASE_9_REPORT.md`. Phase 8 is not declared complete.

## November 7 reliability and control checks

Minecraft 26.2 trials verified recovery from a lost bridge reply and from
an in-episode Python process restart while mining was pending. The recorded
restart finished with four server-confirmed planks in six actions. These
deliberate faults are separate from the ordinary plank trials.
[Live checkpoint restoration](docs/phase75_checkpoint_restart_20261107.md)

A follow-up matched comparison across three additional controlled fixture
seeds gave 2/3 for the trained checkpoint, 3/3 each for frozen and uniform,
1/3 for shuffled features, and 0/3 with neural activity removed. This small
sample does not demonstrate a learned advantage. The three-log and wooden
pickaxe validation targets remain open.
[Full results and recording status](docs/phase75_matched_controls_20261107.md)

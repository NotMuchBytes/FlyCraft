# FlyCraft — Phase 8 report

November 20, 2026. The pitch-enabled candidate completed 30 live trials
per goal, scoring **26/30 one-log, 18/30 three-log, 27/30 four-plank and
12/30 from-empty wooden pickaxe**. The one-log and plank point targets
were met. Three-log and pickaxe reliability remain below target.
[Completed pitch evaluation](#november-20-completed-pitch-evaluation)

November 6 reliability update: a recorded strict one-log smoke check and
interrupted-mining recovery succeeded. A recorded bridge process-tree stall
exposed an unresolved stale-command rejection/acknowledgment defect and failed
collection. These small development checks reuse one fixture seed; they are
not held-out benchmarks or learning gains. Phase 8 remains incomplete. See
[the Phase 7.5 evidence](docs/phase75_reliability_20261106.md).

November 12, 2026. The controlled Minecraft evaluations are complete. The
crosshair-only interface met the one-log and four-plank targets and missed
the three-log and wooden-pickaxe targets. The earlier assisted one-log
comparison has its own results. See the final scorecard below.

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

Milestone trials require OBS recording confirmation before gameplay starts.
The separate OBS collection captures only Minecraft. A local heartbeat
controls recording without desktop input or a remote-control server.
Recording runs stop if confirmation disappears. Original MP4s remain local
and the run metadata records their paths. Routine scored episodes use
structured logs.

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

| November 6 strict controlled-fixture goal | Actual result | Point target |
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

The headless runner now accepts the three-log goal and has an optional
three-tree fixture for the yaw-only policy. A live probe caught the policy
spending its first log on planks. The three-log goal now masks recipe
and placement actions across all policy conditions.

The mask kept one, one, and two logs across three layout repeats. Giving
visible standing logs at the current pitch priority yielded two logs
on all three layouts. Restricting observations to the current pitch
yielded one, two, and two logs, so the priority variant was retained.
Each variant scored 0/3 three-log completions in this development set.
The original checkpoint was frozen and all scores came from Minecraft
inventory. Both recorded sensor variants have verified OBS footage.
The retained build passed 112 automated tests and Fabric assembly.
[Three-log trials and recording metadata](docs/phase8_three_logs_20261107.md)

## November 8 headless crafting and longer goals

The headless adapter now executes vanilla inventory recipes for planks,
sticks and crafting tables. It places a table through the actual crosshair,
opens the workbench through normal interaction, and verifies the recipe
and inventory for wooden pickaxes. A prepared recorded transaction placed
and used its table in four actions and 31 ticks.

The recorded full pickaxe chain began with empty inventory and finished in
103 actions and 1,396 ticks. It gathered three logs, crafted the ingredients
and table, and used a stone support face supplied by the controlled fixture.
The server confirmed one wooden pickaxe in inventory. The recorded trial
demonstrates the full chain in that fixture. The earlier trial reached the
table and failed before placement. Both are development episodes.

A separate three-log pilot reached the goal in 2/3 development trials with
a 1,500-tick limit. The new fixed held-out plan uses 30 layout seeds across
six worlds and scores both long goals. The historical 27/30 one-log and
21/30 plank scores remain separate.
[Crafting evidence and held-out plan](docs/phase8_crafting_20261108.md)

The first two held-out worlds produced **7/10 three-log successes and
0/10 pickaxe successes**. Three-log failures ended with two logs.
Six pickaxe failures reached a crafted table and timed out before
placement. A separate recorded three-log repeat succeeded in 57 actions
and 887 ticks. Its 60.567-second MP4 passed full decoding.

**Phase 8 remains open.** The two longer goals have controlled live
demonstrations. The 30-trial gates still need 20 trials per goal, and the
held-out pickaxe sample has yet to reproduce the development success.
The plan and data were preserved at the 55% weekly stop point for new development.
All 113 automated tests passed and the Fabric build succeeded.
[Held-out results and recordings](docs/phase8_crafting_20261108.md)

The frozen evaluation later resumed on the third world. The RAM guard
interrupted that block after five scores, and a fresh run completed its
interrupted pickaxe layout. The cumulative held-out results are **8/13
for three logs and 0/13 for pickaxes**. Seventeen planned trials per goal
remain. The retry's original and interrupted records are both preserved.

## November 12 final controlled-fixture scorecard

The remaining two layout pairs in world 3 produced two three-log successes
and the first held-out from-empty pickaxe success. Minecraft confirmed
the pickaxe in 72 actions and 1,043 ticks, with acknowledged terminal
delivery and matching controller inventory.

| Goal | Confirmed successes | Point target | Descriptive 95% Wilson interval |
| --- | ---: | ---: | ---: |
| One log | 27/30 (90.0%) | 80%, met | 74.4%–96.5% |
| Three logs | 20/30 (66.7%) | 70%, missed | 48.8%–80.8% |
| Four planks | 21/30 (70.0%) | 70%, met | 52.1%–83.3% |
| Wooden pickaxe from empty inventory | 3/30 (10.0%) | 50%, missed | 3.5%–25.6% |

The long goals used the same 30 layout seeds across six world seeds, with the
checkpoint frozen and a 1,500-game-tick limit. All 60 results have acknowledged
terminal delivery and matching server and controller outcomes. The server's
inventory matched the controller's terminal record in 58 episodes and the
acknowledged bridge packet in the remaining two. The median
was 86 actions and 1,193 ticks for three logs, and 110 actions and 1,500 ticks
for pickaxes, including failures. One-log and four-plank scores come from
earlier seed sets. The intervals describe layout outcomes without adjusting
for shared worlds.

Seven of the ten three-log failures broke three blocks but collected fewer
than three logs. The other three broke two blocks. Eighteen of the 27 pickaxe
failures reached a crafted table. Four of those eighteen saw a legal
placement affordance, and the only selected placement produced no confirmed
block change. The other failures stopped after sticks (seven) or planks
(two). The three successful pickaxe episodes used the actual workbench and
finished in 72–102 actions on three world seeds.

The learned readout selected actions from engineered affordances, while the
planner supplied recipe dependencies and bounded recovery. The long-goal
sample evaluates the combined system with one frozen checkpoint. The earlier
matched controls did not establish a causal benefit for the neural features
or for the live updates. All 113 automated tests passed again, including the
Phase 7 regression suite. Natural-terrain performance and full server restart
recovery remain unverified.

Two pickaxe repeats produced fully decoded Minecraft-only OBS recordings.
Both timed out, including the fresh repeat of the first successful layout.
The exact scored successes have action and inventory logs only. The earlier
verified development MP4 shows a successful from-empty pickaxe.
[Per-episode results](experiments/phase9/phase8_completion_bench_20261108/results.json)
[World breakdown and recordings](docs/phase8_crafting_20261108.md)

Phase 8 reliability remains open for the two longer goals. For Phase 9,
prioritize pickup recovery after confirmed block breaks and add policy-selected
pitch actions while retaining the existing checkpoints. Test approach,
placement, and crafting separately on development layouts before repeating
matched policy controls on fresh seeds.

## Experimental live pitch control

The frozen benchmark traces show that all seven three-log failures with
three confirmed breaks observed a dropped log after the final break. The
nearest observed drop ranged from 1.66 to 3.71 blocks from the actor's
eyes. A pickup remained unconfirmed in every case. This leaves a specific
navigation problem after mining, alongside the low frequency of legal
table-placement views.

The opt-in headless readout adds `LOOK_UP` and `LOOK_DOWN` and three inputs
for the observed pitch error and the two new previous-action indicators.
Checkpoint transfer copies the original 63-by-10 weights into the
66-by-12 readout and initializes the remaining weights to zero. Existing
checkpoints and the default ten-action interface are preserved. The policy
samples both new actions, and Fabric executes each as a fixed relative
turn through the existing controller. Mining and table placement continue
to require the actual crosshair and a server-confirmed result.
[Observation and action contract](docs/phase8_observation_contract.md)

The matched development pilot used three fresh layouts in one controlled
Minecraft world, a shared checkpoint, 15-degree turns, two-tick forward
input and a 1,500-tick deadline. Both configurations evaluated fixed
weights. All 12 scores have acknowledged terminal inventory.

| Goal | Yaw only | Pitch enabled | Median actions, yaw / pitch | Median game ticks, yaw / pitch |
| --- | ---: | ---: | ---: | ---: |
| Three logs | 1/3 | 1/3 | 107 / 105 | 1,500 / 1,500 |
| Wooden pickaxe from empty inventory | 0/3 | 2/3 | 117 / 55 | 1,500 / 798 |

The pitch-enabled pickaxes finished in 54 and 55 actions at 784 and 798
ticks. Each mined three blocks, reached a legal table-placement view,
placed a table and crafted through the workbench. The yaw-only policy saw
a placement affordance in one trial and did not select it. The pitch-enabled
policy's failed pickaxe trial mined one block. The two three-log conditions
succeeded on different layouts.

Minecraft acknowledged 175 policy-selected pitch actions across six
episodes. All settled, with a median of ten ticks, a peak sampled pitch
speed of 88.34 degrees per second, and zero recorded endpoint error or
overshoot. The sample compares the whole optional interface, including the
expanded surface rays. It does not isolate the effect of each change. The
results leave the original 30-trial gates in place. All 115 automated tests
passed and the Fabric live build succeeded.
[Yaw reference](experiments/phase9/p8_pitch_dev_20261112_yaw/run.json)
[Pitch-enabled pilot](experiments/phase9/p8_pitch_dev_20261112_pitch/run.json)

Two fresh OBS repeats used the successful pilot layouts. Layout 619126558
timed out with six planks and four sticks. Layout 619126559 produced an
inventory-confirmed wooden pickaxe from empty inventory in 80 actions and
1,226 game ticks. The 88.833-second and 77.067-second Minecraft-only MP4s
passed game-frame matching and full decoding. The spectator rendered on
the RTX 4050. The recorded attempts are separate from the matched sample.
[Timed-out repeat](recordings/phase9/youtube/p8_pitch_pickaxe_recorded_20261112_a.json)
[Successful repeat](recordings/phase9/youtube/p8_pitch_pickaxe_recorded_20261112_b.json)

### Placement training and transfer

Three live development episodes started with an unplaced table, three
planks and two sticks. Each placed the table and crafted the pickaxe in
five actions, taking 42–49 game ticks. Each produced a restorable
pitch-schema checkpoint with a nonzero REINFORCE update. The three
weight-update norms ranged from 0.0258 to 0.0280.

The final checkpoint and frozen expanded transfer then attempted the same
three fresh layouts in a different world with 420 ticks per trial. Both
scored 0/3. The trained policy placed one table and did not craft a pickaxe
within the deadline. The frozen policy placed no tables. Median action
counts were 38 and 36, respectively. All nine training and evaluation
episodes had acknowledged, matching terminal inventory. This prepared
fixture comparison provides no evidence that the three updates improved
completion on new layouts. The checkpoint stays separate from the
from-empty evaluation and earlier checkpoints.
[Training metadata](experiments/phase9/p8_pitch_place_train_20261112_a/run.json)
[Matched evaluation](experiments/phase9/p8_pitch_place_eval_20261112_a/run.json)

## November 17 pickup audit and pitch evaluation plan

The historical baselines remain 27/30 one-log, 20/30 three-log, 21/30
planks and 3/30 from-empty pickaxe. The Phase 7.5 fixed-pose diagnostic
verified that a policy-selected forward retry could jump over a
one-block step and shorten the approach to a visible trunk. Natural
exploration trials did not demonstrate a collection gain from a
separate forward prior, so the pitch plan leaves that prior off.
[Phase 7.5 live evidence](PHASE_7_5_REPORT.md#november-17-fixed-pose-blocked-forward-diagnostic)

Reanalysis of the seven historical yaw-only failures with three breaks
found that each sampled forward at least once with a visible drop after
the final break. In two episodes the drop appeared in only one decision
and was lost immediately after forward input. In five episodes there were
2–41 drop-visible decisions and 2–19 forward selections while a drop
was selected. Among the 43 forward selections with a following decision,
six had blocked movement, all in the same episode. The same drop remained
selected after 35 forward inputs, and its distance fell by at least
0.02 blocks after 22 of those. In the earlier pitch pilot, a failed three-log episode
broke three logs, finished with two, and never saw a drop in the six
decisions remaining after its final break. These traces identify both
brief loss of visibility and failed approach while the sensor still
selects a drop. A forward prior for target-absent exploration would
leave the latter decisions untouched.
[Post-break trace audit](experiments/phase9/phase8_pitch_followup_20261117/pickup_audit.json)

The pitch follow-up fixes 30 fresh layout seeds across six disposable
worlds, with the preserved checkpoint and a separate 24/30 controlled
one-log gate before the longer goals. It requires server-confirmed
inventory, terminal acknowledgment and explicit block or recipe
evidence. The planned scoring retains drop visibility after mining
and legal placement offers before workbench use.
[Fresh 30-trial-per-goal plan](experiments/phase9/phase8_pitch_followup_20261117/heldout_plan.json)

### Controlled one-log gate for the pitch candidate

The candidate collected a log in **26/30 trials (86.7%)**, passing the
24/30 point gate. The descriptive 95% Wilson interval was 70.3%–94.7%.
The five-layout blocks scored 4/5, 3/5, 4/5, 5/5, 5/5 and 5/5 across
six fresh world seeds. Each run used the frozen readout with pitch
actions enabled, two-tick forward input and a 400-tick limit.
All 30 inventories matched at the acknowledged terminal boundary.

Across successes and failures the median was 10 actions and 8.76
episode-wall seconds. Three misses broke a log without pickup. The
fourth saw a log and did not reach a legal mining view. This controlled
result clears the one-log prerequisite for the longer pitch trials.
The Phase 7.5 matched vanilla-terrain set remains at 0/2 per condition.
[Verified per-episode scores](experiments/phase9/phase8_pitch_followup_20261117/one_log_results.json)

### November 19 continuation

The saved evaluation contains 5/7 three-log successes, 3/7 pickaxe
successes and 5/5 plank successes. These counts are interim. All scored
episodes passed the independent inventory and terminal-delivery audit.
The second longer-goal batch reached its wall limit during an unscored
three-log episode. Its four earlier scored episodes remain included.
The interrupted episode is preserved and its layout receives a fresh
attempt. The remaining cells use the same checkpoint, observations,
policy RNG, action cap, tick deadline and actuator settings.
[Audited continuation baseline](experiments/phase9/phase8_pitch_followup_20261117/progress_20261119_initial.json)

A fresh first-person repeat of the first pickaxe layout started with
empty inventory and confirmed one wooden pickaxe in 55 actions and
846 game ticks. It broke four log blocks, placed a table and completed
the recipe through the normal workbench transaction. The recorded
repeat stays outside the 30-trial sample.

The 55.867-second Minecraft-only MP4 uses the RTX 4050 spectator.
Its original verification and November 19 recheck both decoded all
1,676 frames, with matching SHA-256. Frame review shows mining,
approach and table placement. The spectator view does not display
the actor's inventory menu, so the inventory and recipe logs provide
the crafting outcome.
[Milestone metadata](recordings/phase9/youtube/p8_pitch_20261117_pickaxe_milestone.json)
[Playback recheck](experiments/phase9/p8_pitch_20261117_pickaxe_milestone/verification_20261119.json)

### November 20 resumed evaluation

After the November 19 user-requested pause, the implementation and
checkpoint hashes still matched the frozen evaluation. All 118 Python
tests passed again. The first two seed blocks now contain 7/10
three-log, 10/10 plank and 4/10 pickaxe successes. These remain
interim scores alongside the completed 26/30 one-log result.
[Audited first two blocks](experiments/phase9/phase8_pitch_followup_20261117/progress_20261120_first_two_worlds.json)

The November 19 continuation repeatedly reached the 768 MiB RAM reserve.
Unscored attempts and partial episodes are preserved. The smaller
384 MiB server heap uses the runner's supported range, with the same
policy settings, observations and action deadlines. Available memory
recovered before the November 20 continuation.

One unintended extra plank repeat was queued during the smaller-heap
resume because the first schedule scan omitted the November 19 run
names. The scan was corrected, the extra repeat was designated for
exclusion before its outcome, and it stopped at the RAM guard without
a score. The scorer now rejects its run ID explicitly.
[Exclusion record](experiments/phase9/phase8_pitch_followup_20261117/excluded_runs.json)

The midpoint audit has 10/15 three-log, 14/15 plank and 6/15 pickaxe
successes. Every scored episode has acknowledged, matching terminal
inventory. Each successful crafting episode also has the required
confirmed mining, recipe and placement actions. Source and checkpoint
hashes remain fixed. The remaining 15 layouts per goal stay scheduled.
[Midpoint scores and failure modes](experiments/phase9/phase8_pitch_followup_20261117/midpoint_results_20261120.json)

## November 20 completed pitch evaluation

All 120 planned episodes have independent server inventory scores,
matching controller terminal inventory and acknowledged terminal delivery.
Every success has confirmed log breaks. Crafting successes also have the
required confirmed recipe and table-placement actions. All 120 scored
controller records have learning disabled and zero weight updates.

| Goal | Verified successes | Point target | Result | Descriptive 95% Wilson interval |
| --- | ---: | ---: | --- | --- |
| One log | 26/30 (86.7%) | 80% | Met | 70.3%–94.7% |
| Three logs | 18/30 (60.0%) | 70% | Missed | 42.3%–75.4% |
| Four planks | 27/30 (90.0%) | 70% | Met | 74.4%–96.5% |
| Wooden pickaxe from empty inventory | 12/30 (40.0%) | 50% | Missed | 24.6%–57.7% |

The action and time medians include successes and failures. Wall time is
the controller-recorded episode duration, excluding process launch.
Game time is the server scoring tick count divided by twenty.

| Goal | Median acknowledged actions | Median wall seconds | Median game seconds |
| --- | ---: | ---: | ---: |
| One log | 10 | 8.76 | 8.90 |
| Three logs | 96 | 70.12 | 70.23 |
| Four planks | 14 | 10.51 | 10.65 |
| Wooden pickaxe | 108 | 74.99 | 75.00 |

The fixed plan uses 30 layout/world-seed pairs per goal across six world
seeds. Relative fixture snapshots contain nine distinct arrangements for
the one-log and plank goals and fourteen for the longer goals. These are
controlled flat survival fixtures with semantic sensing, recipe macros,
planner masks and a supplied placement support face for pickaxes.
The Wilson intervals describe these layout outcomes without adjusting
for shared seeds or repeated geometry.
[Per-episode scores, settings, transaction evidence and failure modes](experiments/phase9/phase8_pitch_followup_20261117/final_results.json)

### Failure modes

Three one-log misses broke a log without pickup. The fourth never
reached a legal mining view. Two plank misses broke a log without
pickup, and the third never reached a legal mining view.

The twelve three-log failures finished with one log in two episodes
and two logs in ten episodes. Three failures confirmed at least three
breaks, and one of those saw no dropped-log target after its final
break. The other nine failures confirmed fewer than three breaks.
The pitch candidate therefore retains both mining/approach failures
and pickup failures.

Of the eighteen pickaxe failures, twelve stopped after confirmed
stick crafting, four reached a confirmed crafted table, and two
stopped after mining. All four failures with a crafted table received
at least one legal placement offer and selected no placement action.
Every successful pickaxe episode confirmed its own table recipe,
placement and pickaxe transaction from an empty starting inventory.

### Provenance, assistance and remaining gaps

The checkpoint SHA-256 is
`acdde37f8d3288764bcaad9dc9eea7c4f916c9894f54a019684fc3f555dd37f5`.
The live implementation SHA-256 is
`797c90920bd4dd348804c49ff578da65b4615b8fcbd46b1daf6ce82e4c3873ce`.
The sparse graph SHA-256 was reverified as
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.
The original 139,255-neuron graph and earlier checkpoints are preserved.

The candidate uses the optional 66-feature, twelve-action pitch interface,
bounded 15-degree camera turns, two-tick forward input, displacement
feedback and the preserved 120-action policy limit. Long goals use
1,500 ticks. One-log and plank goals use 400 ticks. Mined-column tracking
and the three-tree fixture apply to the longer goals. The fixed plan
leaves the forward-retry jump and target-absent forward prior disabled.
Those features have separate Phase 7.5 diagnostics and ablations.

The trained readout samples actions. Semantic resource sensing, legal
affordances, recipe execution, goal dependencies and the optional motor
assistance are engineered components. This evaluation used fixed
weights. The five-policy held-out vanilla comparison scored 0/2 in each
condition, with a separate 0/2 forward-prior result. The new goal scores
establish no learning advantage or neural contribution. The older
yaw-only scores and the small pitch development pilot remain separate
evidence on their recorded seed sets.
[Matched policy comparison and exploration evidence](PHASE_7_5_REPORT.md#fresh-held-out-vanilla-comparison)

The finalized evaluation records include one wall-budget interruption
and four RAM-guard stops. Their scored episodes remain included,
and unscored episodes were repeated in fresh disposable saves.
A user-paused attempt and the explicitly excluded extra repeat are
preserved separately. Fresh attempts retain their own run identities.
The RAM reserve remained 768 MiB, the GPU temperature cutoff remained
75°C, and the disk guard remained 2,048 MiB. Peak sampled GPU temperature
in the finalized evaluation runs was 56°C. CPU temperature telemetry
was unavailable. Earlier runs used a 512 MiB server heap, and resumed
runs used the supported 384 MiB heap.

The Python suite passed all 118 tests on November 20. The same frozen
Fabric source had passed assembly and the three standalone Java test
mains. Gradle's default test task did not discover those standalone
mains. All runner-owned Minecraft and bridge processes exited or were
cleaned up. The final supervisor completed all 120 unique scored cells.
[Resume ledger](experiments/phase9/phase8_pitch_followup_20261117/resume_runs.json)

Two accepted development milestone exports show the first-person
obstacle recovery and a from-empty pickaxe. They are separate fresh
executions outside the benchmark. The Minecraft-only RTX 4050 captures
passed window matching and visual review. November 20 full decoding
reverified all 869 frames of the 29.0-second jump video and all
1,676 frames of the 55.867-second pickaxe video. Earlier partial
captures retain their original evidence and explicit coverage labels.
[Playback and checksum verification](experiments/phase9/phase8_pitch_followup_20261117/milestone_verification_20261120.json)

Phase 8 remains open for the three-log and pickaxe reliability targets.
Natural-terrain search and collection remain unestablished. The
10,000-world Phase 9 campaign remains pending separate authorization.

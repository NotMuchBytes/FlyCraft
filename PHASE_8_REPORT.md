# FlyCraft — Phase 8 progress report

Updated: 2026-10-28 (Asia/Amman). **Phase 8 is not complete.**
Matched live evaluation is still underway; no 30-trial completion target has
yet been demonstrated. This report preserves the current evidence and will be
updated when the bounded evaluation batches finish.

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
incomplete batches. Final comparisons remain pending.

## 4. Comparison with Phase 7 and neural contribution

Phase 7's real bridge supported navigation only. Phase 8 has demonstrated
real acknowledged log pickup and plank crafting in development pilots. Phase
7's held-out simulated pickaxe result remains 160/300 (53.33%); that result is
not comparable to a live controlled pilot.

No positive causal neural-contribution claim is established yet. The full
live controller computes the existing 18-step neural sensory window. The
`no_neural` condition retains the bias and goal/inventory/context features
while removing the three neural readout values. This does not remove the
engineered planner or semantic observations. The matched comparison is needed
before attributing success to the sparse neural model.

## 5. Reliability checks

The 55-test suite passed after the initial Phase 8 implementation. An added
completed-checkpoint regression also passes. Phase 8 tests cover server
inventory consistency, block acknowledgment versus pickup, failed mining and
recovery, missing acknowledgment timeout, episode/connection interruption,
crafting failure, pending-transaction checkpoint restoration without replay,
neural-feature removal and completed-checkpoint result isolation. The Fabric
main/client sources compile successfully.

Unit protocol tests do not replace live mining-interruption, network-loss or
natural-world reliability evaluations. Those live stress tests remain work.
The recording interruption exposed a real fail-closed path. Its metadata's
original `wall_budget` label predates the supervisor error-label fix; the
launcher traceback identifies recording-confirmation loss as the cause.

## 6. Limitations and completion gates

The 30-trial targets remain unestablished: one-log 80%, three-log 70%, planks
70%, pickaxe 50%. Earlier pilots reuse layouts and cannot count toward those
targets. Broader held-out evidence and confidence intervals remain pending.
The fixtures begin near small trees, use semantic rays and recipe macros, and
do not test exploration, arbitrary terrain, hostile environments or pixel-only
control. Longer-goal policy errors and curriculum transfer remain substantial.
GPU samples during completed pilots stayed at or below 52 C; CPU temperature
was unavailable. Runs are bounded and supervised; no overnight training is
performed. Weekly and five-hour usage are checked through actual account
telemetry.

## 7. Phase 9 recommendations

Complete matched live evaluations before expanding scope. Improve recovery
from resource-consuming off-goal crafts, then test rehearsal and goal-specific
reward baselines across multiple training seeds. Separate transaction
reliability from policy success, test interrupted actions and reconnects in
real game sessions, and progressively replace nearby flat fixtures with
unseen terrain and natural tree search. Retain all negative results.

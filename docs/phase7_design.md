# Phase 7 design and evidence boundary

The original 139,255-neuron graph and its dynamics remain fixed. Phase 7
extends the Phase 5 `LinearSoftmaxPolicy`, rather than introducing another
neural model. The default Phase 5 four-feature/four-action interface and its
old checkpoints still work.

## Control and learning

`ResourceWorld` extends `World2D` movement and `AngularSensor` observation with
finite trees, explicit collection, recipe inventory consumption, local crafting
stations, and optional collision/vision obstacles. This is an intentionally
simplified simulator, not a Minecraft physics or crafting implementation.

The recipe planner specifies required outcomes and a dependency graph. It
reserves ingredients when expanding recipes and uses cumulative production
counters so that consuming an ingredient does not invalidate a historical
milestone. The root always requires the actual final inventory. Unexpected
loss or off-plan spending can reopen prerequisites through bounded replanning.
The manager validates dependencies, rejects cycles, and selects ready goals
by priority. It never emits an action sequence.

Every action is sampled by the existing softmax readout. Its Phase 7 shape is
63 features by 10 actions (630 parameters). Inputs are the four existing neural
features, their interactions with eight subgoal kinds, near-goal indicators,
bounded inventory summaries, recent failure/stagnation/visibility summaries,
and the last action. The brain's sensory mapping, sparse connectivity,
normalization, and neuron count are unchanged. Prior readout weights transfer
to the original first four rows/columns; added weights start at zero.

The action set adds collect, four crafting interactions, and table placement.
An environment mask removes physically impossible interactions. It does not
choose the action appropriate to the current goal: surplus and incorrect
crafting remain possible. This mask and the recipe graph are substantial
handcrafted assistance and are held constant in the main learning comparison.

Training uses the existing episodic REINFORCE implementation with discounted
returns, its moving scalar baseline and gradient clipping, plus optional
entropy regularization. Both unsuccessful and successful trajectories update
policy weights. There is no action-sequence playback, imitation oracle, deep
network, or connectome edge plasticity. Previously learned behavior is reused
through policy parameters; memory stores outcomes and best lengths, not a
script executor.

The final reward is visible same-target distance progress plus 0.2 times
angular improvement, a 0.02 action cost, a 0.10 failed-action cost, 0.25 per
unit of production still needed by the active subgoal, 8 on root completion,
and -2 on unsuccessful termination. Earlier all-production shaping rewarded
surplus crafting; those exploratory logs/checkpoints remain under `v2`.

## Persistence and stopping

Memory retains 64 recent action/observation records, world-scoped obstacle and
last-seen information for up to 16 worlds, authoritative observed inventory,
goal progress, and success/failure statistics. Memory affects policy features.
Persistent checkpoints include this memory, policy/baseline, RNG, curriculum,
goal statuses, recovery state, pending action and full learning trajectory.
An optional simulator snapshot allows exact mid-action continuation.

New Phase 7 checkpoint writes are atomic and refuse to overwrite artifacts.
The fixed feature cache digest and interface schema are checked on restore.
Real Minecraft world state is not restored by a Python checkpoint.

Episodes default to 120 actions and at most four recovery events. Recovery
detects repeated failures, stagnation, missing resources, interruptions and
unexpected inventory changes. It replans and temporarily suppresses one
ineffective action while leaving sampling to the policy. Missing resources
terminate only when the active subgoal still needs a resource. A recovery is
counted successful on later measurable progress; this is not a causal estimate
of how many goals recovery rescued. Replanned subgoal attempts contribute to
both numerator and denominator of subgoal metrics.

## Curriculum and evaluation

The six levels are navigate, nearby collection, find-and-collect, three-log
collection, planks, and a wooden pickaxe. Promotion requires a separate
40-world evaluation meeting 70% success and a configurable action bound.
Evaluation never updates the learner or its memory/RNG. Training, curriculum
evaluation and final evaluation use distinct seed domains in the recorded
runs. Final evaluation uses 100 unseen simulator seeds per goal for each of
three trained policies; these are shared matched worlds, not 300 distinct
world layouts per goal.

The main comparison uses the same planner, sensors, affordance masks and
recovery with frozen transferred versus trained readout weights. The original
four-action Phase 6.5 policy is also evaluated with its original action set,
and a uniform policy measures what planning plus random actions accomplishes.
Seed 29 additionally has shuffled-neural and disabled-recovery controls.

## Fabric boundary

The optional live adapter supports only `navigate_object`. The original
newline-JSON TCP bridge and 18-step full-connectome neural window remain in
use. Additive telemetry supplies player pose, ray-hit distance and a world
session identity. Distance completes goals; the policy receives near-state
and neural features rather than target coordinates. Full neural windows,
not the cache, run for live action decisions.

An observed block-face distance of at most 0.85 is conservative with respect
to the server's 1.6-block center-distance criterion. Tick/world matching,
response-age rejection, one outstanding request, bounded action duration and
stopping requests at terminal status limit stale/interrupted control. The
server smoke harness places a marker once and measures progress without
selecting any actions. Live training and resource/crafting execution are not
implemented or claimed.

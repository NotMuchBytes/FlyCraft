# Broader curriculum revision — November 25, 2026

The user selected “Use a staged broader curriculum” for the remaining budget.
The original wood campaign is paused and preserved at 338 generated worlds,
337 scored episodes and checkpoint SHA256
`ab18a30bd132b3556bfbfaa211fe78982de0a715215b30385a1d9a9326e46e78`.
Its untouched final evaluation seeds remain excluded from this revision.
The total authorized training budget is still 10,000 generated worlds,
including aborted instances. This leaves 9,662 new training slots. Separate
development and evaluation worlds do not count as training worlds.

## Executable stages and gates

1. Terrain: 64 training worlds, three seeded step/log teaching arenas followed
   by one wood retention task. Retention rotates one log, three logs, planks
   and wooden pickaxe. The arena has an absolute starting pose and ordinary
   survival physics; it is not a vanilla-overworld benchmark.
2. Natural exploration: 128 training worlds, with the same three-to-one
   retention mix. Primary episodes start at actual vanilla overworld spawns;
   the operator never surveys resources or places trees.

After each stage the candidate checkpoint is locked. Thirty fresh primary
seeds are run under trained, frozen transfer, uniform, no-neural and shuffled
neural conditions. Each condition gets the same seed, policy RNG, interface
and budget. Retention trials use the locked trained candidate. Revision 2
evaluates 30 fresh retention seeds per wood goal (120 total per stage) and
requires at least 24/30 one-log, 21/30 three-log, 21/30 plank and 15/30 pickaxe
successes, alongside 24/30 primary trained successes. Point thresholds do not establish neural benefit;
condition results, intervals, action counts, elapsed time and failures must
still be reported. Exact replays of entity RNG are not claimed.

Stone tools, food/shelter, mining/survival, combat and Nether/progression are
reserved stages with **no executable interface in this revision**. After the
two supported stages the runner stops at `awaiting_next_skill_implementation`.
It never fills the remaining budget with mislabeled wood episodes. The full
broader curriculum has no measured completion ETA yet.

## Transfer and engineered assistance

The sparse 139,255-neuron connectome stays unchanged, with the existing full
18-step neural observation window at each decision. Only the linear readout
learns. Terrain mode expands the 66-feature/12-action pitch head to 74/13;
the original weight prefix is preserved exactly in the transfer.
The new jump column copies the forward logits with a grounded `log(4)`
penalty: an explicit starting prior, not a learned jumping result. New
observation weights on existing actions start at zero. The old checkpoints
are neither overwritten nor silently loaded through an incompatible adapter.

New inputs are own health, food, grounded state, and visible obstacle,
support, lower surface and water flags, plus previous jump action. Terrain
flags use 15 first-hit rays in the existing camera-relative field of view,
with a three-block range. Occluded and unknown space is not supplied as a
map. No unseen resource location enters the policy or reward. The optional
novelty reward uses only new two-block cells of the actor's own visited pose,
while no resource is visible; its reward is bounded to the first 15 new cells.
Observed health loss is penalized. These are engineered reward choices.

`JUMP_FORWARD` is sampled by the same policy as every other action. It applies
one normal jump pulse and eight fixed forward ticks. It is legal only on dry,
grounded observations. There is no blocked-retry jump assistance or aiming.
Acknowledgments report upward displacement, peak height and horizontal
movement. Jumping alone never establishes resource success: the existing
independent checker still requires an actual log break and inventory gain.
Semantic sensing, masks, planner structure and recipe transactions remain
engineered assistance, shared across all controls.

## Provenance and operations

The isolated development checkout is `C:/Users/anass/Documents/Codex/FlyCraft-curriculum`,
branch `phase9-staged-curriculum`; the original checkout and STOP are preserved.
The frozen plan is `experiments/phase9/fc9_stage25/config.json`. Its source,
seed catalog, transferred checkpoint, each input/output checkpoint, and raw
evidence are hashed. Cached Java exports retain the verified speedup; changing
policy/runtime code invalidates the frozen plan and launcher cache.

The runner independently checks every episode and pauses for contradictory
evidence, a technical interruption or nine failures in ten primary training
episodes. It never edits code from log instructions. Unsupported skills and
failed gates cannot report completion or trigger shutdown.

The 768 MiB live RAM reserve, 2,048 MiB disk reserve and 75°C GPU guard remain.
Launch requires a 30-second healthy window at 1,800 MiB available RAM, or
3,000 MiB for a recorded milestone. CPU temperature is unavailable. Native
Windows sleep/shutdown protection now watches both campaign STOP files and
releases at critical unplugged battery. Locking Windows is compatible with
headless training; OBS milestone capture must still pass its actual-frame
preflight and full video decode. A failed recording is preserved and any
later capture is a labeled new execution, never an exact replay.

The old wood-only completion shutdown watcher is cancelled because its plan
is superseded. Its replacement watches the staged ledger, requires all skills
and gates complete, verifies the foundation and new artifacts, and retains
the original 60-second cancellable non-forced shutdown. Later skills pending,
failed gates, STOP or technical errors cannot trigger shutdown. Fan maximum
speed is still unverified: the missing HP services require a reboot that has
not been performed during training.

## Development evidence

All 166 automated tests pass, including matching, retention and shutdown eligibility checks. Native Fabric
compilation succeeds. Two matched-seed evaluation probes both scored 0/1
one-log collection in the teaching arena (80 actions and 60 game seconds
each). The first zero-column transfer selected 25 jumps; the movement-prior
candidate selected one. Both have native jump acknowledgments confirming
about 1.252 blocks of peak upward displacement. Neither broke a log. Thus
jump execution is demonstrated; collection improvement and natural-terrain
reliability are not. Raw logs, initial poses and independent audits are in
`experiments/phase9/terrain25_probe001` and `terrain25_probe002`.

The first actual curriculum world (official training slot 339) succeeded in
13 actions and 264 ticks, with two independently confirmed breaks, one log in
inventory and a verified readout change. Its original Minecraft-only RTX
4050 milestone MP4 passed capture preflight and full decode. This is training
evidence, not a held-out score or proof of learned benefit.

The first four new training worlds scored **2/4**: terrain **1/3** (Wilson
95% interval 6.1–79.2%) and wood retention **1/1** (20.7–100%). Terrain averaged
62.7 actions, 44.4 game seconds and 68.0 worker-wall seconds, including its
recorded milestone. Retention used eight actions, 6.3 game seconds and 22.7
worker-wall seconds. The two terrain failures reached the fixed tick budget
without a confirmed break; turning/exploration remained weak. All four actual
readout changes and their checkpoint chain were reverified, with the original
connectome and transferred weight prefix unchanged. Full results and raw
evidence hashes: `experiments/phase9/staged25_operations/first4_audit.json`.

Through official world 350, twelve new training worlds scored **6/12**:
terrain **4/9** (Wilson 95% 18.9–73.3%) and retention **2/3** (20.8–93.9%).
Eleven actual readout updates were verified; one unexecuted terminal command
correctly suppressed learning. Milestones 339 and 350 both passed complete
decode and sampled review. See `through350_audit.json` in the same operations
folder for per-episode actions, times, failures and checkpoint lineage.

Before evaluation, revision 2 hardened natural controls to reuse the trained
reference's actual native starting XYZ/yaw/pitch. The checker rejects pose
drift instead of trusting a requested teleport. A separate development pilot
ran all five conditions on one fresh natural seed with exactly matching poses,
policy RNG and 600-tick budgets. Each scored **0/1**, with zero updates and no
visible target or confirmed break. Trained/frozen/no-neural/shuffled used 40
acknowledged actions; uniform used 43. Trained moved only 1.23 blocks net,
versus 11.69 for uniform. This confirms the comparison interface and the
remaining exploration weakness; it establishes no broader skill or neural
benefit. It uses development data, not the held-out gate seeds. Exact entity
RNG replay remains unverified. `natural_interface_pilot.json` and
`natural_pilot_exploration_audit.json` retain the evidence.

Revision 2 preserves the prior source/config/state at world 350. It changes
comparison setup and evaluation gates, with **no actor, reward, readout,
training seed or training action-budget change**. All four wood skills now
need retention gates so a stronger collection score cannot hide forgotten
crafting. The next official training slot is 351.

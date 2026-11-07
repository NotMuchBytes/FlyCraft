# FlyCraft Phase 7.5 reliability status

Date: 2026-10-28. Status: **in progress**. The strict-mode 30-trial live
reliability requirement has not been met. This report does not declare either
Phase 7.5 or Phase 8 complete.

The original 139,255-neuron brain, earlier checkpoints, simulation experiments
and working Fabric resource interactions remain preserved. Phase 8's historical
assisted one-log comparison scored trained 29/30, frozen 27/30, uniform 19/30
and no-neural 25/30 in reset flat fixtures. It included visible-target aiming
and is not evidence for the later crosshair-only control interface.

## Changes and bugs

The bounded tick-based camera controller implements configurable yaw/pitch
speed, acceleration/deceleration, relative endpoints, continuous-command expiry,
safe replacement/cancellation, wraparound, pitch clamping and requested/body/
rendered telemetry. The AI selects camera actions; block interactions require
the actual crosshair. Camera probes and the three-layout policy comparison are
documented in `docs/camera_controller.md`, including the increased settling time
and the late-pickup failure. Overshoot measured zero in both motor conditions;
no overshoot reduction is claimed. The existing learned action set lacks pitch.

Connection-loss lifecycle polling, native-crash detection and owned-process
cleanup were improved. NVIDIA OpenGL and the dedicated Java application's GPU
preference avoided the reproduced AMD-driver shutdown crash in bounded later
tests; no global driver changes were made. RAM reserve and GPU temperature
guards prevent continued resource pressure.

Inventory scoring now uses an immutable terminal tick snapshot and explicit
delivery acknowledgment. The controller seals its episode ledger and cannot
credit later pickups or old inventory packets to an expired episode. Missing
or unexecuted terminal commands suppress training. Outdated camera actions are
canceled rather than accumulated. Existing bounded goal recovery remains active;
there is no demonstrated new long-horizon recovery improvement.

The headless survival prototype's incorrect initial spawn was fixed, normal
player physics retained, and semantic sector boundaries aligned. Its separate
spectator camera has no influence on the actor's observations or decisions.
An OBS wrong-image failure is preserved and rejected; exact-title Windows
Graphics Capture and image preflight now gate new recorded trials.

## Verification and limits

The October 28 full suite passed 74 tests in 17.153 seconds, covering old behavior
plus terminal inventory, interruption/acknowledgment handling, restoration,
camera kinematics, launch arguments and recording integrity. Fabric compiled
and the accepted headless redo's client/server exited cleanly. The existing
Phase 7 1,800-episode simulation regression remains preserved separately.

Strict live policy camera pilots scored instant 3/3 and bounded 2/3 within
their 20-second deadline. Later headless development redo collected a log in
1/1 trial, with actual block change and inventory confirmation, plus a verified
MP4 showing the supplied skin. One subsequent real training trial also collected
a log and saved a nonzero readout update that loaded successfully. These tiny
development checks are not an independent 30-trial success estimate. Their
full provenance is in `PHASE_9_REPORT.md`.

Memory optimization matched six tested full neural windows exactly while
reducing post-initialization controller RSS. It is an implementation optimization,
not evidence that memory improves decision-making. Neural contribution,
catastrophic forgetting, reward exploitation and long-horizon recovery still
need matched repeated training/evaluation experiments. Earlier non-neural and
frozen comparisons do not establish a causal benefit for neural features.

Next: run independent strict one-log trials across starting conditions, validate
real interrupted mining and reconnect recovery, then collect the required
matched five-policy comparisons. Keep negative results and MP4 gaps explicit.
Finish these reliability gates before claiming broader natural-world autonomy.

## October 29 reliability and learning increment

The full automated suite now passes **90 tests in 16.376 seconds**. Passive
terminal pickup updates goal memory without inventing an executed action;
unsafe reward attribution suppresses learning. Both adapters reject replies
for obsolete episode IDs. Successful terminal cancellation no longer creates
a false failed action/recovery. Windows status-file reader contention and
early-render capture preflight failures received bounded retry fixes.

A live STOP/resume check preserved an interrupted episode and partial MP4,
discarded its candidate update, and restored the last committed checkpoint in
a fresh attempt. Two new real training episodes committed verified readout
updates. The serial coordinator uses durable state, source/checkpoint hashes,
exclusive worker leases and finite jobs. Connection-loss and mining-interruption
reliability across repeated real sessions remain unestablished.

The five-policy strict live comparison used two matched development seeds:
trained 1/2, original frozen Phase 7 2/2, uniform 1/2, neural removal 0/2,
shuffled features 1/2. All ten MP4s are verified. All paired exact p-values
are 1.0, so neither a learning gain nor causal neural benefit is established.
The trained failure repeated unproductive turns/movements until its finite
400-tick deadline; one detected stagnation/replan did not recover the goal.

A separate empty-inventory plank pilot collected a log and crafted four planks
in four actions/93 ticks (1/1), with actual block/inventory confirmation and
a verified MP4. Recipe clicks remain an engineered action transaction. The
simulation-only retention and rehearsal experiments show possible task tradeoffs,
without significant improvement; neither rehearsal candidate was promoted.
Details and actual intervals are in `PHASE_9_REPORT.md`.

The strict 80%-of-30 live one-log gate remains unmet. Phase 7.5 is not complete.
Preserve the current evidence and broaden independent strict evaluations before
scaling or claiming reliable natural-world collection.

## Later October 29: strict one-log evaluation

The subsequent fixed 30-seed evaluation scored **27/30 (90%)** with two-tick
forward input, bounded 15-degree turns and crosshair-only mining. Actual frozen
inventory and acknowledged boundary delivery confirmed outcomes. The point
target is met for these controlled near-tree fixtures; Wilson 95% interval is
74.4%-96.5%. Thirty distinct seeds produced seven relative fixture snapshots,
so this does not demonstrate natural exploration or 30 unique terrain types.

All three failures are retained: one mined without pickup, two never broke a
block. Near-zero movement sometimes still receives a successful-input ack;
collision feedback and recovery remain weak. Every trial ended within the
400-tick deadline and all servers closed cleanly. Milestones 1,10,25,30 have
verified MP4s; the other 26 intentionally retain logs only per the user's change.

Trial 11's early success row lacked its terminal field. The coordinator stopped;
an audited validator-only repair confirmed the unchanged raw acknowledged
inventory boundary without rerunning gameplay. Previous config/source/state
and the rejection are archived. Actor, controller, policy and trial settings
did not change. All **97 tests passed in 20.020 seconds** after this repair.

The checkpoint remained unchanged throughout evaluation. The 27/30 result
establishes no new learning or causal neural contribution. Full provenance,
motor comparison and limitations are in `PHASE_9_REPORT.md`. Broader connection,
interruption, long-horizon and recovery validation remains; Phase 7.5 is not
declared complete solely from this collection milestone.

## Repeated plank validation and remaining reliability work

A second fixed 30-seed evaluation scored 21/30 (70%) from empty inventory to
four planks (Wilson 95% 52.1%-83.3%). All 21 observed pickups led to a confirmed
craft; six failures mined without pickup and three broke no block. The engine's
recipe clicks remain an engineered macro selected by the learned policy.
All 98 automated tests pass; the new goal predicate rejects a log-only false
craft success. The source and checkpoint stayed fixed for this evaluation.

Only milestones 1,10,25,30 were recorded, as requested, and all four MP4s are
verified; routine episodes retain logs. Both one-log and plank point targets
are now met in controlled fixtures. This does not establish natural-world
autonomy, causal neural benefit or new learning. Repeated live fault recovery,
blocked-movement feedback, policy pitch control and longer goals still need
work. Phase 7.5 is not declared wholly complete. See `PHASE_9_REPORT.md`.

## Blocked movement feedback increment — October 29

Root cause: both Fabric adapters previously marked FORWARD successful when its
input timer expired, even if the player had not moved. Recovery uses action
errors to recognize repeated failure, so stationary input could remain invisible
to that path until the much longer stagnation threshold. Historical live traces
contained successful-input acknowledgments with near-zero displacement.

Both adapters now measure horizontal own-player displacement from actual action
execution to completion. A completed forward pulse below 0.02 blocks reports
`movement_blocked`; acknowledgments also include distance, confirmation and
whether verification was enabled. Interrupted commands keep their original
interruption reason. This detects lack of movement, not a unique collision
cause. The graphical adapter uses its own client pose; headless uses server pose.
No hidden map, target position, automatic steering or aim is introduced.

`--movement-feedback displacement` is the new default. The explicit
`input_only` mode preserves the older acknowledgment semantics for comparisons.
Existing recovery and policy selection are unchanged: repeated failures can
temporarily mask the ineffective action, but the learned readout selects the
next action. The brain remains 139,255 neurons with the same checkpoints.

The pre-change suite passed 98 tests in 15.252 seconds. The updated full suite
passed **100 tests in 15.699 seconds**. New tests compile and execute the actual
Java displacement threshold, zero/diagonal movement and invalid-pose cases,
and verify that blocked acknowledgments trigger bounded recovery without
inventing collected resources or scripting a recovery action. Fabric compilation
and both live server/client launches passed in the milestone trials.

Six real Minecraft episodes compared both feedback modes across three reused
development layouts that had failed historically, using the same checkpoint,
source, policy RNG seeds, relative initial fixtures, two-tick forward pulses,
camera settings and 400-tick budgets. Complete world/entity RNG is not matched;
all executions are fresh, not replays. Learning was disabled.

| Mode | Success | Actions per case | Ticks per case | New blocked errors |
| --- | --- | --- | --- | --- |
| Input-only | 1/3 | 26,33,6 | 400,400,122 | 0 |
| Displacement | 1/3 | 25,34,6 | 400,400,117 | 2 |

Both success-rate Wilson 95% intervals are 6.1%-79.2%. Mean game times including
failures were 15.367 and 15.283 seconds; these tiny differences establish no
performance improvement. The enabled mode correctly reported two stalled
movements. They did not trigger repeated-failure recovery in the live trial;
the unit test verifies that path for consecutive failures. Broader recovery
and collection improvement remain unproven. One historically failed case
succeeded in both new modes, illustrating uncontrolled execution variability.

All six outcomes have actual inventory and acknowledged terminal-boundary
evidence, clean game exits and unchanged checkpoint hashes. The first case of
each mode was the predefined recording milestone: both complete MP4s passed
decode/content/checksum validation, despite both goals failing. Four routine
episodes intentionally have logs only. No required milestone MP4 is missing.
Peak sampled GPU was 42 C; minimum available RAM 3,315.145 MiB. CPU temperature
was unavailable. Data and the fixed plan are in
`experiments/phase9/phase75_movement_20261029/`.

The prior 27/30 log and 21/30 plank evaluations remain historical input-only
results; they have not been repeated under the new feedback semantics. Do not
pool this failure-selected pilot with them or claim a new learning/neural gain.
Next: larger matched feedback evaluations, blocked/drop pickup recovery, and
live mining/connection-loss stress tests. Phase 7.5 remains incomplete.

Actual weekly usage reached 55% after this bounded task. No new development
tasks or experiments were started afterward; results were packaged for review.

## Companion follow increment — reviewed November 5

Subsequent user-authorized companion work adds a separate opt-in singleplayer
NPC, engineered vanilla following, bounded stuck/no-route handling, stale neural
response rejection after mode changes, lazy brain loading and explicit death
recovery. Human controls remain independent. The 26.3 compatibility port is
isolated from the 26.2 development target; both compiled successfully.

One October 31 interactive Minecraft session produced 93 follow trace samples
and a fully decoded, playable 104.7-second Minecraft-only MP4. Following was
observed; human gameplay and teleport commands prevent treating this as an
independent evaluation. Normal world/client exit interrupted the planned
stop/resume check before acknowledgment. Respawn and water survival remain
unverified live. Earlier interactive resource sessions have no MP4; the follow
recording does not replace missing footage for them.

The regression suite gained a Java follow-steering/motor test; final verification
on November 5 passed **101 tests in 23.052 seconds**. No graph,
checkpoint or training update was made. Owner coordinates and server collision
knowledge belong only to engineered companion navigation, not neural resource
observations. This result does not add a log-collection success or establish
neural benefit. Full evidence, provenance and remaining checks are in
[`docs/companion_follow_validation.md`](docs/companion_follow_validation.md).
Phase 7.5 remains incomplete.

## November 6 reliability increment

The controller now validates position/visible geometry before committing
inventory and mining acknowledgments. An invalid-packet/retry diagnostic
counted one block twice before the fix and once afterward. Baseline 101 tests
passed; final **104 tests passed in 20.999 seconds**.

A recorded strict one-log smoke check succeeded in 2 actions/76 ticks. A real
+90-degree mining interruption produced `mining_aim_lost`; the learned
controller recovered and collected a log in 22 actions/358 ticks. These are
controlled survival fixtures, with learning off. A real 6.464-second bridge
process-tree stall exposed a protocol defect: an outdated command is discarded
without a rejection acknowledgment, leaving `acknowledgment_timeout`. That
trial mined but collected no log by 400 ticks. No infinite loop or crash occurred.
Work stopped at this reproduced problem under the user's instruction; the
handshake defect remains unresolved.

All four scored sessions have playable MP4s; final review marks the bridge-failure
clip's visual coverage partial because a game menu obscures part of gameplay.
The original metadata/footage are preserved. This includes a launcher-only pause
explicitly excluded from connection-recovery claims. Two zero-action preflight
attempts have no MP4 (RAM guard, AMD renderer). Six generated instances reuse
one seed, not independent unseen-world tests. Graph/checkpoint hashes are
unchanged; there were zero new training updates. See
[full evidence and next steps](docs/phase75_reliability_20261106.md).

## Bridge recovery follow-up

Both Fabric adapters now explicitly reject delayed, unexecuted commands so
the policy can discard the pending decision and sample again. The headless
26.2 recorded retry recovered from a 6.545-second bridge stall and collected one
log in 10 actions and 276 game ticks. A separate no-fault 26.2 regression
collected one log in 4 actions and 100 ticks. Both were confirmed by server
inventory. The run with the deliberate stall is excluded from ordinary
success-rate estimates. Both use one controlled fixture seed, with learning off.

The automated suite passed 107 tests and the mod compiled for 26.2 and 26.3.
The recovery MP4 passed a full decode. The first retry never reached gameplay
and has no MP4. Two no-fault recording attempts produced startup-only MP4s
before the RAM guard stopped the runs. Full transport disconnect and live
checkpoint restoration still require validation. See the
[recovery evidence and recording details](docs/phase75_rejection_recovery_20261106.md).

The November 7 read-timeout diagnostic uncovered a separate delivery defect.
After a 20.082-second stall, Java timed out before receiving command 2. The
controller issued that command on the closed connection and eventually
stopped at `acknowledgment_timeout`. One block broke, but inventory remained
at zero logs at 600 ticks. This was a log-only diagnostic. The read-timeout
path remains unresolved and Phase 7.5 remains incomplete. The full automated
suite passed again with 107 tests in 19.685 seconds.

The read-timeout repair now checks a failed-reply interval, command watermark
and adapter identity before it discards an undelivered policy decision. Both
Minecraft validation attempts reached the RAM guard. The first had no
gameplay. The second had one server-confirmed log, but the bridge was resumed
during cleanup before the socket deadline, so recovery remains unverified in
Minecraft. No milestone MP4 was produced. See the
[repair and retained run evidence](docs/phase75_rejection_recovery_20261106.md#read-timeout-repair-and-validation-status).

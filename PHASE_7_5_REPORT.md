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

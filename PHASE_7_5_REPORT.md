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

The latest full suite passed 74 tests in 17.153 seconds, covering old behavior
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

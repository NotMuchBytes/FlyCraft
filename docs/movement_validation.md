# Forward movement and navigation validation

The strict adapters previously held every FORWARD input for five ticks. The
retained two-seed control logs show roughly one block of displacement between
decision and acknowledgment observations. A policy can pass beside a nearby
tree before its next decision. Its subsequent repeated turns are discrete policy
choices, not evidence that the camera motor queued an excessive turn.

`tools/run_phase8_live.py --forward-ticks N` now configures a fixed 1-10 tick
input pulse in both graphical and headless adapters. The default remains five
for checkpoint/behavior compatibility. In a coordinator campaign, initialize
with `tools/run_phase9.py init ... --forward-ticks N`; its frozen runtime profile
is forwarded identically during training and all evaluation conditions. Missing
fields in older configurations retain the five-tick default.

Duration is fixed before a run. No target distance, target angle, fixture label
or hidden state selects it. The policy still selects FORWARD, turns, mining and
crafting. Vanilla physics retains inertia and collision; shorter input does not
promise a particular traveled distance or automatically stop at a target. Smaller
pulses may require more decisions and increase total task time.

The read-only `tools/analyze_live_navigation.py` matches episode/command/action
acknowledgments before measuring actual pose changes. It excludes commands
explicitly not executed and prevents duplicate or cross-episode credit. It
reports visible-target losses, unseen-decision streaks, sampled near-without-
mining observations, translation and wrapped yaw endpoint errors. Translation
includes drift and observation delay. Endpoint error does not measure peak
per-tick overshoot; use the existing camera trace for that.

The first comparison reuses two development seeds from the prior control pilot,
with learning disabled, identical checkpoint/RNG/camera/deadlines, and new world
instances for each motor setting. Both settings run the same updated source.
These are adaptive development checks, not fresh held-out evidence. Full MP4
coverage, game-state scoring and unchanged checkpoints are required before
accepting an episode. Results belong in `PHASE_9_REPORT.md`; do not pool different
movement settings into a single success rate or claim reliability from two seeds.

The paired pilot scored five-tick 1/2 and two-tick 2/2, with mean game times
12.55/6.95 seconds including failures. A subsequent predeclared 30-seed two-tick
evaluation scored 27/30 (90%; Wilson 95% 74.4%-96.5%). It used seven distinct
relative fixture snapshots across 30 world seeds. There was no learning, policy
change or natural-terrain test. One result-validator amendment is fully archived;
actor/controller/runner and the trial plan stayed fixed. See the Phase 9 report
for the three failures and the remaining blocked-movement feedback limitation.

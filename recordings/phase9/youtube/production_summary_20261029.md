# October 29 development footage notes

This is a development pilot, not the 10,000-world experiment. Official training
worlds: zero. Cumulative Phase 9 committed real training episodes/updates: three
(one October 28, two October 29). One interrupted candidate update was preserved
without promotion. Generated instances, distinct seeds and committed episodes
are different counters; see each campaign's state and source manifest.

## Usable sequences

- Training episode 1: `dev_pilot_20261029_b_pilot_trained_00001_a0001`, log
  collected in 15 actions/240 ticks. Verified 28.7-second MP4.
- Interrupted episode 2: `dev_pilot_20261029_b_pilot_trained_00002_a0002`,
  operator STOP after three acknowledged actions. Partial 15-second MP4, no
  committed episode/update. Label it interrupted, never successful training.
- Resumed episode 2: `dev_pilot_20261029_b_pilot_trained_00002_a0003`, new
  execution/world instance after restoring the last committed checkpoint;
  log collected in five actions/116 ticks. Verified 18.967-second MP4.
- Matched controls: all ten `dev_controls_20261029_c_eval_a_*` videos have
  verified complete episode coverage. Trained 1/2, original Phase 7 frozen 2/2,
  uniform 1/2, neural removal 0/2, actual-feature permutation 1/2. Include failed
  trials and finite deadlines. Two seeds do not establish a learning/neural gain.
- Planks: `headless_planks_validation_20261029`, empty inventory to mined log,
  pickup, then four planks. Four actions/93 ticks, verified 20.867-second MP4.
  Recipe clicks are engineered; the policy selects the action. Result 1/1.

Each corresponding JSON file here gives the exact video path, checksum,
duration and verification status. Full files are local under `recordings/phase9/`;
large MP4s are intentionally excluded from Git. Copies are in the chat outputs.

## Claims and presentation

No performance improvement or causal neural benefit has been demonstrated.
Frozen dynamics still use the preserved 139,255-neuron graph; only the small
readout learns. Semantic rays, goal decomposition, fixture preparation, action
masks/recovery and crafting macros are engineered assistance. The separate
observer follows only for recording and does not guide the actor.

Charts in `figures/` use retained real observations. Training plots contain only
two new committed observations. Static brain snapshots select a recorded
maximum-activity window and disclose that selection; they are not firing
animations or simulated footage. Simulation rehearsal is separate research and
generated no Minecraft worlds. Neither candidate was promoted.

Set A is reused development data; the final 100-seed Set B was not run. Early
RAM/I/O/preflight attempts have missing complete or partial-only footage, with
original logs retained. Historical rejected wallpaper footage remains rejected.
No episode has been faithfully replayed: successful redos are new executions.
Do not replace actions, invent frames or present partial footage as full coverage.

Remaining milestones: strict 30-trial collection/crafting gates, longer goals,
natural terrain, repeated interruption/reconnection, parallel throughput and
long-run memory stability. Phase 7.5/8/9 are not declared complete.

# Phase 9 evaluation status

No official Phase 9 evaluation has begun. Development seeds/layouts used while
debugging must not be relabeled as an untouched final benchmark. Generated
world instances, distinct seeds and episodes must be counted separately.
Repeated trials of seed 44556777 in this pilot are repeated development worlds,
not evidence of generalization across unseen seeds.

The coordinator now creates reproducible, disjoint pilot/training partitions,
100-seed Set A and 100-seed Set B using versioned SHA256 derivation. Set B
execution requires a frozen final policy; that selection blocks further
training. Evaluation disables learning, and a nonzero update or learning flag
fails commitment. Conditions share seeds, policy RNG, action budgets, camera
mode and affordances. Catalog creation does not mean those worlds were evaluated.

`headless_smoke_01` completed one real survival episode and failed (0/1).
The actor initially spawned at the default origin rather than the vanilla
adjusted spawn. The fixture was consequently placed in the air and the actor
fell away. This implementation error was fixed and the failed data preserved.

`headless_recorded_redo_02` completed one real survival episode and collected
one log (1/1). The frozen existing readout selected COLLECT_LOG and FORWARD;
the game confirmed one broken block and one inventory log. The harness ended
at 75 ticks, terminal acknowledgment arrived one tick later, and client/server
exited with code 0. Peak sampled GPU temperature was 49 C and minimum available
RAM was 2683 MiB. The recording is rejected for wrong content; actual gameplay
success does not validate its MP4. This single development success is not a
30-trial reliability estimate. Do not pool it with the earlier assisted policy
evaluation or the differently configured failed prototype.

`headless_recorded_redo_04` repeated the development fixture with corrected
capture: 1/1 log, 75 ticks, two sampled actions, one confirmed block change and
one inventory log. Both game JVMs exited cleanly. The 20.4-second MP4 passed
full decode (612 frames), actual-game/OBS image preflight and manual frame
inspection. Maximum sampled GPU temperature was 47 C and minimum available
RAM was 2355.906 MiB. This is a new execution of the frozen policy, not a replay
of the original failed episode. It is still one reused development layout.

`headless_learning_pilot_01` used a separate development seed 44556778 and
enabled learning: 1/1 log, 98 ticks, four actions and reward 9.3883. The measured
readout weight delta was 0.0361531, exactly matching the reported update. The
new checkpoint loaded successfully; the original checkpoint was preserved.
Its 19.633-second MP4 passed decode, image preflight and frame inspection.
This establishes that a real feedback update occurred, not that performance
improved. This seed is now training data and cannot be used as held-out data.

`headless_checkpoint_restore_01` restored that checkpoint into a fresh process
and development seed 44556779. With learning disabled, it collected one log in
106 ticks and four acknowledged actions. The checkpoint hash remained unchanged
after evaluation. The video was fully decoded and visually inspected. This
tests restoration, not generalization improvement. A late unexecuted policy
response was rejected at the boundary; terminal inventory still correctly
confirmed success. This historical run exposed incomplete passive terminal-pickup
reward/subgoal counters. The October 29 fix updates goal progress and logs
unattributed reward separately while suppressing unsafe learning.

Phase 8's historical 29/30 trained one-log result used visible-target aiming
assistance. The strict camera comparison used only three matched layouts:
instant 3/3 and bounded 2/3 before the deadline. These results and their
limitations remain in `PHASE_8_REPORT.md` and `docs/camera_controller.md`.

Required future comparisons are trained, frozen transferred, uniform action,
neural features removed, and neural features shuffled. All must use identical
observation/action affordances, matched starting conditions, separate unseen
seeds, actual inventory-based outcomes and reported failures. Small development
pilots are insufficient to establish causal neural contribution. Training must
be disabled for evaluation and checkpoint hashes retained.

## 2026-10-29 control definition

The new control campaign uses the preserved original Phase 7 policy as its
explicit frozen reference. Earlier development comparisons used the campaign's
starting checkpoint instead; those results remain separate. The no-neural
condition retains bias, planning, memory, context and masks but zeros the three
activity inputs. The shuffled condition now permutes the actual window's
activity columns as `[total, left, right]`, retaining bias. The historical
sector-swap control left centered inputs unchanged and used cached features;
its data and source manifests remain preserved. Do not pool these interventions.

Raw fixed-network activity and the intervened policy inputs are both logged.
Comparisons use identical real Minecraft affordances, camera limits, budgets and
paired seeds. Confidence intervals are descriptive over small controlled
fixtures. The final 100-seed Set B remains unused.

On October 29 the complete two-seed development comparison scored trained 1/2,
original frozen Phase 7 2/2, uniform 1/2, no-neural 0/2 and shuffled 1/2. Every
episode has a verified MP4 and unchanged evaluation checkpoint. All exact paired
comparisons give p=1.0; neither learning nor neural benefit is established.
See `experiments/phase9/validation_20261029.json` for actions, times, intervals
and failures, and `PHASE_9_REPORT.md` for simulation retention/rehearsal results.

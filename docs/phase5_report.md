# Phase 5 learning report

## Result

Phase 5 is complete. FlyCraft now has explicit seeded episodes, outcome-based rewards, policy-gradient updates, safe checkpoints, JSONL episode logs, and exact resume support. The connectome is not retrained: only a 4-by-4 softmax action readout over fixed connectome-derived features changes.

The first prespecified 400-episode experiment was retained as a negative result. It reduced final distance by 24.87% but improved success by only 11.33 percentage points, below the fixed 25-point gate. One registered follow-up increased training to 2,000 episodes per seed without changing the optimizer, task, seeds, evaluation, or thresholds.

## Follow-up validation

Across held-out evaluations for seeds 11, 29, and 47 (200 episodes per seed):

| Policy | Success rate | Mean final distance | Mean reward |
|---|---:|---:|---:|
| Untrained | 1.17% | 4.970 | 0.440 |
| Trained | 55.50% | 1.628 | 5.612 |
| Trained, shuffled neural features | 26.00% | 3.106 | 3.037 |

The trained policy improved success by 54.33 percentage points and reduced final distance by 67.24%, passing both prespecified gates. All three same-seed reruns were exact, all three loaded checkpoints matched the in-memory policies, and every training episode produced a nonzero weight update.

The shuffled-feature control remained better than baseline, so part of the gain is a learned forward-action prior. Correct neural feature alignment still added 29.5 percentage points of success over shuffled features. The hidden-target control was not safe: `NO_OP` occurred only 13.25–16.75% of the time. This policy should therefore run only under an external episode/task safety envelope until absent-target behavior is trained explicitly.

Artifacts: `experiments/phase5/results/learning_validation.json`, `experiments/phase5/runs/`, `checkpoints/phase5/followup_2000ep/`, and `docs/figures/phase5_learning_validation.{png,svg}`.


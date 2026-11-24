# Phase 8 reliability development, November 23

Phase 8 is still open. This directory is Phase 8 work in the existing live
harness's historical `experiments/phase9` output namespace. It authorizes
no Phase 9 campaign or checker implementation.

The completed November 20 frozen pitch evaluation remains 26/30 one log,
18/30 three logs, 27/30 four planks and 12/30 wooden pickaxe. Its 120 episodes
are now development/training data for the new readouts. They cannot also
serve as held-out validation of those readouts.

## Development comparison

World seed 202611230801, layout seeds 728310449, 461992637 and 890173251,
policy RNG 9001, 120 policy actions and 1,500 game ticks per longer goal.
All start empty. All use strict bounded 15-degree yaw/pitch actions,
three separate prepared trunks and mined-column memory. Jump assistance
and the target-absent forward prior are disabled. Two versus five forward
ticks is an engineered motor-duration comparison. The policy selects every
action. Relative fixture geometry matches, while absolute spawn poses are
not guaranteed to match across fresh saves. These are fresh executions,
not replays or vanilla-spawn tests.

| Readout | Forward ticks | Three logs | Wooden pickaxe |
| --- | ---: | ---: | ---: |
| Preserved reference | 2 | 1/3 | 1/3 |
| Preserved reference | 5 | 2/3 | 2/3 |
| Positive-progress fit | 2 | 3/3 | 1/2 |
| Positive-progress fit | 5 | 1/2 | 2/2 |
| Progress plus confirmed mining fit | 2 | 3/3 | 3/3 |

The small pilot does not establish an improvement. `development_audit_v2.json`
contains all 21 scored episodes, action counts, elapsed times, descriptive
Wilson intervals, inventory/break/crafting checks and failure modes. The
partially completed cells remain partial. Hardware and wall-budget stops
retain their logs and distinct run identities. No failed scored cell is
silently retried. The latest five-tick partial run sampled RAM as low as
98.7 MiB before the repeated-sample guard shut it down. Minecraft is held
when memory is below the reserve. The new development coordinator waits
for two samples at least 2,400 MiB before launching, with the existing
768 MiB live reserve, 2,048 MiB disk guard and 75-degree GPU cutoff.

## Readout fitting and evidence

`reconstruct_logged.py` reconstructs only the existing policy features from
logged operational observations and neural responses. It verifies every
original action probability vector, action count, outcome and total reward.
For a recorded terminal-control race it uses the actual later terminal
packet from the same episode. No Minecraft action is replayed by this
offline utility. It generates no new expert action labels.

`train_progress_readout.py` fits the existing 66-feature, 12-action linear
softmax readout, using L-BFGS-B weighted behavioral cloning, action-balanced
example weights and a 0.0001 L2 anchor to the original weights. The sparse
139,255-neuron graph and both earlier checkpoints are preserved.

The first fit retained 1,670 positive-reward transitions but only three
mining examples. The live pilot showed that it often declined a legal log
break. Mining reward is usually negative until later pickup, so filtering
only positive transitions underrepresented mining. With
`--confirmed-break-labels`, the corrected fit includes 246 actual successful
`COLLECT_LOG` block-change acknowledgments with minimum example weight 0.1.
Its 1,913 examples do not change the original rewards or outcome labels.
Collection success still requires actual server inventory. Interrupted,
unsuccessful and unconfirmed breaks supply no mining labels. All per-episode
break counts match the archived actor evidence.

| Artifact | SHA-256 |
| --- | --- |
| Original checkpoint | `acdde37f8d3288764bcaad9dc9eea7c4f916c9894f54a019684fc3f555dd37f5` |
| Positive-progress fit | `53491b1d8ad80dd5323a6cda6794c992dd248a4f479a80a57b0e75618941b07c` |
| Corrected mining fit | `0dc48b845f66029cd5c5855e1835713a8c0dd6577b1c4901ffa388e0f34f38a4` |

The new checkpoints are under `checkpoints/phase8/finish_20261123/`.
`progress_readout_training.json` and `mining_readout_training.json` list all
120 source episodes, optimization settings and retained action counts.
`artifact_integrity.json` verifies both embedded fit records, both preserved
checkpoint hashes, the original 139,255-by-139,255 graph, the unchanged live
implementation and checksums of all 189 source log files.
An independent repeat with the committed training utility reconstructed all
120 source episodes again and verified action/acknowledgment alignment. It
produced the exact same NPZ SHA-256 and zero weight difference. The record
is `mining_fit_reproduction.json`. This verifies reproducibility of fitting,
and is separate from live performance evidence.
Loss reduction is training evidence only. On November 24 the corrected
candidate completed its three-layout development pilot with 3/3 per longer
goal. It is selected for a separate fresh held-out evaluation. See
`../phase8_finish_20261124/development_audit.json`. These six development
scores do not establish a reliability or neural-contribution advantage.

Example commands, from the repository with its Python environment:

```powershell
python experiments/phase9/phase8_finish_20261123/train_progress_readout.py --confirmed-break-labels --checkpoint-out NEW.npz --provenance-out NEW.json
python experiments/phase9/phase8_finish_20261123/analyze_development.py --output NEW_AUDIT.json
python experiments/phase9/phase8_finish_20261123/run_mining_development.py --work-dir ABSOLUTE_WORK_PATH --stop-file ABSOLUTE_STOP_PATH
```

Outputs must be new. The coordinator resumes only missing scored cells and
stops if its expected configuration or checkpoint differs. It performs no
training during a live episode. The underlying runner retains process
ownership, isolated disposable worlds and its original operational guards.

## Validation and remaining work

The unchanged baseline passed 118 tests. The final suite passed all 119
tests in 41.625 seconds. The new gradient test uses independent finite
differences with nontrivial legal masks. One OBS cleanup unit test previously
depended on the host's actual free RAM and stopped early during memory
pressure. Its mocked RAM and disk inputs are now deterministic. Separate
tests still verify the live/preflight low-RAM guard and process cleanup.

Both existing accepted milestone MP4s were decoded completely again on
November 23: 869 frames for obstacle recovery and 1,676 for the pickaxe.
Checksums match the November 20 verification. These recordings demonstrate
their original separate executions, and supply no evidence for the newly
trained readouts. See `milestones_reverified_20261123.json` for paths and
playback verification.

Select the candidate only after development. Then freeze its checkpoint
and motor configuration before drawing a fresh held-out seed catalog.
Retest 30 episodes per goal. Gates are at least 24 one-log, 21 three-log,
21 plank and 15 pickaxe successes. Report confidence intervals and the
existing engineered assistance separately from learned readout behavior.
Use matched trained, frozen, uniform, no-neural and shuffled controls before
making any learning or neural-contribution claim. Existing natural-world
controls remain 0/2 each. Once Phase 8 is verified, stop and discuss the
Phase 9 checker with the user.

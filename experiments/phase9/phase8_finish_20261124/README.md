# Phase 8 continuation, November 24

## Complete primary reliability sample

All 120 predeclared scored episodes completed without technical stops:

| Goal | Success | Target | 95% Wilson CI | Median actions | Median wall / game seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| One log | 27/30 | 24/30 | 74.4%–96.5% | 9 | 8.864 / 8.975 |
| Three logs | 27/30 | 21/30 | 74.4%–96.5% | 42 | 35.509 / 35.625 |
| Four planks | 27/30 | 21/30 | 74.4%–96.5% | 9.5 | 10.128 / 10.200 |
| Wooden pickaxe | 19/30 | 15/30 | 45.5%–78.1% | 75.5 | 59.261 / 57.300 |

Medians include failed episodes. Intervals are descriptive, without adjustment
for six shared world seeds or repeated fixture geometry. See `final_results.json`
for every score/failure, `completion_audit.json` for exact reconstruction and
zero evaluation updates, and `artifact_integrity_final.json` for preserved
graph/checkpoints and training-source hashes. Minimum sampled available RAM
was 1,180.34 MiB, maximum GPU temperature 54°C. All guards stayed enabled.

Seed identities are disjoint from development. Geometry is not: 28/30
single-tree trials and 27/30 longer-goal trials reuse development arrangements
(`layout_overlap_final.json`). This establishes controlled held-out-seed
reliability, not unseen-terrain generalization or a neural contribution.
The predeclared control repeats and milestone capture are still being
verified; they remain outside the primary 30-trial denominators.

## Development and frozen protocol

The corrected mining-supervised readout completed all six development cells:
3/3 three-log pickups and 3/3 wooden pickaxes, each from empty inventory.
Median actions were 26 and 39, and median episode wall times were 25.458 and
31.005 seconds, respectively. All successful block changes, recipe actions,
table placements and terminal inventories passed the independent audit.
The descriptive Wilson interval is 43.9%–100% for each three-trial result.
These are development outcomes, not the final 30-trial reliability scores.

The selected checkpoint is
`checkpoints/phase8/finish_20261123/progress_readout_mining.npz`, SHA-256
`0dc48b845f66029cd5c5855e1835713a8c0dd6577b1c4901ffa388e0f34f38a4`.
Forward input remains two ticks, with 15-degree bounded yaw/pitch, the strict
crosshair affordance, 120 policy actions, three prepared trunks and mined-column
memory on longer goals. The policy selects actions. No automatic aiming,
hidden resource coordinates or scripted collection is added.

`freeze_plan.py` freezes the selected checkpoint/configuration and draws six
fresh world seeds with five layout seeds each. Every previously recorded
world/layout seed is excluded. The old 120 pitch episodes and these development
layouts remain outside the new held-out sample. `run_heldout.py` evaluates one
log first, then releases the longer goals at 24/30 verified successes. It
resumes only unscored cells, preserves failed outcomes and technical stops,
and writes all actual scores even if a later target is missed. This is a
bounded Phase 8 evaluation of 120 episodes. It starts no Phase 9 campaign.

Controls are predeclared as trained, frozen Phase 7 transfer, uniform,
no-neural and shuffled-neural on the first three layouts of the first new
seed block, for one-log and pickaxe goals. All receive the selected pitch
interface and the same goal-specific motor settings, budgets and fixtures.
Control repeats stay outside the primary 30-trial goal scores. Report these
small paired samples descriptively and identify engineered assistance.

The first control launch stopped at the RAM guard after one verified trained
one-log success when another Minecraft client consumed available memory.
That scored episode remains in `unpaired_episodes`, outside the matched sample
because its five-condition group was incomplete. A separately identified fresh
execution repeats the incomplete group in a new disposable save. Any fully
completed five-condition group is retained and never repeated. This recovery
rule is independent of the observed success/failure outcome; no scored data
is deleted. Counts include both the paired sample and technical-stop episodes.

The full baseline suite passed 119 tests in 25.684 seconds. The generalized
scorer reproduces all 120 historical episode records and goal summaries
exactly when compared by episode identity. Prior data and the live source
hash remain unchanged. `artifact_integrity.json` verifies the 139,255-neuron
graph and both original checkpoint hashes again.

At the user's request, Microsoft-signed RAMMap 1.63 was downloaded from
Microsoft Sysinternals and launched with administrator approval to run
`-accepteula -Et`, the standby-cache operation. Available RAM measured
1,603 MiB before and 2,293 MiB afterward; this is an observation, not an
attribution of the entire difference to RAMMap. The process finished before
the new scored pilot. Its launch hold stopped attempt `stride2_a1` before
any episode was scored; the successful pilot is distinct attempt `stride2_a2`.

The pre-launch memory margin is now configurable, defaulting to two samples
at 1,800 MiB, based on the measured approximately 750 MiB owned runtime. The
768 MiB live reserve remains unchanged. The successful pilot sampled a
minimum 770.49 MiB available and maximum 52 degrees Celsius GPU temperature.
The disk guard remains 2,048 MiB, GPU cutoff 75 degrees Celsius and server
heap 384 MiB. CPU temperature remains unavailable.

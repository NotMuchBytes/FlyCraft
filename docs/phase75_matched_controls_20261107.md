# Phase 7.5 matched live policy comparison

The fixed plan paired five policies on three previously unused world/layout
seed pairs. Each pair used one disposable Minecraft 26.2 world and five
survival episodes, with the policy order rotated between worlds. The starting
pose, empty inventory and fixture block snapshot matched across all five
conditions within each world. The three trunks started at different offsets
from the actor. These are flat-world near-tree fixtures with distinct seeds
and geometry. The world and item RNG state between episodes was not reset.

Every condition used strict crosshair mining, two-tick forward actions,
bounded 15-degree yaw turns, displacement feedback, and a 400-tick deadline.
The trained and ablated conditions use the same preserved live checkpoint.
The frozen baseline uses the earlier Phase 7 transfer. The uniform baseline
samples the same allowed action set and uses the same engineered goal and
recovery systems. No-neural zeroes the neural activity inputs and retains the
bias. Shuffled applies a fixed permutation to the activity inputs.
Training was disabled in all episodes.

## Results

All fifteen server outcomes agree with the controller's terminal inventory
and goal result. All terminal boundaries were acknowledged and all three
servers exited cleanly. Action counts are medians over successes and failures.
The 95% Wilson intervals are descriptive and wide because each condition has
only three trials.

| Condition | Confirmed logs | 95% interval | Median actions started | Failures |
| --- | ---: | ---: | ---: | --- |
| Trained | 2/3 | 20.8%–93.9% | 12 | One mined without pickup |
| Frozen Phase 7 transfer | 3/3 | 43.9%–100% | 7 | Zero |
| Uniform | 3/3 | 43.9%–100% | 4 | Zero |
| Neural activity removed | 0/3 | 0%–56.1% | 31 | Two never mined, one mined without pickup |
| Neural features shuffled | 1/3 | 6.1%–79.2% | 32 | Two never mined |

The trained failure broke a log and subsequently cycled through turns and
forward actions until the 400-tick deadline. Its 27 action starts include 12
forward actions, 14 yaw turns and one mining action. The drop was selected
as the visible target immediately after mining. After a right turn, the sensor
selected a standing block, and the drop was never selected again that episode.
Frozen and uniform both
collected the log in the same fixture. Removing or shuffling the neural
inputs changed the observed outcomes, but the small sample and the strong
engineered affordances prevent attributing a reliable learning gain or neural
advantage. The prior 27/30 one-log and 21/30 plank results remain separate.
No retention, training benefit or generalization to natural terrain is
established by this batch.

Peak sampled NVIDIA GPU temperature was 54 C and the lowest available RAM
sample was 1,101.12 MiB. The three matched blocks used structured logs.
The plan separately selected a recorded trained repeat of the first fixture.
Both recording attempts stopped before gameplay at the RAM guard, with
minimum samples of 610.93 and 513.45 MiB. Neither produced an MP4. The second
used the later controller-abort accounting fix, with the same policy and
settings. The original matched episode data remain intact. The recording
milestone remains pending.
[First attempt](../recordings/phase9/youtube/p75_controls_recorded_20261107_a.json)
[Retry](../recordings/phase9/youtube/p75_controls_recorded_20261107_b.json)

[Fixed plan](../experiments/phase9/phase75_controls_20261107/plan.json)
[Per-trial results](../experiments/phase9/phase75_controls_20261107/results.json)
[Analysis from preserved raw traces](../experiments/phase9/phase75_controls_20261107/analyze.py)

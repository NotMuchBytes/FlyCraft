# FlyCraft Phase 3 report

## 1. Objective

Build and characterize a deterministic interface from a minimal 2D visual
world through the full structural-connectome simulator to an artificial action
decoder, without learning. The key result is negative but informative: stable
parameters did not carry distinguishable activity to the selected descending
population; repeated closed-loop drive eventually caused runaway recruitment
and a non-useful turning bias.

## 2. Newly available metadata

The new files are `classification.csv.gz` (139,255 unique neurons, complete
coverage) and `consolidated_cell_types.csv.gz` (138,327 unique neurons; 928
metadata neurons absent). Schemas, hashes, overlaps, and distributions are in
`docs/phase3_metadata_report.md`.

## 3. Input and output populations

**DATA FACT:** input candidates are the 9,706-neuron intersection of visual
`family=Photo Receptors` and classification `sub_class=photo_receptor`: 4,955
left and 4,751 right.

**DATA FACT:** outputs are all 1,305 neurons explicitly classified with
`super_class=descending`: 647 left, 650 right, 8 other-side.

**ENGINEERING CHOICE:** each visible condition stimulates a deterministic
50-neuron sector cohort. Exact root IDs are stored in the open-loop JSON.

## 4. Sensor and encoder

The world is a bounded 10x10 arena with agent position, heading, one target,
deterministic reset, and `TURN_LEFT`, `TURN_RIGHT`, `FORWARD`, and `NO_OP`.
The sensor is a transparent five-sector 180-degree angular field. Visible
sectors receive fixed current amplitude 1.05 for a configurable duration.

## 5. Neural model and parameter search

The unchanged Phase 2 vectorized LIF-like simulator used all 139,255 neurons
and 19,773,733 directed aggregate edges. We tested 42 predeclared combinations
covering log1p scales 0.08-0.16, decay 0.0-0.85, and one- to three-step pulses.
Every configuration and all six conditions are retained in
`experiments/phase3/results/open_loop_results.json`.

Best stable setting by maximum propagation without >10% global activation:

| Parameter | Value |
|---|---:|
| transform | log1p |
| scale | 0.08 |
| decay | 0.8 |
| threshold/reset | 1.0 / 0.0 |
| pulse | 1.05 for 3 steps |
| transmitter handling | unsigned |

It produced peak global activity of 51-59 neurons across visible conditions,
so activity spread beyond the 50 directly driven cells. It produced zero
spikes in every selected descending neuron.

## 6. Open-loop discrimination

Conditions were far left, left, center, right, far right, and not visible, each
from identical zero neural state. For the best stable setting:

| Condition | Peak global active | Descending spikes | Unique descending cells |
|---|---:|---:|---:|
| far left | 59 | 0 | 0 |
| left | 54 | 0 | 0 |
| center | 55 | 0 | 0 |
| right | 51 | 0 | 0 |
| far right | 54 | 0 | 0 |
| not visible | 0 | 0 | 0 |

The mean pairwise cosine distance between visible descending-response vectors
was 0.0. A repeated left stimulus reproduced the response exactly.

At scale 0.13 and above, or with stronger accumulated pulses, descending
activity appeared only alongside runaway peaks of roughly 130,000-134,000
active neurons. Those responses were rejected as a usable decoder basis rather
than presented as successful discrimination.

## 7. Controls

- Zero-input/not-visible remained silent in open and closed loop.
- Repeated identical left input was bitwise deterministic at the recorded
  descending temporal-response level.
- Left/right mirrored conditions used equal cohort sizes and identical current.
- All unsuccessful, silent, and runaway grid entries remain in the JSON.

## 8. Output decoder

Raw descending activity was measured before assigning actions. The artificial
decoder maps left/right spike-count difference to same-named turns, balanced
nonzero activity to forward, and zero activity to no-op. This is explicitly an
engineering interface, not decoded fly motor intent.

## 9. Closed loop

Four 20-step episodes used left, center, right, and hidden targets. Each world
step ran six neural steps. Repeated three-step visual drive accumulated in the
recurrent network:

| Episode | Actions | Peak global active | Result |
|---|---|---:|---|
| target left | 17 right, 1 left, 2 no-op | 130,365 | runaway turning bias |
| target center | 17 right, 1 left, 2 no-op | 130,060 | runaway turning bias |
| target right | 18 right, 2 no-op | 129,695 | runaway turning bias |
| target hidden | 20 no-op | 0 | stationary control |

No episode moved forward. The visible episodes rotated in place and left and
center ended with identical state. The repeated left episode reproduced its
trajectory and action sequence exactly. The loop therefore executed
successfully as software, but did not establish stable or useful sensory-motor
behavior.

## 10. Performance

- Open-loop neural rate for the best configuration: approximately 34-51
  steps/s across recorded condition runs.
- Closed loop: 5.80-6.66 world steps/s with six neural steps per world step.
- Closed-loop neural rate: 35.3-40.5 steps/s.
- Peak RSS: 550.21 MiB during open-loop search; 549.54 MiB closed-loop.
- Per 20-step visible episode, sensory encoding took 11.4-16.5 ms total and
  decoding 25.7-30.5 ms total; sparse neural simulation took 2.96-3.40 s.

## 11. Visualizations

- `experiments/phase3/figures/open_loop_output_activity.svg`
- `experiments/phase3/figures/closed_loop_trajectories.svg`

Both are dependency-free scientific SVGs generated from recorded metrics.

## 12. Failures and limitations

- The initial metadata tool invocation lacked the repository root on
  `sys.path`; this was fixed before generating outputs.
- A first stable closed-loop control used the completely silent setting. It was
  superseded by the objectively better stable configuration that propagated
  nine additional local cells; both attempts are recorded in the development
  log.
- The simplified uniform unsigned LIF model exhibits a sharp silence/runaway
  transition. Receptor-specific signs, heterogeneous thresholds, conduction
  delays, and physiological calibration are absent.
- Sector partitions preserve annotated side but are not retinotopic.
- Descending classification supports observation, not the artificial action
  semantics.
- This is not a biologically faithful fly-brain simulation and no learning
  occurred.

## 13. Reproduction

From the project root with the Phase 2 environment:

```powershell
.\.venv\Scripts\python.exe tools\prepare_phase3_metadata.py
.\.venv\Scripts\python.exe experiments\phase3\run_open_loop.py
.\.venv\Scripts\python.exe experiments\phase3\run_closed_loop.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 14. Phase 4 recommendation

The software interface is ready for further research, but the neural model is
not ready for Minecraft or behavior training. Before Phase 4, investigate a
scientifically defensible way to prevent recurrent saturation and transmit
graded information to descending neurons—for example receptor-aware sign data,
cell-class-specific dynamics, or a documented readout from nearer downstream
visual projection populations. Do not tune a decoder to hide the current
failure.

## Phase boundary

Phase 3 is complete. No Minecraft/Fabric integration, reinforcement learning,
rewards, behavior training, or navigation teaching was started.


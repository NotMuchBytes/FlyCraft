# FlyCraft

Local project location: `C:\Users\anass\Documents\FlyCraft` (moved out of OneDrive).

FlyCraft connects published FAFB v783 fruit-fly connectome structure to a small
Minecraft control interface. Phases 1–4 prepare and stabilize a sparse neural
model and bridge it to Minecraft 26.2/Fabric. Phase 5 learns a deliberately
small action readout while leaving the graph and neural dynamics fixed. Phases
6/6.5 exercise that readout in reproducible Minecraft tasks.

Phase 7 adds hierarchical goals, persistent checkpointed memory, bounded
recovery, performance-gated curriculum training and longer-horizon readout
learning. The original 139,255-neuron graph is preserved. See
[`PHASE_7_REPORT.md`](PHASE_7_REPORT.md), the
[design](docs/phase7_design.md) and [commands](docs/phase7_usage.md).
Phase 8 adds acknowledged survival mining, inventory observations, normal
crafting transactions and a live resource-goal controller using the same learned
readout. Real one-log collection and plank crafting have passed development
pilots; the historical assisted one-log comparison scored 29/30 on held-out
reset layouts. Longer goals and the new strict camera interface remain under
evaluation. These controlled tree
fixtures do not establish natural-world autonomy. See the
[observation contract](docs/phase8_observation_contract.md) and
[recorded live-run commands](docs/phase8_usage.md). Phase 7's original results
and checkpoints remain preserved.

The current runner uses bounded camera movement and crosshair-only block
interactions. Read [camera validation](docs/camera_controller.md) before
comparing it with earlier assisted runs. On this Windows laptop, FlyCraft's
dedicated Java runtime uses the NVIDIA RTX 4050, verified by the selected
renderer rather than a preference message; see [GPU evidence](docs/windows_gpu.md).

Phase 9 is an ongoing development pilot with transactional checkpoint/resume,
separate seed sets, a dashboard and Minecraft-only milestone recording. Three
real training episodes have committed readout updates. A matched two-seed,
five-policy comparison establishes no learning or neural benefit. A later strict
one-log evaluation scored 27/30 with fixed two-tick movement; one headless plank
episode passed from an empty inventory. The supplied local actor skin is
installed. The 10,000-world campaign has not started, and broader reliability
targets remain pending. See the
[current report](PHASE_9_REPORT.md) and [architecture](docs/phase9_architecture.md).

A connectome supplies structural connectivity and annotations. It does not by
itself supply exact neuron or synapse dynamics, learning rules, consciousness,
or Minecraft knowledge. Later engineering assumptions must be documented.

## Reproduce Phase 1 analysis

```powershell
python tools/analyze_codex_data.py
```

The program discovers tables by schema, streams compressed CSV data, performs
bounded-memory exact duplicate checks, and writes
`docs/initial_data_report.md`.

## Reproduce Phase 2

Create/activate a virtual environment and install `requirements.txt`, then run:

```powershell
python -m unittest discover -s tests -v
python tools/investigate_missing_neurons.py
python tools/prepare_connectome.py
python experiments/phase2_signal_propagation.py
```

The preparation command creates a deterministic ascending-root-ID index and an
aggregate raw-count CSR matrix in `data/processed/`. The experiment uses 50
deterministically selected visual annotations, runs seven documented stability
configurations, saves complete JSON metrics, writes an SVG plot, and generates
`docs/phase2_report.md`.

The default model uses unsigned connections and a conservative `log1p` weight
transform. These are engineering assumptions, not claims about receptor-level
biology. See `docs/data_semantics.md` for the data/model boundary.

Do not commit or redistribute the source tables until their upstream license
and redistribution terms have been verified.

## Reproduce Phase 3

Phase 3 adds metadata-grounded photoreceptor and descending-neuron populations,
a deterministic five-sector visual sensor, a minimal 2D world, an artificial
output decoder, and reproducible open- and closed-loop experiments.

```powershell
.\.venv\Scripts\python.exe tools\prepare_phase3_metadata.py
.\.venv\Scripts\python.exe experiments\phase3\run_open_loop.py
.\.venv\Scripts\python.exe experiments\phase3\run_closed_loop.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The main result is negative: stable parameters propagated activity locally but
not to the selected descending neurons. Repeated closed-loop drive reached them
only after near-global runaway recruitment, producing a non-useful turning
bias. See `docs/phase3_report.md`. No Minecraft/Fabric integration, learning,
rewards, or behavior training was started.

## Train and evaluate the Phase 5 readout

From the project root in PowerShell:

```powershell
.\.venv\Scripts\python.exe tools\train_phase5.py --episodes 100 --seed 42 --checkpoint checkpoints\phase5\my_seed42.npz --output experiments\phase5\runs\my_seed42.jsonl
.\.venv\Scripts\python.exe tools\evaluate_phase5.py --checkpoint checkpoints\phase5\my_seed42.npz --episodes 200 --seed 10042 --output experiments\phase5\runs\my_seed42_eval.json
.\.venv\Scripts\python.exe tools\train_phase5.py --episodes 100 --checkpoint checkpoints\phase5\my_seed42.npz --resume --output experiments\phase5\runs\my_seed42_resume.jsonl
```

Fresh training and evaluation refuse to overwrite existing artifacts. Resume
restores the checkpoint RNG state and writes a new checkpoint whose name ends
in `_resumed_to_N.npz`.

See `docs/phase5_report.md` for the deterministic learning evidence and
`docs/phase6_report.md` for the matched live Minecraft evaluation. Graphs are
under `docs/figures/`; raw metrics and logs remain under `experiments/`.

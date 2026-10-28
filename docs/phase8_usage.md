# Phase 8 live trials

Python's existing virtual environment, cached Fabric/Gradle dependencies and
the original graph/checkpoints are required. No new Python packages are added.

Read [the observation contract](phase8_observation_contract.md) first. The
server mod is required for explicit block and own-inventory acknowledgments.
The disposable harness uses survival mode and never opens a saved player world.

## Background recording

Load `tools/obs_recording.lua` in a dedicated OBS collection containing exactly
one Window Capture source named `Minecraft only`. Use exact Minecraft title
matching, remove desktop/microphone audio sources, and set the recording output
directory. Configure the script's saved `command_file` and `state_file` settings
to `<control-dir>/obs-command.txt` and `<control-dir>/obs-state.txt`. These are
local files; a websocket server and global hotkeys are unnecessary. OBS's
[frontend API](https://docs.obsproject.com/reference-frontend-api) supplies the
recording start, stop and active status operations.

Set the capture's bounding-box type to **Scale to inner bounds**, with bounds
1920 by 1080 and no crop. This fits both small and maximized Minecraft windows
without changing the desktop window. The script saves an output screenshot
after recording starts so framing can be verified independently of its source.

The current machine has a separate `FlyCraft Background` collection/profile
already configured. OBS may remain in the tray. Minecraft remains a rendered,
unfocused window; minimizing its window can break window capture. The runner
starts new disposable clients with focus hints disabled. The script stops its
own recording if supervisor heartbeats disappear for 60 seconds.

Run from the repository root (paths below are placeholders):

```powershell
.\.venv\Scripts\python.exe tools/run_phase8_live.py --run-id unique_run --work-dir C:/scratch/live-runs --build-dir C:/scratch/mod-build --checkpoint checkpoints/phase8/live_train01/trial_0005.npz --frozen-checkpoint checkpoints/phase7/curriculum_v3_seed29.npz --goals one_log --conditions trained,frozen,uniform,no_neural --trials 10 --world-seed 82000 --layout-start 82000 --seconds 850 --trial-ticks 300 --obs-control-dir C:/scratch/obs-control
```

Run identities and output paths must be new. At most 30 trials per goal/condition
and 900 seconds per invocation are allowed. Supervise runs; do not leave them
overnight. The supervisor samples NVIDIA GPU temperature and stops at 75 C.
It does not have a CPU temperature sensor. Recording must be confirmed before
the trial gate opens, and loss of confirmation aborts the suite. Each run's
`run.json` records the resulting video path. Raw server scores, controller
decisions and launcher/game logs are preserved under `experiments/phase8/`.

Use `--train` only for an explicitly separated development set. Checkpoints
are written to a new run-specific directory; earlier checkpoints are retained.
Evaluation conditions never update policy weights. The `frozen` condition uses
the explicit Phase 7 checkpoint, and uniform sampling uses the same affordance
mask and engineered planner as the trained agent.

## Camera and NVIDIA graphics

New runs use the bounded camera and crosshair-only interactions. Use explicit
`--camera-mode legacy` to reproduce the historical assisted Phase 8 interface;
those results must remain separate. `--camera-mode instant` is the strict
single-write actuator reference for matched camera comparisons. Controller
limits, command semantics and initial live evidence are in
[camera_controller.md](camera_controller.md).

On the current hybrid AMD/NVIDIA laptop, FlyCraft's dedicated Java executable
has a per-application Windows **High performance** GPU preference. The runner
defaults to OpenGL and waits for the actual device log to identify NVIDIA
before starting any trials. A preferred-device message alone is insufficient.
An AMD selection aborts the suite. `--graphics-backend vulkan` remains available,
but Vulkan on NVIDIA still reproduced an AMD driver fault during shutdown on
this machine. The subsequent NVIDIA OpenGL run closed normally; see
[windows_gpu.md](windows_gpu.md) for the evidence and scope of the setting.

The supervisor reserves 768 MiB of available system RAM by default and aborts
after three consecutive low-memory samples. Gradle launch heaps are capped at
512 MiB each. GPU temperature and the minimum sampled available RAM are saved
in `run.json`. These are sampled system measurements, not CPU temperature or
proof of thermal safety between samples.

```powershell
.\.venv\Scripts\python.exe tools/analyze_phase8.py --runs unique_run --output experiments/phase8/unique_summary.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Scores come from actual server inventory, independently of controller claims.
Incomplete suites are explicitly identified; never count missing trials as
successful. Wilson intervals describe controlled fixture trials, not natural
Minecraft generalization. Repeated development layouts and training episodes
must be excluded from held-out comparisons.

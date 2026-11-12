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

Use new run identities and output paths. Each invocation allows up to 30 trials
per goal/condition and 900 seconds. The supervisor samples NVIDIA GPU
temperature and stops at 75 °C. CPU temperature is unavailable on this laptop.
Recorded runs require OBS confirmation before the trial gate opens and stop if
confirmation is lost. The `run.json` records the video path. The experiment
folder retains the server scores, controller decisions and launcher/game logs.

Use `--train` only for an explicitly separated development set. Checkpoints
are written to a new run-specific directory; earlier checkpoints are retained.
Evaluation conditions never update policy weights. The `frozen` condition uses
the explicit Phase 7 checkpoint, and uniform sampling uses the same affordance
mask and engineered planner as the trained agent.

Use `--headless --goals three_logs --three-tree-fixture` for the controlled
multi-tree goal. Three separate trunks make logs reachable at eye height
with the existing yaw-only action set. The server records each initial
fixture and requires three logs in inventory. The flag applies only to
the three-log and wooden-pickaxe goals and defaults off. The wooden-pickaxe
version starts with empty inventory and includes a stone face for horizontal
table placement.

The headless `pickaxe_transaction` diagnostic supplies planks, sticks and
a reachable workbench. Add `--unplaced-table-fixture` to start with an
owned workbench and a visible support face so the policy must place it
first. Keep these diagnostics separate from `wooden_pickaxe` trials.
For a fixed evaluation plan, `--layout-seeds` takes one distinct signed
64-bit seed per `--trials` slot. Every goal and condition in that slot
uses the same layout seed.

For routine scored episodes, use the headless server with structured logs.
For milestone footage, use `--headless --spectator --milestone 1` with the
dedicated OBS control folder. The spectator client records the actor without
supplying any policy observations. Record fresh repeats under new run IDs and
keep their scores outside the original sample.

The [fixed long-goal plan](../experiments/phase9/phase8_completion_bench_20261108/plan.json)
records the exact checkpoint hash, world/layout seeds and controller settings.
Use `--goals three_logs,wooden_pickaxe --three-tree-fixture --remember-mined-columns
--policy-seed 9001 --forward-ticks 2 --trial-ticks 1500` for its two-goal blocks.
The [scorer](../experiments/phase9/phase8_completion_bench_20261108/analyze.py)
uses the corresponding local run and episode logs. Register interrupted
layout subsets in `retries.json` and keep their original run records.

The one-shot `--headless --operator-fault server_restart` diagnostic stops
the runner-owned Minecraft server during a mining action. It reopens the
same disposable save with a fresh episode identity and keeps the Python
bridge running. Use one evaluation trial with learning disabled. Add the
usual spectator and OBS flags to capture both attempts. The recorder
rechecks the Minecraft window after the spectator relaunches, before the
replacement episode starts.

`--operator-fault server_crash` uses the same recovery path after forcibly
terminating the owned server process. It requires a disposable save with
existing level metadata and a nonzero exit from the interrupted process.

Use `--headless --natural-world --goals one_log --trials 1` for a vanilla
overworld spawn. Supply one world seed per invocation and use
`--layout-start` to seed the initial heading. The runner clears the
actor's starting inventory and leaves the terrain as generated. Report
these runs separately from the flat-fixture benchmark.
Add `--jump-on-blocked-forward` to test an opt-in vanilla jump pulse on
grounded forward retries. It requires displacement feedback and applies
only when the policy selects consecutive forward actions after a block.

## Camera and NVIDIA graphics

Add `--headless --pitch-actions` to enable the experimental 12-action
readout. Legacy checkpoints transfer their 63-by-10 weights into its
66-by-12 matrix. The new weights start at zero. New pitch checkpoints
use a distinct schema and require the flag to resume. Match this flag
across policy conditions when comparing learned and uniform behavior.

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

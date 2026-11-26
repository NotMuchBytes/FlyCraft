# FlyCraft

FlyCraft connects a **139,255-neuron fruit-fly connectome** to a small learned action readout and an experimental Minecraft controller. It runs locally. The neural graph stays fixed while the action readout learns.

Start with the Python demo below. Full-network inference and real Minecraft require the additional data and Java setup.

**Active development: [`phase8-real-minecraft`](https://github.com/NotMuchBytes/FlyCraft/tree/phase8-real-minecraft).** The commands below clone this branch. GitHub's `main` branch contains an older code snapshot.

## What works today?

- Python training and evaluation with saved checkpoints and reproducible seeds.
- Real survival mining, inventory-confirmed pickups, planks, sticks, crafting tables and wooden pickaxes in controlled Minecraft scenes.
- Policy-selected movement and camera actions, crosshair-only mining, episode logs and interrupted-action handling.

The planner, semantic sensors, legal-action masks and crafting transactions are engineered components. Reliable exploration and collection in natural terrain remain under development. The optional companion's follow mode uses engineered navigation.

Broader training has started with policy-selected jumping and terrain exploration, while retaining the wood tasks. The original 338-world foundation is preserved. Stone tools, food, combat and later progression still need their own validated interfaces; they are not trained skills yet. See the [staged curriculum and live evidence](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase9_staged_curriculum.md).

## 1. Quick start: Python demo

These commands were tested on **Windows PowerShell with Python 3.14.7**. Install [Git](https://git-scm.com/downloads) and a **64-bit Python 3.14** release from the [Python 3.14 download page](https://www.python.org/downloads/release/python-31410/), then open PowerShell where you want the project:

```powershell
git clone --depth 1 --branch phase8-real-minecraft https://github.com/NotMuchBytes/FlyCraft.git
cd FlyCraft
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use the virtual environment's Python directly as shown. Activation and changes to PowerShell's execution policy are unnecessary. Run the remaining commands from the `FlyCraft` repository root.

### Check the installation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_learning.py -v
```

These tests use the neural-feature table included in the repository. Minecraft and the large source dataset are unnecessary for this demo.

### Train and evaluate your first readout

```powershell
.\.venv\Scripts\python.exe tools/train_phase5.py --episodes 100 --seed 42 --checkpoint checkpoints/phase5/first_run.npz --output work/first_run_train.jsonl
.\.venv\Scripts\python.exe tools/evaluate_phase5.py --checkpoint checkpoints/phase5/first_run.npz --episodes 200 --seed 10042 --output work/first_run_eval.json
```

The console prints a summary. Your checkpoint is under `checkpoints/phase5/`, and detailed results are under `work/`. This demo is a small 2D simulator using cached features measured from the neural model.

Commands refuse to overwrite existing artifacts. Choose new filenames for another fresh run. To continue training the same readout:

```powershell
.\.venv\Scripts\python.exe tools/train_phase5.py --episodes 100 --checkpoint checkpoints/phase5/first_run.npz --resume --output work/first_run_resume.jsonl
```

Resume restores the saved RNG state and writes a new checkpoint ending in `_resumed_to_N.npz`. See the [Phase 5 report](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase5_report.md).

## 2. Prepare the full connectome

Skip this section for the demo. Full-network inference and Minecraft control require source data and a generated graph, which are not included in a clone.

Obtain the **FAFB v783** exports from [FlyWire Codex](https://codex.flywire.ai/fafb), following the publisher's access and usage terms. Save these five files in `data/` and keep them compressed:

```text
data/
  neurons.csv.gz
  connections_princeton_no_threshold.csv.gz
  visual_neuron_types.csv.gz
  classification.csv.gz
  consolidated_cell_types.csv.gz
```

Use `connections_princeton_no_threshold.csv.gz`; the smaller filtered `connections.csv.gz` is a different input. The five exports total about 267 MiB compressed. [Data details and source location](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/data/README.md) document the expected files. Download directly from the publisher rather than committing source data to this repository.

Prepare the generated graph and interface:

```powershell
.\.venv\Scripts\python.exe tools/prepare_connectome.py
.\.venv\Scripts\python.exe tools/prepare_phase3_metadata.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Preparation writes `data/processed/`, including the 139,255-by-139,255 sparse graph, neuron index and interface metadata. It validates expected neuron/connection counts and leaves the compressed exports unchanged. Some tests require optional local Java, OBS or FFmpeg tools and are skipped when those tools are absent.

Read [data semantics](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/data_semantics.md) for biological assumptions, filtering and matrix orientation.

## 3. Run a real Minecraft test

The standard development target is **Minecraft 26.2**, **Java JDK 25**, Fabric Loader **0.19.5** and Fabric API **0.161.0+26.2**, pinned in [`minecraft_mod/gradle.properties`](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/minecraft_mod/gradle.properties). The current supervised launcher uses Windows executable paths. Complete sections 1 and 2 first.

### Prepare Java and game dependencies

1. Download a Windows x64 **JDK 25 ZIP**, for example from [Eclipse Temurin](https://adoptium.net/temurin/releases/?version=25&os=windows&arch=x64). Extract its contents into `.runtime/jdk-25/`. Both `.runtime/jdk-25/bin/java.exe` and `bin/javac.exe` must exist there.
2. Read and agree to the [Minecraft EULA](https://www.minecraft.net/en-us/eula) before using the local server harness. It writes acceptance into its disposable server folder.
3. Build the mod and fetch dependencies once with an internet connection:

```powershell
$env:JAVA_HOME = (Resolve-Path ".runtime/jdk-25").Path
$modBuildDirectory = Join-Path (Get-Location) ".runtime/mod-build"
Push-Location minecraft_mod
& "$env:JAVA_HOME/bin/java.exe" -Xmx64m -classpath gradle/wrapper/gradle-wrapper.jar org.gradle.wrapper.GradleWrapperMain --no-daemon --max-workers=2 "-PflycraftBuildDir=$modBuildDirectory" assemble downloadAssets
Pop-Location
```

The wrapper supplies Gradle. The live runner subsequently uses offline launch preparation, so the initial download matters. Leave several GiB of RAM free and room for Java/Minecraft caches and run logs.

### Start one headless collection attempt

This creates a disposable survival world with a prepared tree. The actor selects its own actions. A spectator window and OBS are unnecessary for this event-log test.

```powershell
.\.venv\Scripts\python.exe tools/run_phase8_live.py `
  --run-id my_first_one_log `
  --work-dir .runtime/live `
  --build-dir .runtime/mod-build `
  --checkpoint checkpoints/phase8/finish_20261123/progress_readout_mining.npz `
  --headless --pitch-actions `
  --goals one_log --trials 1 `
  --world-seed 2026112401 --layout-start 30101 `
  --policy-seed 9001 --forward-ticks 2 `
  --trial-ticks 400 --seconds 180 --server-heap-mib 384
```

This experimental checkpoint is included on the development branch. It met all four controlled reliability point targets in the evaluation below; an individual attempt may fail. Use a new `--run-id` for each fresh attempt. Existing player worlds are not used.

Look in `experiments/phase9/my_first_one_log/` for `run.json`, `server.jsonl`, `controller.jsonl` and bridge/action logs. That historical output folder also contains Phase 8 tests; it does not start the Phase 9 campaign. Success requires the item in the actual server inventory.

The supervisor keeps a **768 MiB available-RAM reserve**, **2 GiB free-disk reserve** and **75°C NVIDIA GPU cutoff** when that telemetry is available. Guard stops are recorded in `run.json`. Free resources and start a fresh attempt rather than reducing the live reserve.

For longer goals, comparisons, recovery diagnostics and Minecraft-only OBS recording, follow the [live-trial guide](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase8_usage.md). The [observation/action contract](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase8_observation_contract.md) explains policy inputs and interface assistance.

## Current results — November 24, 2026

The selected pitch-enabled readout completed a frozen **30 live trials per goal**, each from empty inventory:

| Goal, from empty inventory | Confirmed successes | Target |
| --- | ---: | ---: |
| One log | 27/30 (90%) | 24/30 |
| Three logs | 27/30 (90%) | 21/30 |
| Four planks | 27/30 (90%) | 21/30 |
| Wooden pickaxe | 19/30 (63.3%) | 15/30 |

All four point targets are met. The descriptive 95% Wilson intervals are 74.4%–96.5% for the three 27/30 results and 45.5%–78.1% for pickaxes. They do not adjust for shared worlds/fixtures. All results have matching terminal inventory and block/crafting acknowledgments, with zero evaluation weight updates. The original sparse brain and earlier checkpoints remain unchanged.

These are controlled flat-world fixtures. The earlier evaluation (26/30 one-log, 18/30 three-log, 27/30 planks, 12/30 pickaxes) is now training/development data for this readout and is excluded from the new scores. New seed identities are separate from development, but the small fixture generator repeats block arrangements: 28/30 single-tree trials and 27/30 longer-goal trials reuse development geometry. These scores test held-out-seed reliability and establish no natural-terrain reliability, unseen-layout generalization or neural contribution.

**Phase 8 controlled validation is complete.** All 30 matched control repeats and the selected-readout milestone are verified. In the small Phase 8 controls, trained and shuffled-neural tied, so those tests established no neural advantage.

**Phase 9 is in progress.** The original 338-world foundation is preserved. Its first broader stage added 64 training worlds and 270 evaluation trials. Terrain collection scored trained 25/30, frozen 19/30, uniform 4/30, no-neural 0/30 and shuffled 11/30. Wood retention scored one-log 20/30, three-log 30/30, planks 25/30 and pickaxe 29/30. The one-log retention gate failed, so the candidate did not advance. These controlled fixtures establish no natural-terrain or unseen-layout reliability.

On November 26 a bounded 32-world retention repair began from the same checkpoint, with fresh evaluation seeds and unchanged targets. Its first training trial succeeded in six actions; repaired reliability is not yet measured. **180 tests pass.** Windows sign-in auto-resume and a hidden restart watchdog are installed on the development PC; two crash tests recovered the same runner in about 16 seconds without replaying actions. Pre-login boot registration was denied by Windows permissions. [Automatic resume, repair protocol and limits](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase9_auto_resume.md), [Phase 7.5 report](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/PHASE_7_5_REPORT.md), [Phase 8 report](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/PHASE_8_REPORT.md).

The new [checked development supervisor](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase9_checker.md) verifies actual episode evidence, manages bounded resource recovery and writes a Codex fix request when investigation is needed. It passed nine functional live trials, including a fresh hardened-version smoke check, with stop/resume recovery and two verified readout updates. These small development trials estimate no reliability or learning gain. It cannot patch code. The [official campaign executor](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase9_official_campaign.md) requires separate explicit authorization, freezes 10,000 training seeds and records scheduled milestones. The final 100-world evaluation stays untouched. Standalone runs save local handoffs; they do not wake an idle Codex chat. See the [verified launch and host-operation limits](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/experiments/phase9/fc9_20261125_operations/README.md).

## More ways to explore

| You want to… | Start here |
| --- | --- |
| Understand goals, memory and checkpoints | [Phase 7 design](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase7_design.md) and [commands](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase7_usage.md) |
| Inspect camera and movement behavior | [Camera validation](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/camera_controller.md) and [movement validation](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/movement_validation.md) |
| Play alongside the NPC | [Minecraft 26.3 companion preview](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/companion_play.md) and [validation limits](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/companion_follow_validation.md) |
| Run checked development batches | [Checker setup, recovery and Codex handoffs](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase9_checker.md) |
| Reproduce earlier neural experiments | [Phase 2](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase2_report.md), [Phase 3](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase3_report.md) and [Phase 3.5](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/docs/phase35_report.md) |
| Read historical campaign tooling | [Phase 9 report](https://github.com/NotMuchBytes/FlyCraft/blob/phase8-real-minecraft/PHASE_9_REPORT.md) |

The companion has separate version/build instructions. Its engineered follow mode and interactive demonstrations remain separate from autonomous scores. The connectome supplies structural connectivity and annotations; the project documents its additional neural dynamics and control assumptions.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `py` is not recognized | Install Python 3.14 with its Windows launcher, or use that installation's full `python.exe` path to create `.venv`. |
| Missing Python module | Install requirements using `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. |
| Missing data or `data/processed` | Complete section 2. A clone includes demo features, not the full dataset. |
| Graph count/schema mismatch | Check FAFB v783 filenames and the unthresholded connection table. Keep validation checks enabled. |
| `java.exe` missing | Check `.runtime/jdk-25/bin/java.exe`; an extra nested JDK ZIP folder is a common cause. |
| Offline Gradle dependency error | Complete the online build/download step in section 3 first. |
| Windows reports a locked build directory | Use the separate `.runtime/mod-build` path shown above and let any earlier build finish. |
| Output already exists | Choose a fresh name, or use explicit training `--resume`. |
| Port 25567 or 8765 occupied | Let the existing FlyCraft run finish or stop your own previous test before launching another. |
| Resource guard stops a test | Read `run.json`, free resources and preserve the interrupted logs. |

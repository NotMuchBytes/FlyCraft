# Run Phase 7

Use the existing project root and Python environment. No new Python package
or GPU runtime is required.

## Train and resume

```powershell
.\.venv\Scripts\python.exe tools\train_phase7.py --episodes 1200 --seed 29 --initial-phase65 checkpoints\phase5\followup_2000ep\seed_29_trained_final.npz --learning-rate 0.05 --checkpoint checkpoints\phase7\my_run.npz --output experiments\phase7\my_run.jsonl
.\.venv\Scripts\python.exe tools\train_phase7.py --episodes 100 --resume checkpoints\phase7\my_run.npz --checkpoint checkpoints\phase7\my_resumed_run.npz --output experiments\phase7\my_resumed_run.jsonl
```

Fresh artifacts are required. Periodic checkpoints are saved every evaluation
interval. Training stops after the requested episodes or the default
180-second wall budget. `--goal wooden_pickaxe` selects focused training;
otherwise advancement depends on held-out curriculum evaluations. Resume uses
the checkpoint's RNG and training configuration. Do not reuse final test seeds
for training or promotion decisions.

## Evaluate and verify

```powershell
.\.venv\Scripts\python.exe tools\evaluate_phase7.py --checkpoint checkpoints\phase7\curriculum_v3_seed29.npz --phase65 checkpoints\phase5\followup_2000ep\seed_29_trained_final.npz --episodes 100 --ablations --output experiments\phase7\my_evaluation.json
.\.venv\Scripts\python.exe tools\validate_phase7_brain.py --output experiments\phase7\my_brain_validation.json --workers 3
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`evaluate_phase7.py` writes raw rollouts and summaries. The full-network check
recomputes and repeats all six observation windows and verifies the graph
checksum and exact cache equality. Simulated completion rates cannot be
reported as live Minecraft completion rates.

## Live navigation

Build the updated Fabric client and connect to a disposable local test world:

```powershell
.\.venv\Scripts\python.exe minecraft_bridge.py --autonomy-checkpoint checkpoints\phase7\curriculum_v3_seed29.npz --goal navigate_object --save-autonomy-state checkpoints\phase7\my_live_state.npz --log experiments\phase7\my_live_bridge.jsonl
```

Only navigation is supported in live autonomy mode. The client recognizes a
gold-block marker through the existing ray sensor. A terminal goal stays
stopped for that client world session. Start a new service/client session to
attempt a fresh goal. Old `--checkpoint` and `--untrained-policy` modes still
accept the legacy client protocol.

The Fabric build accepts optional `-PflycraftBuildDir=...` and
`-PflycraftRunDir=...` arguments for generated files outside OneDrive. Use
separate fresh runtime folders for smoke tests. Placing
`flycraft-phase7.enabled` in a disposable server runtime enables one marker
scene; do not enable scene-writing harnesses in an existing player world.
`-PflycraftAutotest` enables quick join, and `-PflycraftServer=127.0.0.1:25566`
overrides its default address. Quote property arguments in PowerShell; invoking
the Gradle wrapper through Java avoids batch-argument parsing issues.

See `PHASE_7_REPORT.md` for recorded outcomes and known limitations.

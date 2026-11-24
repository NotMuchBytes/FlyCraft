# Checked development supervisor

The supervisor runs bounded real-Minecraft development batches and asks Codex
to investigate problems. It does not implement or authorize the 10,000-world
campaign. Valid policy failures remain scored; the checker cannot patch code,
change success rules, aim the actor or select its actions.

## What runs locally

`autonomy/evidence.py` independently joins the server scores, initial inventory,
controller outcome, acknowledged terminal boundary, issued commands and actual
actor acknowledgments. It checks inventory-based goals, actual log block
changes, recipe/table placement evidence, action/tick budgets, the five neural
conditions and zero evaluation updates. It rejects duplicate identities and
contradictory evidence. Required milestone videos receive checksum, complete
decode and independent game/capture-frame checks. This is evidence validation,
not an LLM deciding whether a success looks plausible.

`tools/supervise_phase9.py` uses the existing transactional coordinator. It waits
for two resource-ready samples, runs one owned worker at a time, commits only
verified checkpoint updates and writes a local Codex fix request when needed.
It supports the pitch-enabled one-log, three-log, four-plank and wooden-pickaxe
interfaces. Longer goals use the same prepared three-tree fixture and
mined-column memory as Phase 8. This supplies no natural-terrain claim.

The Codex agent is the AI reviewer/fixer. During a Codex-managed batch it reads
the supervisor's attention result and investigates the preserved evidence.
`fix_request.json` and `attention/request_NNNN.md` are also usable as standalone
handoffs. A standalone Python process does **not** wake an idle Codex chat;
there is no external AI service, API charge or automatic messaging integration.

## Initialize a new checked development campaign

Use a fresh name. Run from the repository root after the Minecraft/data setup:

```powershell
.\.venv\Scripts\python.exe tools/run_phase9.py init `
  --name checked_demo --checked --compact --goal wooden_pickaxe `
  --checkpoint checkpoints/phase8/finish_20261123/progress_readout_mining.npz `
  --frozen-checkpoint checkpoints/phase7/curriculum_v3_seed29.npz `
  --forward-ticks 2 --worlds 5 --master-seed 202611240901 `
  --recording-policy milestones --recording-milestones 1
```

This freezes configuration, source, graph and checkpoint hashes. The seed
catalog excludes previously recorded world/layout IDs and separates pilot,
training-reserve, development evaluation and final evaluation partitions.
Creating reserved seed IDs generates no worlds. This supervisor never accesses
the training-reserve or final-evaluation partitions.

```powershell
.\.venv\Scripts\python.exe tools/supervise_phase9.py run `
  --campaign experiments/phase9/checked_demo --split eval_a `
  --max-attempts 2 --seconds 900 `
  --work-dir C:/path/to/work --build-dir .runtime/build_reply_loss_20261107 `
  --obs-control-dir C:/path/to/obs-control --video-export-dir C:/path/to/outputs
```

Use the actual prepared build and OBS control paths on your computer. Evaluation
is the default and cannot update weights. `--split pilot` explicitly runs
development training and saves new readouts after verification. Original input
checkpoints and the connectome are never overwritten. Do not pool these pilots
with the completed Phase 8 benchmark.

## Decisions and recovery

- A verified success or ordinary policy failure commits once and moves on.
- A resource/wall interruption with no score may retry at most twice, using a
  fresh attempt/world and the same planned seed. Both the generated instances
  and interruptions count. A verified score just before a technical exit is
  retained and is not repeated.
- RAM must be at least 1,800 MiB on two samples 30 seconds apart to launch.
  Disk must exceed the 2,048 MiB reserve and measured GPU temperature must be
  below 75°C. Worker live guards retain 768 MiB RAM, 2,048 MiB disk and 75°C GPU.
  Missing GPU/CPU temperature telemetry is disclosed, never invented.
- Contradictory evidence, changed source/checkpoints, a third consecutive
  technical interruption or at least nine failures in ten trained-condition
  episodes pauses the batch and writes a Codex fix request. Those verified
  failures remain in the ledger. Frozen/uniform/ablation controls do not trigger
  the trained-policy failure-rate rule.
- A changed implementation requires a new frozen development campaign. The
  checker cannot erase a fix request, thaw configuration or silently revise
  the benchmark. Resume from a reviewed preserved checkpoint in a fresh plan
  after a behavioral/code repair.

The outer batch allows at most 100 worker launches and one hour. The campaign
allows at most 100 generated development worlds across all conditions/splits,
including interrupted worlds. These bounds do not implement official training.
No previous user-set Codex usage cap is applied.

Create the campaign's `STOP` file or use `tools/run_phase9.py stop --campaign
PATH` to stop. `clear-stop` archives the request before a later resume. The
owner lease prevents overlapping workers. A user stop never requests a code fix.
The derived `dashboard.html`, `supervisor.json`, `state.json` and `checks/` show
actual results and checkpoint state.

## Milestone capture

Routine episodes have event logs only. Scheduled milestones start an owned OBS
instance hidden/minimized with the existing **FlyCraft Background** profile and
collection. It must contain only one exact-title Minecraft window capture and
no desktop/audio sources. An unowned OBS instance is left untouched and blocks
automatic capture. The spectator's actual NVIDIA renderer and matching game/
capture frames must pass before the policy starts. First-person spectator
capture does not feed observations to the actor.

Empty stale OBS session markers are reversibly archived only while OBS is
absent. The owned recorder is stopped only after recording-stop confirmation;
all footage, failed attempts, logs and marker backups remain preserved. A video
with a valid failed policy episode is still a failed episode, never a selected
success or an exact replay. Manual review remains useful for milestone quality;
the automatic pixel comparison/full decode does not replace scientific review.

## Re-audit archived runs without playing Minecraft

```powershell
.\.venv\Scripts\python.exe tools/supervise_phase9.py audit `
  --runs experiments/phase9/p8_mining_20261124_pickaxe_milestone `
  --output work/new_evidence_audit.json
```

The output must be new. This reads historical manifests against their own
frozen source hashes, preserves all originals and starts no game or training.
Source/checkpoint changes in a live campaign remain prohibited.

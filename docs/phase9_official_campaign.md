# Authorized Phase 9 campaign — 25 November 2026

The user explicitly instructed **“start the 10000”**, later requested milestone
recording and a temporary shutdown guard. This authorizes the official training
campaign. Its launch and actual counters are recorded separately from this plan.
Earlier reports stating that authorization was pending are historical.

## Frozen design

- Exactly **10,000 Minecraft-created training world instances**, using distinct
  training-partition seeds and a fixed repeating schedule: one log, three logs,
  four planks, wooden pickaxe. This allocates 2,500 world slots per goal.
- An interrupted or partially initialized world consumes its seed and slot,
  earns no invented score and never reuses that world seed. A prelaunch failure
  without a Minecraft world consumes an attempt ID but no world slot.
- Start from the validated Phase 8 readout
  `checkpoints/phase8/finish_20261123/progress_readout_mining.npz`, SHA256
  `0dc48b845f66029cd5c5855e1835713a8c0dd6577b1c4901ffa388e0f34f38a4`.
  The original graph and all previous checkpoints remain untouched. Only the
  existing action readout learns; the 139,255-neuron sparse graph is fixed.
- The policy chooses actions through the validated pitch interface: bounded
  15-degree camera steps, 2-tick forward input, 120-action ceiling, and 400
  trial ticks for one log/planks or 1,500 for three logs/pickaxe. The 384/512 MiB
  server/client compact profile uses an 854×480 spectator source. OBS exports
  its existing 1920×1080 canvas.
- These are **prepared controlled worlds**, with semantic rays, legal masks,
  recipe transactions and reward shaping. The longer goals use the validated
  three-tree fixture and mined-column memory. These are engineered assistance,
  not learned discovery. No hidden tree positions, automatic aiming, scripted
  collection or new actor behavior is introduced by this launcher.
- Development pilot, training, evaluation A and evaluation B seed partitions
  are disjoint and exclude archived world/layout IDs. This executor accesses
  only training seeds. The final 100 evaluation seeds remain unused until a
  separate frozen evaluation plan; no final evaluation starts automatically.
- At the world budget, freeze the last committed checkpoint and stop training.
  Training scores do not establish held-out reliability or neural advantage.

## Recording and unattended limits

Milestones are **1, 2, 3, 4, 10, 25, 50, 100, 250, 500, 1,000, 2,500, 5,000,
7,500 and 10,000**. The first four show all four goals. OBS captures only the
exact Minecraft spectator window, without desktop/audio. The actual NVIDIA
renderer and independent frame match are required before actions start.
Recordings are full-decoded, checked for episode coverage and SHA256-bound to
their evidence. Files use `FlyCraft_Phase9_Milestone_...mp4`. A failed capture
preserves the raw logs and pauses for review; a later repeat is a fresh attempt,
never an exact replay. Milestone worlds and footage remain preserved.

Routine episodes use structured logs without a spectator/OBS. Only their
independently verified disposable `server/world` directories are reclaimed.
Exact resolved boundaries and link/junction checks precede recursive deletion.
Logs, saved readouts, historical records and unverified worlds are retained.

Launch requires two healthy samples 30 seconds apart: 1,800 MiB RAM for routine
worlds and 3,000 MiB for recordings, plus 2,048 MiB disk and GPU below 75°C.
The existing live 768 MiB RAM, 2,048 MiB disk and 75°C GPU guards remain active.
CPU temperature is unavailable. Known technical interruptions allow at most
two consecutive retries. Contradictory evidence, source/checkpoint changes,
or nine failures in ten trained episodes writes an attention request and stops.

The long executor runs checked batches of at most 100 launches/one hour, with
300 seconds per worker. It never clears STOP, edits code or silently changes a
frozen plan. Standalone attention does not wake an idle Codex chat. No previous
user-set Codex usage cap is applied.

The [temporary power guard](power_guard.md) blocks ordinary shutdown and idle
sleep; unplugged at 5% it requests STOP and releases the block. Forced shutdown
and physical power loss remain possible. It changes no permanent power setting.

## Commands

The official initializer requires an explicit authorization record. Do not use
the sample as evidence of authorization for another user's machine.

```powershell
.venv/Scripts/python.exe tools/run_official_phase9.py init --name fc9_20261125 --checkpoint checkpoints/phase8/finish_20261123/progress_readout_mining.npz --frozen-checkpoint checkpoints/phase7/curriculum_v3_seed29.npz --authorization "start the 10000" --authorized-date 2026-11-25 --master-seed 202611250901 --compact
.venv/Scripts/python.exe tools/run_official_phase9.py run --campaign experiments/phase9/fc9_20261125 --work-dir C:/path/to/work --build-dir .runtime/build_reply_loss_20261107 --obs-control-dir C:/path/to/obs-control --video-export-dir C:/path/to/outputs
```

Use the actual prepared local paths. Launch the executor hidden for background
operation. `state.json`, `summary.json`, `supervisor.json`, `checks/` and
`dashboard.html` contain actual progress. Creating the campaign's `STOP` file
requests safe interruption and preserves the last committed readout.

Validation before launch: **145 automated tests passed**. New synthetic tests
exercise authorization, unique-world accounting across interruption, disjoint
seed partitions, the 10,000th-world boundary, worker/manifest mismatches, cleanup
boundaries, milestone retention and STOP persistence. They are not live scores.

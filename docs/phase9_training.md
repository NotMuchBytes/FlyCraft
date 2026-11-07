# Phase 9 pilot operation

The serial development coordinator is `tools/run_phase9.py`; official training
is disabled. Each invocation permits at most five episodes and 900 seconds,
with at most 300 seconds per worker. Do not start overnight or extended
unattended training. Stop new development around 55% weekly usage, with a 60%
maximum; obtain actual account measurements.

Development reliability checks can use the live worker's
`--operator-fault mining_interrupt` or `--operator-fault bridge_stall` with one
headless episode and learning disabled. Add `--spectator --milestone 1` and the
usual isolated OBS paths for a recorded check. The former issues one disruptive
+90-degree yaw command after mining starts; the latter pauses/resumes the owned
Python process tree for six seconds while Minecraft continues. These are
operator test inputs, never learned actions or ordinary success-rate data.
A [recorded retry](phase75_rejection_recovery_20261106.md) recovered from a
delayed response and confirmed a log in inventory. Full disconnect and live
checkpoint restoration still require validation before expanding training.

From the repository root, use the existing runner with `--headless` to omit
the agent's graphical client. `--spectator --milestone 1` adds mandatory
verified-window OBS capture for a single development episode. Supply a fresh
`--run-id`, existing `--checkpoint`, external `--work-dir` and `--build-dir`,
and an OBS `--obs-control-dir`. Use `--graphics-backend opengl` on this laptop.
The observed working memory limits are `--server-heap-mib 512
--client-heap-mib 768 --capture-width 1280 --capture-height 720`.

Use `python tools/run_phase8_live.py --help` for all supported options. Run IDs
must not overwrite earlier artifacts. `--redo-of` is provenance, not replay.
Without `--train` the readout remains frozen. The runner's capability to save a
trained episode does not establish that a Phase 9 training campaign ran.

Preserve raw JSONL, operator initial fixture snapshots, control/ack files,
source manifests, immutable checkpoint hashes, launcher logs and recordings.
Runtime and data assets remain local and ignored by Git. Generated world
counts in per-run metadata describe that run only. The development coordinator
aggregates generated instances, seeds, committed episodes and updates with
transactional resume. Official experiment counters have not been started.

## Coordinator commands

Initialize a fresh, frozen development configuration:

```powershell
.\.venv\Scripts\python.exe tools\run_phase9.py init --name my_dev_pilot --checkpoint checkpoints\phase9\headless_learning_pilot_01\trial_0000.npz --worlds 3 --master-seed 2026102902 --compact
```

The optional compact profile fixes 384/512 MiB server/spectator heaps and 854x480
source capture. Both profiles retain RAM and temperature guards. Heap limits
do not replace the need for enough free system RAM.

Run or resume with explicit workspace and recording paths:

```powershell
.\.venv\Scripts\python.exe tools\run_phase9.py run --campaign experiments\phase9\my_dev_pilot --max-episodes 1 --seconds 300 --work-dir C:\path\to\work\phase8-runs --build-dir C:\path\to\work\phase8-build --obs-control-dir C:\path\to\work --video-export-dir C:\path\to\outputs
```

New campaigns record only scheduled milestones, as requested by the user.
Use `init --recording-policy milestones` (the default), with optional
`--recording-milestones 1,10,25,30` for a final 30-trial challenge. Only those
episodes receive a spectator and verified MP4; routine episodes retain logs
without a graphical client. OBS must run with the isolated FlyCraft collection
and file control script for milestones. Legacy campaigns keep their all-episode
requirement. No desktop input or focus automation is used.

Open the campaign's `dashboard.html` for a refreshing view, or use `status
--campaign ...` for JSON. Neural features and probabilities come from actual
bridge decisions; bias is labeled and fixed dynamics are distinguished from
learned readout parameters. Throughput is measured; remaining time is estimated.

Use `stop --campaign ...` to request safe interruption. Use `clear-stop
--campaign ...` explicitly before resuming; the old request is archived. Worker
ownership checks also stop the game if the coordinator disappears. A failed
attempt stops that invocation. Resume commits fully completed evidence once or
preserves the interruption before using a fresh attempt identity and checkpoint.

Use `init --goal one_log` (default) or `init --goal planks` for the two
implemented interaction goals. This is an explicit operator selection, not
automatic curriculum promotion. Planks require actual inventory planks >= 4,
not just a collected log; other headless crafting goals remain disabled.
The repeated plank validation runs with learning off. It does not establish
plank-training improvements. A checkpoint advances after actual game
outcomes, acknowledged inventory, model integrity and scheduled recording checks agree.
Passive terminal rewards are logged separately and suppress learning when they
cannot be assigned safely. This is a conservative accounting fix, not a new
learning algorithm or evidence of improved generalization.

For matched development comparisons, use `run --split eval_a` and one condition:
`trained`, `frozen`, `uniform`, `no_neural` or `shuffled`. Learning is disabled.
Set A is reused per selected checkpoint and remains development data. The
`freeze-final` command fixes the selected policy and blocks further training;
only then can `--split eval_b` use final seeds. Each condition gets one pass.
Do not choose policies or tune hyperparameters from final benchmark results.

Behavior/config changes require a new campaign. One idle evaluation received
an archived result-validation-only amendment after a missing terminal field;
see the architecture and report for its strict scope and provenance. No policy,
actor, runner, runtime limit or seed changed. Seed catalogs and checkpoints are
hashed, and interrupted generated instances remain counted. Creating the reserved
10,000 training seeds does not generate those worlds or authorize a full run.

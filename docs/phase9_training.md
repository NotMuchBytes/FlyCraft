# Phase 9 pilot operation

The serial development coordinator is `tools/run_phase9.py`; official training
is disabled. Each invocation permits at most five episodes and 900 seconds,
with at most 300 seconds per worker. Do not start overnight or extended
unattended training. Stop new development around 55% weekly usage, with a 60%
maximum; obtain actual account measurements.

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

Every development episode receives a separate spectator and verified MP4. OBS
must already run with the isolated FlyCraft collection and file control script.
The server-only agent itself does not require a graphical client. No desktop
input or focus automation is used.

Open the campaign's `dashboard.html` for a refreshing view, or use `status
--campaign ...` for JSON. Neural features and probabilities come from actual
bridge decisions; bias is labeled and fixed dynamics are distinguished from
learned readout parameters. Throughput is measured; remaining time is estimated.

Use `stop --campaign ...` to request safe interruption. Use `clear-stop
--campaign ...` explicitly before resuming; the old request is archived. Worker
ownership checks also stop the game if the coordinator disappears. A failed
attempt stops that invocation. Resume commits fully completed evidence once or
preserves the interruption before using a fresh attempt identity and checkpoint.

Only one-log training is enabled. A checkpoint advances after actual game
outcomes, acknowledged inventory, model integrity and recording checks agree.
Passive terminal rewards are logged separately and suppress learning when they
cannot be assigned safely. This is a conservative accounting fix, not a new
learning algorithm or evidence of improved generalization.

For matched development comparisons, use `run --split eval_a` and one condition:
`trained`, `frozen`, `uniform`, `no_neural` or `shuffled`. Learning is disabled.
Set A is reused per selected checkpoint and remains development data. The
`freeze-final` command fixes the selected policy and blocks further training;
only then can `--split eval_b` use final seeds. Each condition gets one pass.
Do not choose policies or tune hyperparameters from final benchmark results.

Config/code changes require a new campaign. Seed catalogs and checkpoints are
hashed, and interrupted generated instances remain counted. Creating the reserved
10,000 training seeds does not generate those worlds or authorize a full run.

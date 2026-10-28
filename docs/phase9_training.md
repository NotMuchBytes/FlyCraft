# Phase 9 pilot operation

The current implementation is a bounded single-world worker. It does not yet
implement the requested 10,000-world scheduler. Do not start extended or
overnight training. Stop new development at approximately 55% weekly Codex
usage, with a 60% maximum; use actual account telemetry.

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
counts in per-run metadata describe that run only; official cumulative counters
and transactional resume have not yet been implemented.

Before an official launch, implement and verify seed separation, checkpoint
commit/recovery, manual stop, benchmark isolation, worker throughput/resource
measurement and milestone video recovery. Freeze the experiment configuration,
review a small development pilot, then obtain explicit full-run authorization.

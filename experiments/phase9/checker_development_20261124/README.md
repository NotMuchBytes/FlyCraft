# Phase 9 checker development — November 24

## Frozen live pilot

The eight declared scored episodes all succeeded: two one-log evaluations,
one three-log pickup, one plank craft, one recorded wooden pickaxe, one
stop/resume collection and two plank-training episodes. This small functional
pilot estimates no reliability rate or learning gain. Two new readout updates
were independently verified before advancing the checkpoint chain. There were
nine disposable generated worlds, including the unscored interrupted world.

The interrupted mining command had no successful acknowledgment. Its episode
was not scored, and the resumed fresh attempt used a different run/world
identity. All original brain/checkpoint hashes remain unchanged. Only
coordination, evidence checking and recorder lifecycle source changed; the
actor, neural dynamics, feature interface and Minecraft actions are unchanged.
See `pilot_plan.json`, `pilot_results.json` and `pilot_audit.json`.

The preselected pickaxe milestone succeeded in 89 actions, 67.737 controller
wall seconds and 67.9 game seconds. Its Minecraft-only RTX 4050 MP4 passed full
decoding over 82.833 seconds and manual frame review. Mining, dropped logs and
the placed crafting table are visible; the spectator HUD does not display
actor inventory, which is verified from server/actor evidence. Original
loading/menu frames and tutorial overlays remain unedited.

After the frozen pilot, corrupted-copy regression tests exposed two reporting
edge cases: a null update object escaped as TypeError, and failed video
validation did not retain the separately verified game outcome in the ledger.
Both are repaired without changing gameplay. Pre-fix test failures are
preserved. All 136 tests pass on the hardened checker; a fresh frozen smoke
trial follows separately. Historical pilot source/configuration is not thawed.

## Protocol and provenance

This is bounded checker/supervisor validation, outside the Phase 8 benchmark
and outside the unapproved 10,000-world campaign. The original baseline passed
119 tests in 16.419 seconds before edits. The candidate passes 134 tests in
16.976 seconds, including deliberate evidence corruption and checkpoint gating.

The independent checker re-audits the 24 archived November 24 run bundles:
152 scored episodes, 116 actual successes and 6,183 unique decision commands.
All 120 primary Phase 8 outcomes remain unchanged. These are preserved old
episodes, not newly executed Minecraft trials. Archived milestone playback is
also checked. See `archived_audit.json` and the final stricter re-audit.

`run_pilot.py` freezes the actual source manifest and declares eight new scored
development episodes: two one-log evaluations in separate supervisor
invocations, one three-log, one plank, one recorded pickaxe, one stop/resume
diagnostic, and two plank-training attempts. Only the two explicit training
episodes may change newly saved readouts. Original graph/checkpoints stay fixed.
The planned source and development seeds freeze before any live attempt.

The stop diagnostic requests STOP after observing a real mining start. It
changes no actor action. A fresh attempt resumes only if no valid score was
produced; valid failures are never retried. This is not a benchmark or exact
world replay. The pickaxe recording is preselected regardless of outcome.

The local evidence gate owns validity decisions. It writes `fix_request.json`
and a Markdown handoff for Codex when investigation is needed. It cannot patch
source, edit benchmarks or authorize official training. A standalone process
does not wake an idle chat; a Codex-managed run receives the attention result.
No extra AI service or usage charge is configured.

See [checker operation](../../../docs/phase9_checker.md) for the exact rules,
resource/ownership bounds, milestone capture and remaining limitations.

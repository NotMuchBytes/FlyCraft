# Phase 9 checker development — November 24

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

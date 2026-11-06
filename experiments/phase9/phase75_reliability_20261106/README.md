# November 6 reliability evidence

See `docs/phase75_reliability_20261106.md` for results and the unresolved
stale-command rejection acknowledgment defect. Phase 7.5 is not complete.

- `summary.json`: trace-derived results, fault validation and visual-review limits.
- `packet_regression.json`: identical injected protocol checks against old/current
  controllers; not Minecraft gameplay.
- `verification.json`: regression/build/preservation checks and actual usage snapshot.
- `analyze.py`: regenerates the summary from preserved local per-run JSONL/metadata.
- `record_visual_review.py`: one-time metadata assessment; intentionally refuses
  to overwrite an existing review backup. MP4 and gameplay logs are untouched.

Raw local logs/MP4s/worlds are ignored by Git. Every attempt keeps its own
source manifest, run metadata and recording mapping. The bridge-stall `a`
attempt is excluded as a fault test because only a launcher was paused. The
`b` retry genuinely paused the owned process tree and failed goal recovery.
Its playable video has partial visual coverage due to a game menu. Original
automated metadata is preserved in `*.pre_visual_review.json` alongside the
amended disclosure. Neither the partial footage nor the failed goal is a pass.

All six generated instances reuse one seed, with four scored episodes and no
new training updates. No population success rate, learning gain or causal
neural contribution is inferred.

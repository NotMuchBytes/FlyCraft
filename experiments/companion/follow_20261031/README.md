# Interactive companion evidence

- `analysis.json`: descriptive measurements from the retained real-game trace.
- `validation_original.json`: original recording supervisor outcome, including
  its failed stop-acknowledgment stage; intentionally not relabeled as a pass.
- `source_manifest.json`: source hashes frozen before the live recording.
- `verification_20261105.json`: later regression, packaging and preservation checks.

The MP4 and raw session logs remain local rather than being committed as large
binary artifacts. Their locations/checksums and the distinction between observed
following and incomplete recovery testing are documented in
`docs/companion_follow_validation.md`. This is engineered companion assistance,
not a learned-policy or resource-collection evaluation.

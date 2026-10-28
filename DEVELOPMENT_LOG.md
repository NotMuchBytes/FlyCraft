# FlyCraft Development Log

This log is append-only for meaningful project work. Failures and uncertainties
are retained.

## 2026-09-20T22:20:29+03:00 — Phase 1 data inspection

**TASK**

Inventory and move available Codex exports, inspect their schemas, and run the initial bounded-memory analysis.

**WHAT WE TRIED**

- Verified the requested profile path, resolved the actual Desktop, inspected gzip headers and sample rows, and moved only schema-confirmed files.
- Streamed the graph and used 128 temporary disk partitions for exact duplicate and unique-pair counts.

**FILES MOVED**

| Filename | Bytes | Original location | New location |
| --- | --- | --- | --- |
| connections_princeton_no_threshold.csv.gz | 275,679,780 | C:\Users\anass\Downloads\connections_princeton_no_threshold.csv.gz | C:\Users\anass\OneDrive\Desktop\FlyCraft\data\connections_princeton_no_threshold.csv.gz |
| neurons.csv.gz | 1,679,884 | C:\Users\anass\Downloads\neurons.csv.gz | C:\Users\anass\OneDrive\Desktop\FlyCraft\data\neurons.csv.gz |
| visual_neuron_types.csv.gz | 631,701 | C:\Users\anass\Downloads\visual_neuron_types.csv.gz | C:\Users\anass\OneDrive\Desktop\FlyCraft\data\visual_neuron_types.csv.gz |

**RESULT**

- Neurons: 139,116; records: 22,285,323; unique directed pairs: 19,773,733; total `syn_count`: 76,944,499.
- Malformed rows: 0; exact duplicate excess rows: 0.

**ERRORS**

- `C:\Users\Hamzah` was absent. A first read-only PowerShell path check had a parser error and changed no files.
- Cell Types and Classification / Hierarchical Annotations exports were absent.
- The first analyzer run's Windows RAM probe returned zero because the native handle signature was not declared. The probe was fixed and the full analysis was rerun report-only; counts matched exactly.

**WHAT WORKED**

- Three files moved with identical byte sizes; the analyzer completed and wrote the initial report.

**WHAT FAILED**

- Classification-based sensory and descending-neuron selection was impossible with the current files.

**ASSUMPTIONS**

- Dataset identity comes from the brief; `syn_count` is reported as aggregate connection weight; the OS-resolved Desktop substitutes for the nonexistent requested profile path.

**PERFORMANCE**

- Verified rerun end-to-end time: 171.006 seconds; peak observed working set: 272.06 MiB.

**NEXT STEP**

Stop after Phase 1. Locate the missing exports, review this report, and wait for explicit Phase 2 approval.

## 2026-09-21T07:17:19+0300 — Phase 2 connectome preparation and first propagation

**TASK**

Build and test an efficient first structural-connectome simulator; no behavior, Minecraft, or learning.

**WHAT WE TRIED**

- Verified official data semantics; investigated graph-absent metadata neurons; built an all-neuron CSR graph; ran synthetic tests and five unsigned propagation configurations.

**RESULT**

- 139,255 neurons, 19,773,733 aggregated directed edges, total raw `syn_count` 76,944,499. Plot: `docs\figures\phase2_activity_vs_timestep.svg`.
- log1p scale 0.01: peak 50, unique 50, 53.75 steps/s.
- log1p scale 0.03: peak 50, unique 50, 56.33 steps/s.
- log1p scale 0.1: peak 50, unique 50, 53.70 steps/s.
- log1p scale 0.3: peak 136,694, unique 137,919, 50.75 steps/s.
- log1p scale 1.0: peak 138,631, unique 138,792, 52.22 steps/s.

**ERRORS**

- The first synthetic reset test used `decay=0` while expecting subthreshold accumulation. It failed correctly; the test was fixed to `decay=1` and then passed.
- The first full experiment completed its numerical runs but Matplotlib's `_backend_agg` DLL was blocked by Windows Application Control. Plotting was replaced with dependency-free SVG and the experiment was rerun.
- During the final read-only integrity pass, an initial checker referenced `ConnectomeGraph.matrix` instead of the actual `adjacency_raw` field, and a log-tail command used the wrong filename casing/name. Both commands failed without modifying data; the corrected checks were then run.
- One read-only metrics-validation command used Unix heredoc syntax in PowerShell and failed before execution; it changed no files and was rerun with a PowerShell here-string.

**WHAT WORKED**

- Synthetic propagation tests passed; graph counts matched Phase 1; zero-input baselines were silent; full-connectome sparse matvec propagation completed.

**WHAT FAILED**

- Reliable descending/output selection remains blocked by missing Cell Types and Classification exports.

**ASSUMPTIONS**

- All metadata neurons retained; neuropil rows summed per pair; unsigned transmitter model; dimensionless uniform LIF-like dynamics; log1p numerical weights.

**PERFORMANCE**

- Graph build: 101.696 s, peak RSS 516.39 MiB. Simulation results are detailed in `docs/phase2_report.md`.

**NEXT STEP**

Stop at the Phase 2 boundary and await explicit approval. Do not start Minecraft, behavior, or learning.

## 2026-10-02 — Phases 5, 5.5, 6, and 6.5

**RESULT**

- Added episodic REINFORCE for a 4-by-4 action readout over fixed connectome-derived features; graph weights and neural dynamics remain unchanged.
- The preserved 400-episode attempt failed its success-rate gate. The single registered 2,000-episode follow-up passed: 55.50% trained versus 1.17% baseline success and 67.24% lower mean final distance.
- Added atomic checkpoint save/load, exact seeded resume, JSONL logs, and train/evaluate CLIs.
- Added three configurable Minecraft task levels and ran matched untrained/trained suites in Minecraft 26.2 through the real Fabric bridge.
- Live trained performance was 4/9 successes versus 2/9 baseline; both the Phase 6 operational gate and Phase 6.5 improvement gate passed.
- Generated `phase5_learning_validation` and `phase65_minecraft_evaluation` PNG/SVG graphs. All raw failures were retained.

**LIMITATIONS**

- Shuffled features retained 26% success, showing a substantial forward-action prior.
- The trained policy is not safe when no target is visible and still timed out in 5/9 Minecraft scenarios.
- The nine-scenario live result is evidence of a working integration, not robust autonomous Minecraft behavior.

**PHASE BOUNDARY**

Phases 5 through 6.5 are complete. Phase 7 was not started.

## 2026-09-21 â€” Phase 3 sensory/motor interface and 2D closed loop

**TASK**

Use the new annotations to build a deterministic artificial visual interface,
observe descending activity, run open-loop discrimination, and characterize a
closed loop without learning.

**FILES CREATED OR MODIFIED**

- Added `interface/`, `environment/`, Phase 3 experiment scripts and tests.
- Generated population CSV/NPZ/JSON artifacts under `data/processed/`.
- Generated open- and closed-loop JSON results and dependency-free SVG figures.
- Added `docs/phase3_metadata_report.md`,
  `docs/interface_population_selection.md`, and `docs/phase3_report.md`.

**DATA AND SELECTION DECISIONS**

- Input candidates: 9,706 neurons satisfying visual
  `family=Photo Receptors` and classification `sub_class=photo_receptor`.
- Output candidates: all 1,305 neurons with classification
  `super_class=descending`.
- Sector and action mappings preserve annotated side where possible but are
  engineering choices, not biological motor interpretations.

**EXPERIMENTS**

- Tested 42 fixed combinations spanning log1p scale 0.08-0.16, decay 0-0.85,
  and one- to three-step pulses across five visible and one zero-input condition.
- Best stable setting: scale 0.08, decay 0.8, threshold 1.0, amplitude 1.05,
  duration 3. It peaked at 51-59 active cells but produced zero descending spikes.
- Settings that reached descending neurons recruited roughly 130,000-134,000
  neurons and were classified as runaway.
- Four closed-loop episodes executed. Repeated visible drive became runaway and
  produced mostly `TURN_RIGHT`; the hidden control remained 20/20 `NO_OP`.
  A repeated left episode reproduced exactly.

**FAILURES AND CORRECTIONS**

- The first metadata-tool run failed because the repository root was not on
  `sys.path`; the script was corrected and rerun successfully.
- The first closed-loop control used a completely silent stable setting. The
  criterion was corrected to prefer maximum non-runaway spread, and the
  experiment was rerun with scale 0.08 / decay 0.8 / three-step input.
- Stable descending discrimination was not achieved. This result was retained
  rather than masked through decoder tuning.
- During handoff, the workspace junction was rejected as a reparse point and
  two initial direct `apply_patch` invocations used the wrong argument form.
  The patch was then applied from the project directory correctly.

**PERFORMANCE**

- Best-setting open-loop neural rate: approximately 34-51 steps/s.
- Closed-loop rate: 5.80-6.66 world steps/s with six neural steps each.
- Peak RSS: approximately 550.21 MiB open loop and 549.54 MiB closed loop.

**PHASE BOUNDARY**

Phase 3 is complete. No Minecraft/Fabric work, reinforcement learning, rewards,
behavior training, or navigation teaching was started.

## 2026-09-21 — Downloaded missing annotation exports

**TASK**

Download the Cell Types and Classification / Hierarchical Annotation exports that were missing during Phase 2.

**RESULT**

- Downloaded official FAFB v783 `classification.csv.gz` (934,402 bytes, 139,255 rows) and `consolidated_cell_types.csv.gz` (901,707 bytes, 138,327 rows) into `data/`.
- Verified gzip/CSV readability, expected schemas, row counts, and SHA-256 hashes. Exact hashes and source URL are recorded in `data/README.md`.

**ERRORS**

- PowerShell `Invoke-WebRequest` failed during TLS receive, and Windows `curl` could not acquire Schannel credentials. Python `urllib` reached the same official static-data endpoint and completed both downloads successfully.

**PHASE BOUNDARY**

The new annotation files were not integrated into the completed Phase 2 experiment. No Phase 3 work was started.

## 2026-09-21T07:19:46+0300 — Phase 2 final stability rerun

**TASK**

Build and test an efficient first structural-connectome simulator; no behavior, Minecraft, or learning.

**WHAT WE TRIED**

- Verified official data semantics; investigated graph-absent metadata neurons; built an all-neuron CSR graph; ran synthetic tests and seven unsigned propagation configurations.

**RESULT**

- 139,255 neurons, 19,773,733 aggregated directed edges, total raw `syn_count` 76,944,499. Plot: `docs\figures\phase2_activity_vs_timestep.svg`.
- log1p scale 0.01, decay 0.9: peak 50, unique 50, 56.22 steps/s.
- log1p scale 0.03, decay 0.9: peak 50, unique 50, 61.14 steps/s.
- log1p scale 0.1, decay 0.9: peak 50, unique 50, 62.17 steps/s.
- log1p scale 0.12, decay 0.0: peak 50, unique 51, 60.96 steps/s.
- log1p scale 0.12, decay 0.9: peak 132,489, unique 136,948, 61.05 steps/s.
- log1p scale 0.3, decay 0.9: peak 136,694, unique 137,919, 56.83 steps/s.
- log1p scale 1.0, decay 0.9: peak 138,631, unique 138,792, 61.52 steps/s.

**ERRORS**

- The first synthetic reset test used `decay=0` while expecting subthreshold accumulation. It failed correctly; the test was fixed to `decay=1` and then passed.
- The first full experiment completed its numerical runs but Matplotlib's `_backend_agg` DLL was blocked by Windows Application Control. Plotting was replaced with dependency-free SVG and the experiment was rerun.

**WHAT WORKED**

- Synthetic propagation tests passed; graph counts matched Phase 1; zero-input baselines were silent; full-connectome sparse matvec propagation completed.

**WHAT FAILED**

- Reliable descending/output selection remains blocked by missing Cell Types and Classification exports.

**ASSUMPTIONS**

- All metadata neurons retained; neuropil rows summed per pair; unsigned transmitter model; dimensionless uniform LIF-like dynamics; log1p numerical weights.

**PERFORMANCE**

- Graph build: 101.696 s, peak RSS 516.39 MiB. Simulation results are detailed in `docs/phase2_report.md`.

**NEXT STEP**

Stop at the Phase 2 boundary and await explicit approval. Do not start Minecraft, behavior, or learning.

## 2026-10-27 — Phase 7 autonomy and project relocation

**IMPLEMENTED**

- Added goal dependencies/priorities, recipe planning, bounded persistent memory,
  learned goal-conditioned action selection, curriculum and autonomous recovery.
- Extended the existing readout to 63x10 weights; preserved the 139,255-neuron
  graph and Fabric bridge. Added exact mid-action and CLI checkpoint resume.
- Added a resource/recipe extension of World2D and optional live navigation.

**VERIFICATION**

- Baseline: 23/23 tests passed. Final: 45/45, including after relocation.
- Full-network cache windows and complete repeated activity states matched
  exactly; graph checksum unchanged. Offline Fabric build passed after moving.
- Three final 1,200-episode runs; 3,599/3,600 nonzero policy updates.
- Held-out simulated pickaxe completion: 160/300 (53.33%); not reliable at
  the 70% criterion. Easier goals improved over frozen transferred policies.
- Corrected live navigation passed after eight neural-policy actions, with
  server-measured distance 1.437 blocks and zero bridge/stale-response errors.

**FAILURES RETAINED**

- Early runs exposed resource invalidation/replanning, surplus-production reward
  farming and a subgoal-credit counting issue. Logs/checkpoints remain.
- First live navigation stopped at 1.848 blocks because ray-hit and center
  distances differed. Fixed the completion contract and retained the failed run.
- OneDrive blocked a build-directory cleanup and a log reopen. External build
  output and a persistent log handle resolved those failures.
- Recovery and neural-feature ablations show substantial action-prior/context
  effects; reliable autonomous Minecraft crafting has not been demonstrated.

**USER-REQUESTED MOVE**

- Moved the complete project from OneDrive Desktop to
  `C:\Users\anass\Documents\FlyCraft`.
- All 231 data/checkpoint files (348,041,570 bytes) matched pre-move SHA-256
  hashes. Repointed the old workspace junction while retaining its previous
  link; repaired venv activation and nine existing console launchers.
- Python, pip, all tests and the Fabric build work in Documents. Test processes
  were stopped. No existing checkpoint was overwritten and nothing was pushed.

Detailed evidence and Phase 8 recommendations: `PHASE_7_REPORT.md`.

## Phase 8 implementation and evaluation in progress — 2026-10-28

- Created private `NotMuchBytes/FlyCraft` on GitHub and published the preserved
  Phase 7 baseline followed by the Phase 8 implementation on main and
  `phase8-real-minecraft`.
- Added acknowledged survival mining, separate dropped-log pickup, actual
  own-inventory observations, normal crafting/placement transactions, bounded
  failures and live learned-policy goal sessions. No graph or prior checkpoint
  was overwritten. Details: `docs/phase8_observation_contract.md`.
- One-log and plank development pilots passed. Three-log and pickaxe pilots
  still failed; the 30-trial completion gates are not yet established.
- Added Minecraft-only OBS file control, recording-confirmed trial gates,
  unfocused client startup and bounded recording supervision. Preserved setup
  errors and partial batches; fixed stale crafting inventory, frame cropping,
  Windows sharing races and cleanup after recorder failure.
- 60 tests pass. A rerun of 1,800 Phase 7 simulation episodes exactly reproduces
  baseline deterministic metrics across three preserved checkpoints. The
  original graph SHA-256 is unchanged.
- Bounded matched live comparisons are underway. Full Phase 8 results remain
  pending; see `PHASE_8_REPORT.md`. The user queued Phase 7.5 stabilization
  after this Phase 8 iteration, preserving all successful real interactions.

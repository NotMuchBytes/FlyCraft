# Phase 9 progress snapshot: first 274 worlds

25 November 2026. Training continues in the original frozen campaign. This
snapshot is **274/10,000 world slots (2.74%)**, not campaign completion.
The independent read-only re-audit reproduced all **274 scores**, with
**238 successes**, no changed evidence and no checkpoint-chain discrepancies.
All **149 automated tests passed** in 20.749 seconds.

| Training goal | Successes | Rate | Mean actions | Mean game seconds | Mean worker wall seconds |
|---|---:|---:|---:|---:|---:|
| One log | 66/69 | 95.7% | 10.81 | 8.96 | 35.47 |
| Three logs | 59/69 | 85.5% | 40.04 | 32.66 | 59.12 |
| Four planks | 65/68 | 95.6% | 11.88 | 9.39 | 34.87 |
| Wooden pickaxe | 48/68 | 70.6% | 66.35 | 49.04 | 75.05 |

Means include successes and failures. These are **adaptive training outcomes**,
not held-out reliability estimates or evidence of a neural/learning advantage.
No binomial confidence interval is presented as a fixed-policy reliability
interval. The separate final evaluation remains untouched. Engineered fixtures,
semantic sensors, recipe transactions, legal masks and mined-column memory
remain exactly as disclosed in the [frozen design](../../../docs/phase9_official_campaign.md).

Failures remain scored: one-log had two break/pickup failures and one without a
confirmed break; three-log had ten break/pickup failures; planks had two without
a confirmed break and one break/pickup failure. The 20 pickaxe failures stopped
after sticks (14), crafting a table (4), or planks (2). Nothing was re-aimed,
replayed, rescored, or selected into a different result.

There were **254 verified readout updates**. The remaining 20 episodes
suppressed training with `unexecuted_terminal_command`; the saved checkpoint
chain correctly retained its preceding weights. Original graph, initial/frozen
checkpoints and the implementation hash remain unchanged:
`90a18f3f4e206b93115dfd6458a9fef5aa31255f2b40e6f81955bd3d6108c1b7`.
The snapshot checkpoint is world 273, SHA256
`4dbc287e3072a8bc082c82e728dcfe52865b2f1c2773f9772f94225f252e0d74`.

All nine milestone MP4s (1, 2, 3, 4, 10, 25, 50, 100, 250) passed another full
decode, hash and episode-coverage audit. The five newer milestone samples were
also inspected manually at 60% of their original duration: Minecraft-only
first-person footage, normal tutorial overlays, no screensaver/desktop capture.
Milestone 250 visibly shows the block breaking. All five newer recorded goals
succeeded; the previously recorded failed pickaxe remains preserved.
The MP4s and worlds have not been edited or rerun for this audit.

Exactly **265 verified routine world directories** were reclaimed; all nine
milestone worlds, episode logs and saved readouts remain available. Across this
snapshot, minimum sampled available RAM was **2,245.23 MiB** and maximum GPU
temperature **57°C**. CPU temperature is unavailable. Original RAM/disk/thermal
guards, normal-shutdown block, critical-battery release and the completion-only
shutdown companion remain enabled. The HP fan service update still requires a
reboot and has not been applied during training.

The first 274 attempts took **6.375 hours**, including readiness waits: about
**42.98 worlds/hour**. The dashboard's worker-only throughput excludes those
waits and therefore should not be treated as the total campaign rate. Continuing
the observed inclusive rate would require roughly **9.4 more days**; resources,
interruptions and policy behavior can change this estimate.

[Machine-readable audit, all episode checks and video paths](progress_00274.json).
The audit script was run outside frozen runtime source and changed no live
campaign files. The next scheduled recording is world 500.

# Phase 6 Minecraft task protocol

Phase 6 evaluates the Phase 5 policy through the existing Fabric-to-Python neural bridge. The Minecraft harness may reset the player, place the target, measure outcomes, and end an episode. It never selects an action. Every action is sampled from the same learned readout policy used in Phase 5.

## Locked evaluation protocol

- Policy mode: stochastic for both baseline and trained conditions.
- Bridge RNG seed: `9001` for both conditions.
- Trained checkpoint: `checkpoints/phase5/followup_2000ep/seed_29_trained_final.npz`.
- Baseline: a fresh zero-weight `LinearSoftmaxPolicy` (uniform action probabilities).
- Decision interval: 10 Minecraft ticks.
- Target observation: one of five ray-cast sectors; no distance or world coordinates are sent to the policy.
- Conditions are run in separate clean Minecraft/Fabric processes over the same nine scenario definitions.

## Tasks

| Task | Scenarios | Success | Timeout | Purpose |
|---|---:|---|---:|---|
| `T1_ORIENT` | bearings -40, +40, -20 degrees at distance 7 | absolute target yaw error <= 10 degrees | 8 decisions | single-skill orientation |
| `T2_APPROACH` | bearings 0, -20, +20 at distances 4.5, 5, 5.5 | target distance <= 1.6 blocks | 18 decisions | repeated navigation decisions |
| `T3_GENERALIZE` | bearings -40, +40, 0 at distances 6, 7, 8 | target distance <= 1.6 blocks | 20 decisions | held-out start combinations |

The outcome reward is distance progress plus `0.20 * angular improvement in radians`, with `+3` on success. It is used only for evaluation here; no online learning occurs during Phase 6.

## Pass criteria fixed before the live run

Phase 6 is operational if all nine episodes complete, actions are supplied by the neural policy bridge without stale-response or bridge errors, and the trained agent succeeds in at least one scenario from each task level. Phase 6.5 demonstrates improvement if trained success rate exceeds baseline success rate and trained mean reward exceeds baseline mean reward on these same scenarios. Raw logs and unsuccessful episodes are retained.

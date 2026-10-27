# Phase 6 and 6.5 report

## Live Minecraft result

Phase 6 and Phase 6.5 are complete under the locked protocol in `docs/phase6_tasks.md`. Two fresh Minecraft 26.2/Fabric runs executed the same nine server-defined scenarios. The Fabric client sent only a five-sector ray-cast observation to the Python service. Every action was sampled by either the untrained or trained policy; the server only reset scenes and measured outcomes.

| Condition | Successes | Success rate | Mean reward | Median reward | Timeouts |
|---|---:|---:|---:|---:|---:|
| Untrained | 2 / 9 | 22.22% | 3.336 | 2.988 | 7 |
| Trained | 4 / 9 | 44.44% | 3.544 | 3.011 | 5 |

Trained success by task was 1/3 orientation, 2/3 approach, and 1/3 held-out start-condition generalization. This passed the operational gate of at least one success at every level. It also passed the predeclared comparison gate because both success rate and mean reward exceeded baseline.

This is a small, noisy nine-episode demonstration, not a claim of robust Minecraft autonomy. Orientation did not improve over baseline in this sample, and the trained policy still timed out in five scenarios. The strongest observed improvement was approach (2/3 versus 1/3) plus one generalization success versus none.

## Artifacts

- Machine-readable metrics: `experiments/phase6/phase6_metrics.json`
- Episode table: `experiments/phase6/phase6_episodes.csv`
- Unedited service/server/client logs: `experiments/phase6/raw/`
- Comparison plot: `docs/figures/phase65_minecraft_evaluation.{png,svg}`
- Built mod: `minecraft_mod/dist/flycraft-bridge-0.1.0.jar`

No Phase 7 work was started.


# Bounded camera controller and initial validation

Date: 2026-10-28. The camera controller is implemented. Full Phase 7.5/8
reliability and autonomous-task validation remain incomplete.

## Observed causes

Inspection found direct 15-degree yaw writes in both Fabric clients. Earlier
resource actions also snapped toward visible hits, and forward reset pitch to
zero. Phase 8's eight-tick turn plus eight-tick cooldown and five-tick polling
left 20 ticks between observations. A measured sample of 92 earlier turns had
median acknowledgment delay eight ticks, median next-observation gap 20 ticks,
and median bridge latency 146.059 ms (maximum 1461.706 ms). These delays and
large writes explain jerky and delayed corrections; that timing evidence does
not by itself measure angular overshoot.

The resource-bearing calculation also used Java's remainder operator for yaw
wrapping. Accumulated headings beyond its assumed range produced invalid
bearings. The shared floor-based wrap now handles arbitrary accumulated yaw.
Stale/duplicate action identities and responses are rejected before movement.

## Controller and boundary

`CameraMotion` is a generic tick-based actuator receiving explicit angles or
angular velocities. It receives no blocks, entities or target coordinates.
`CameraDriver` applies it to Minecraft player angles and logs actual movement;
a read-only render mixin also records the rendered camera angle.

| Property | Default | Units |
|---|---:|---|
| `camera.maxYawVelocity` | 120 | degrees/second |
| `camera.maxPitchVelocity` | 90 | degrees/second |
| `camera.yawAcceleration` | 720 | degrees/second squared |
| `camera.pitchAcceleration` | 540 | degrees/second squared |
| `camera.yawDeceleration` | 1080 | degrees/second squared |
| `camera.pitchDeceleration` | 810 | degrees/second squared |
| `camera.toleranceDegrees` | 0.02 | degrees |
| `camera.maxCommandAgeTicks` | 8 | ticks |
| `camera.relativeTimeoutTicks` | 100 | ticks |
| `camera.continuousTtlTicks` | 5 | ticks |

Properties belong in `flycraft-phase8-client.properties` for the resource
client, or `flycraft-camera.properties` for the earlier navigation client.
The runner exposes `--camera-mode` and `--turn-degrees`. Its policy action step
defaults to 15 degrees and supports smaller configured steps. The preserved
policy does not learn a continuous turn magnitude or select a pitch action.

Relative commands retain one endpoint instead of reapplying their delta each
tick. Continuous commands use degrees/second and expire unless renewed; a
renewal extends the same command rather than queues another turn. Replacement
commands preserve bounded braking. A new target inside unavoidable braking
distance is rejected while existing motion brakes. Ordinary cancellation
decelerates; disconnect/emergency cancellation stops further writes. Manual or
external angle changes cancel motion and impose a short override cooldown.
World resets clear command identities and pose history.

Yaw uses the shortest wrapped delta; pitch is clamped to [-90,90]. Each step
is capped at 50 ms so a delayed tick cannot cause a catch-up jump. Position,
speed, acceleration, angular error, endpoint overshoot and settling time are
logged. Continuous commands have no endpoint, so their endpoint-error and
overshoot values are null. Commands are serialized rather than queued behind
ongoing turns. The redundant legacy turn cooldown is removed in strict modes.

Both `bounded` and `instant` modes require actual crosshair hits for mining,
placement and opening crafting tables. They never automatically aim or track
targets. Earlier assisted results use explicit `legacy` mode. See the
[observation contract](phase8_observation_contract.md) before comparing scores.

## Initial live motor comparison

`camera_before_v2_vulkan` and `camera_after_v2_vulkan` use the same world and
layout seed 44556677, checkpoint, controller limits and scripted angle cases,
on the NVIDIA Vulkan renderer. They isolate an instantaneous relative actuator
from the bounded actuator; the reference omits historical extra cooldown and
target-aim macros. These are **scripted motor tests, not policy success**.

The reference passed all 11 applicable cases and skipped continuous input,
which its original interface does not support. Bounded passed all 12 cases:
small +/-1-degree turns, +/-15 degrees, 90 degrees, yaw wrap at 180 degrees,
pitch clamps, rapid reversal, interruption, duplicate/stale rejection, and
continuous-input renewal/expiry. A second bounded run also passed 12/12.

| Measurement across nine static cases | Instant reference | Bounded |
|---|---:|---:|
| Maximum observed player yaw velocity | 4385.55 deg/s | 115.73 deg/s |
| Mean wall time to player-angle settling | 0.097 s | 0.675 s |
| Final wrapped angular error | 0 degrees | 0 degrees |
| Maximum recorded endpoint overshoot | 0 degrees | 0 degrees |

For 15-degree yaw, settling took 0.102/0.101 seconds in the reference and
0.501/0.468 seconds with bounds. For 90 degrees it took 0.101 versus 1.306
seconds; 180 degrees took 0.074 versus 2.249 seconds. Bounded motion reduces
large steps and peak speed but adds measurable actuator latency. There is no
evidence here that the single-request reference overshot its endpoint, so no
claim of a measured overshoot reduction is made. Policy corrections and
interaction assistance require separate evaluation.

Only one primary repeat per condition is available. Frame sampling and host
timing differ between launches. Rendered samples are retained, but a
pre-command rendered sample is not always available; these values describe
the player-angle settling criterion, not a perceptual smoothness rating.
Rapid reversals use the same relative-command timing and therefore have
different endpoints when the actuators have made different progress.
The later Vulkan client shutdown failures remain separate from motor results.

Reproduce the analysis with:

```powershell
.\.venv\Scripts\python.exe tools/analyze_camera_comparison.py --before camera_before_v2_vulkan --after camera_after_v2_vulkan --output experiments/phase8/new_camera_comparison.json
```

The dependency-free Java tests cover over 300 cases, including random
dual-axis turns, acceleration/deceleration, wraparound, pitch limits, stale
commands, reversals, lag, cancellation and manual override. Python invokes the
actual Java core. The complete automated suite currently passes 65 tests.

## Remaining validation

An initial strict-mode policy comparison used the same three starting layouts
and poses (world/layout start 44556777), six-live-episode checkpoint, policy RNG
9001, NVIDIA OpenGL backend and 400-tick/20-second deadline. Normal Minecraft
item-drop dynamics were not replayed exactly. No training occurred.

| Measurement | Instant reference | Bounded |
|---|---:|---:|
| Inventory-confirmed completion before deadline | 3/3 | 2/3 |
| Acknowledged block breaks / issued mining commands | 3/3 | 3/3 |
| Mean successful trial game time | 10.983 s | 5.175 s |
| Mean actions in successful trials | 12.33 | 3.00 |
| Actual trial times (failure capped at deadline) | 4.45, 9.85, 18.65 s | 4.45, 20.00, 5.90 s |

The bounded run's failed trial broke the log but obtained the item after the
server deadline. The controller's late success at 20.521 wall seconds remains
a failure in the independent server score. This reproduces the known terminal
observation/synchronization limitation. Both runs closed cleanly after the
Windows NVIDIA preference was applied, with maximum sampled GPU temperature
48 C. Videos and separate summaries are in each run's metadata and
`experiments/phase8/camera_policy_before_01.json` / `camera_policy_after_01.json`.

Three layouts cannot establish a task improvement or meaningful reliability
threshold. The shorter successful-only mean does not account for the failure.
The mining ratio describes executed, affordance-masked transactions; it is
not unrestricted cursor-hit accuracy. Both strict interfaces mask mining until
the crosshair is on the selected block. More repeated held-out comparisons
and longer deadlines are needed before attributing performance to smoothing.

The older 29/30 assisted one-log result is not evidence for this changed
interface. The preserved ten-action policy
also lacks pitch control, limiting strict table placement and higher logs.
Natural-world search, long-goal recovery, full live interruption/reconnect
stress tests and untouched held-out neural ablations remain pending. Phase 9's
headless infrastructure and the 10,000-world experiment are not complete.

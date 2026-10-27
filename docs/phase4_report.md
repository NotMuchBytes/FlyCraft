# Phase 4 report: Minecraft integration

## Gate decision

**PASS.** Two consecutive deterministic cycles covered left, center, right, and target-absent conditions. Minecraft produced the observations, the full graph simulator produced neural activity, the annotated readout generated actions, and Minecraft applied every first response with matching tick IDs. There were zero bridge errors and zero stale actions in the retained successful run.

## Exact stack

- Minecraft Java Edition 26.2
- Fabric Loader 0.19.5
- Fabric API 0.161.0+26.2
- Fabric Loom 1.17.21
- Gradle 9.5.1
- Microsoft OpenJDK 25.0.1, copied project-locally from the Minecraft Launcher runtime
- Python 3.14 virtual environment
- IPC: loopback TCP plus newline-delimited JSON from standard libraries

The mod layout came from FabricMC's official 26.2 example branch. Java 25 and Fabric version requirements follow the [official Fabric documentation](https://docs.fabricmc.net/players/installing-java/windows) and [Fabric example mod](https://github.com/FabricMC/fabric-example-mod/tree/26.2). No system-wide Java, Minecraft, or mod installation was changed.

## Test world and protocol

A project-local, offline-only dedicated server uses creative mode, peaceful difficulty, a flat world, five-chunk simulation distance, no structures, and a deterministic four-phase harness. For each phase it resets the player pose and places a visible gold block left, center, or right at seven blocks, or removes it for the absent control. The target position is used only to construct/reset the test world; coordinates are not sent to the policy.

The client samples once per 20 ticks. A request triggers the selected fixed 18-step bounded-rate window from zero state. Responses contain the same tick ID, action, readout totals, peak activity, and neural latency. `TURN_LEFT`/`TURN_RIGHT` change yaw by 15 degrees; `FORWARD` holds the forward key for five ticks; `NO_OP` changes nothing.

## Results without learning

For both first complete cycles:

| Presented target | Minecraft observation | Neural decoder action |
|---|---|---|
| Left | left | TURN_LEFT |
| Center | center | TURN_LEFT |
| Right | right | TURN_RIGHT |
| Absent | not_visible | NO_OP |

Center-to-left is a retained negative result from the fixed neural side decoder, not corrected with a hidden heuristic. Because the visual-projection metadata has left/right but no neutral-side population and the center response had a small left bias, the untrained decoder did not produce `FORWARD`.

Across 86 applied actions in the successful retained log, neural latency was 78.90 ms minimum, 95.76 ms median, and 404.38 ms maximum (the first cold request). There were no response-ID mismatches, stale actions, or bridge failures. Machine-readable evidence is in `experiments/phase4/phase4_metrics.json`; raw server/client logs are retained under `experiments/phase4/raw/`.

## Problems encountered

- Git and Windows curl could not use Schannel credentials, so the official Fabric template ZIP was downloaded through Python TLS.
- Java could not resolve security files while running inside the restricted process sandbox. The existing launcher JDK was copied into a project-local runtime and Gradle was explicitly authorized.
- OneDrive locked Gradle's generated output directory. Authoritative source remains in the FlyCraft project, while builds run from a non-OneDrive mirror and copy only the final JAR back.
- The first scene harness placed later targets relative to a pose changed by earlier actions, so right-phase coverage was unreliable. That run is retained as `run1_*`. The harness was corrected to reset the player pose each phase; `run2_*` passed twice.
- Minecraft's optional OSHI performance-counter probes emitted Windows registry warnings. They did not affect server, client, neural bridge, or synchronization.

## Limitation

The bridge demonstrates reliable closed-loop plumbing, not intelligence. It uses a simplified five-ray target sensor, a single block type, a local controlled world, and an intermediate neural readout rather than descending neurons.


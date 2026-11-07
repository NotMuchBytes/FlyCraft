# Phase 7.5 live checkpoint restoration

The operator-only `bridge_checkpoint_restart` diagnostic saves the first
pending mining decision before delivering it. After Minecraft reports mining
has started, the runner stops the bridge process tree it launched. Minecraft
continues running. After a bounded five-second pause, a fresh Python process
loads that snapshot and waits for Minecraft to acknowledge the pending action.
The snapshot is distinct from committed training checkpoints. This mode
requires one trained-policy evaluation episode with learning disabled.

## Verified retry

On Minecraft 26.2, run `p75_pending_checkpoint_20261107_b` saved command 1 at
observation tick 760 and stopped the bridge after that command started mining
at tick 768. The new launcher started 5.316 seconds after shutdown. Minecraft
logged eight connection refusals during the restart. The first restored
decision exchange arrived at tick 990, from the same Fabric adapter instance.
Its real acknowledgment said command 1 had broken a block after 60 action
ticks. Python accepted it once and issued command 2. The Minecraft trace has
exactly one mining start and exactly one block change.

The learned policy continued with movement and camera actions, collected the
drop, then selected `CRAFT_PLANKS`. The server adapter performed the existing
engineered 2×2 inventory recipe interaction. Both the server and restored
controller confirmed **four planks after six actions and 281 game ticks**.
The terminal exchange was acknowledged on its first wait tick. Both Minecraft
processes exited cleanly. The original 139,255-neuron graph, policy checkpoint
and training history were preserved. No updates were made.

OBS captured the isolated Minecraft window on an RTX 4050 with OpenGL. The
32.133-second H.264 MP4 passed full decoding, and sampled frames showed
gameplay before, during and after the outage. The 854×480 game window was
scaled to 1920×1080 at 30 fps. The spectator shows the actor's movement and
mining. The recipe and final inventory are verified in the synchronized logs.
Minimum sampled available RAM was 929.17 MiB and maximum sampled GPU
temperature was 54 C. The video and raw traces remain available locally.
[Verified recording metadata](../recordings/phase9/youtube/p75_pending_checkpoint_20261107_b.json)

## Earlier attempt and scope

The first recording attempt hit the 768 MiB RAM guard before gameplay and
produced a playable 5.033-second startup-only MP4. It has zero scored episodes
and no checkpoint restart. The successful retry is a separate execution.
[Startup-only recording metadata](../recordings/phase9/youtube/p75_pending_checkpoint_20261107_a.json)

The 110-test automated suite passed in 19.917 seconds. This test establishes
in-episode Python process restoration with a live headless adapter in one
controlled fixture. It does not estimate recovery rates, exercise a Minecraft
server restart, or add an ordinary plank success to the evaluation totals.
[Successful run manifest](../experiments/phase9/p75_pending_checkpoint_20261107_b/run.json)

# Phase 7.5 bridge recovery

The [original bridge-stall trial](phase75_reliability_20261106.md) broke a log,
then discarded a stale FORWARD response without acknowledging it. The Python
controller waited for the missing acknowledgment and the episode ended with zero
logs. This increment addresses responses that reach the adapter after their
execution window.

Both Fabric adapters now send a `not_executed` receipt for a recognized stale
command in the current episode. They reserve its command ID so a delayed
duplicate cannot execute. The graphical client also keeps its request in flight
until the client-thread callback finishes. Python discards the pending policy
decision, retains the observed inventory, and requests a fresh decision.
Unexecuted commands do not count as actions, action rewards, or block changes.
The controller suppresses training for affected episodes and terminates after
five rejections. A spectator-only change dismisses the capture client's pause
overlay when no game action is required.

## Live validation

In Minecraft 26.2, run `p75_rejection_fix_20261106_b` suspended the serving
Python process tree for 6.545 seconds. The headless adapter rejected FORWARD
command 2 with `not_executed/stale_response` at server tick 849, with zero
execution ticks and no block change. The trace contains no start event for
command 2. The controller recorded that rejection, selected fresh actions,
and completed the goal in **10 executed actions and 276 game ticks**. The server
and controller both confirmed **one log in inventory**. Both game processes
exited cleanly.

The original failure and successful recovery used the same flat survival fixture,
world and layout seed 2026110601, policy seed 9001, checkpoint, 15-degree bounded
turns, two-tick forward actions, and a 400-tick budget. Their absolute spawn
positions and game RNG were not fully matched. This is one successful
recovery from a delayed reply. It provides no success-rate estimate for
unseen worlds and does not exercise an HTTP read timeout or full disconnect.

## Verification and footage

- **107 automated tests passed** in 21.607 seconds. New cases cover unexecuted
  action accounting, bounded rejections, and recovering a pending checkpoint
  transaction without replaying it. The Fabric mod compiled for Minecraft 26.2
  and 26.3. Live recovery exercised the 26.2 headless adapter; the 26.3 build
  was not deployed or exercised in-game.
- The recovery milestone has a 28.067-second Minecraft-window MP4. Full FFmpeg
  decoding passed. OBS scaled the 854x480 game capture to 1920x1080 at 30 fps.
  A 6 fps sample check detected the pause overlay in 110 samples of the original
  failure clip and zero samples of the recovery clip.
  Video SHA-256 `501c046032d08a21f7a4dbee32dd940018cb64fdc5ac069128585ed80a41eff5`.
  [Recording metadata](../recordings/phase9/youtube/p75_rejection_fix_20261106_b.json)
- The first recording attempt, `p75_rejection_fix_20261106_a`, failed to compile
  because it used an incompatible screen accessor. The corrected build ran as
  a new execution. No gameplay took place in the first attempt and no MP4 exists
  for it. Two recorded no-fault attempts hit the 768 MiB free-RAM guard before
  gameplay. Their playable MP4s cover startup only. The minimum samples were
  640.02 and 711.70 MiB respectively. These three attempts have zero scored
  episodes and remain archived with their separate run and recording metadata.

Run manifests and recording metadata are retained in the repository. The raw
game, controller and bridge traces and original MP4s are retained locally.
The 139,255-neuron graph and checkpoint stayed unchanged, and there were zero
training updates. This check does not measure neural contribution or change
the historical one-log and plank success rates.

Checkpoint SHA-256
`acdde37f8d3288764bcaad9dc9eea7c4f916c9894f54a019684fc3f555dd37f5`.
[Successful run manifest](../experiments/phase9/p75_rejection_fix_20261106_b/run.json)

## No-fault follow-up on November 7

Run `p75_rejection_normal_20261107_c` used the same checkpoint, seeds, motor
settings and 400-tick budget in a new 26.2 survival fixture. The agent collected
**one log in 4 executed actions and 100 game ticks**, with server inventory
confirmation and one acknowledged block change. The server exited cleanly.
The routine server-only regression was logged without OBS and ran with at
least 1,101.49 MiB free RAM in samples. Its logs do not replace the startup-only
recordings from the two earlier attempts.
[Run manifest](../experiments/phase9/p75_rejection_normal_20261107_c/run.json)

## Read timeout reproduced on November 7

A separate server-only diagnostic used the same seed and checkpoint with a
600-tick budget. The harness suspended the owned bridge process tree for
20.082 seconds. Command 1 broke a log at tick 108. The post-mining request
from tick 110 was waiting when Java logged `SocketTimeoutException: Read timed out`.
After resuming, Python processed that request and issued FORWARD command 2 on
the already-closed connection. The next live request, from tick 430, still
acknowledged command 1. Command 2 has no action-start event and no receipt.
Five unmatched acknowledgments ended the controller session with
`acknowledgment_timeout`. The server recorded **zero inventory logs at 600
ticks** and exited cleanly. The trace shows one actual action, the successful
mining action. The controller's failure counter includes the unacknowledged
command, which was a transport failure.

The earlier fix handles late replies that reach Fabric. This fault closes the
socket before Fabric can learn the pending command ID. Repair requires an
explicit delivery reconciliation that rules out earlier execution before
discarding the pending decision. The read-timeout diagnostic used structured
logs only. It was a fault reproduction without a recording milestone or a
successful recovery. Raw events are preserved locally and the run manifest is
checked in. The 107-test automated suite passed again in 19.685 seconds.
[Read-timeout run manifest](../experiments/phase9/p75_bridge_read_timeout_20261107_a/run.json)

## Read-timeout repair and validation status

Fabric now reports the start of a failed reply interval and its most recently
accepted or explicitly rejected command ID. The controller reconciles a
pending decision only when it was issued within that interval, belongs to the
same adapter instance and game session, and is newer than Fabric's watermark.
A real acknowledgment takes precedence. On proven loss the existing
unexecuted-command handling discards the decision, suppresses learning and
resamples from current observations. No replay or action credit is assigned
to the undelivered command.

The repository's regression suite passed 110 tests in 19.224 seconds. Added
coverage includes invalid inventory during recovery, real acknowledgment
precedence, adapter replacement, and pending checkpoint restoration.

The first server-only retry, `p75_reply_loss_fix_20261107_a`, compiled and
stopped at the 768 MiB RAM guard before gameplay (732.17 MiB minimum).
The second retry used Serial GC and a four-processor JVM limit while keeping
the 384 MiB heap and RAM guard. The Minecraft server confirmed one log after
78 game ticks, but the RAM guard (631.95 MiB minimum) ended the run during the
suspension. The bridge resumed after 10.624 seconds during cleanup, before the
15-second socket deadline. The controller stopped without an acknowledged
episode. This is inventory evidence from the server and does not validate
read-timeout recovery. No matched recorded recovery or new milestone MP4
was produced. Raw episode and operator-fault data are retained.
[First retry](../experiments/phase9/p75_reply_loss_fix_20261107_a/run.json)
[Second retry](../experiments/phase9/p75_reply_loss_fix_20261107_b/run.json)

## Verified Minecraft read-timeout recovery

Server-only run `p75_reply_loss_fix_20261107_c` completed the full test.
The bridge process tree was suspended for 20.199 seconds. Minecraft broke a
log at server tick 109, then Java's read of the tick-110 observation timed out.
When Python resumed, it generated FORWARD command 2 for that closed exchange.
The next exchange (observation tick 430) reported reply loss since tick 110
and a watermark of 1. Python discarded command 2 and generated command 3.
There is no Minecraft action-start event for command 2. The camera rejected
command 3 for `stale_wall_time` with zero action ticks, and subsequent decisions
continued normally.

The controller counted 10 acknowledged actions (including the zero-tick
camera rejection), one block change, and one log in terminal inventory.
The independent server also confirmed one log at 529 episode ticks, received
the terminal acknowledgment on the first wait tick, and exited cleanly.
Minimum sampled RAM was 1,093.63 MiB and maximum sampled NVIDIA GPU
temperature was 48 C. The unchanged checkpoint ran with learning disabled.
The earlier failing trial used the same fixture and policy seeds and
600-tick limit, with a different absolute spawn position and game RNG. This
validates one headless recovery on Minecraft 26.2. Broader reliability,
graphical-adapter recovery and live checkpoint restoration remain open.
[Successful run manifest](../experiments/phase9/p75_reply_loss_fix_20261107_c/run.json)

## Recorded milestone

Run `p75_reply_loss_recorded_20261107_a` was a fresh execution with the same
checkpoint, fixture and policy seeds, and an isolated OBS spectator. Java
timed out on observation tick 780 during a 20.417-second bridge suspension.
The bridge later generated FORWARD command 2 for the closed exchange. The
tick-1100 request reported the loss and the watermark of 1, so the controller
discarded command 2 before sampling command 3. The action trace confirms
command 2 never started. The camera rejected command 3 for
`stale_wall_time` with zero action ticks. The policy continued and both
server and controller confirmed one log in inventory at **505 game ticks**.
The controller recorded **nine acknowledged actions** including that camera
rejection, and one block change. Terminal acknowledgment arrived on the
first wait tick and both Minecraft processes exited cleanly.

OBS recorded the Minecraft window on the RTX 4050 using OpenGL. The 42.1-second
H.264 MP4 passed full decoding. The game ran at 854×480 and OBS exported
1920×1080 at 30 fps. Capture preflight matched the independent Minecraft
frame and six sampled timestamps show the game throughout the stall and
recovery, with Minecraft tutorial overlays visible. The original video
was preserved without editing the AI's actions. Minimum sampled available
RAM was 1,516.57 MiB and maximum sampled GPU temperature was 47 C.

This gives two confirmed read-timeout recoveries on the same fixture seed.
They are excluded from normal goal success-rate and learning estimates. The
earlier headless episodes retain their own logs and have no video. The new
recording covers the recorded retry.
[Recording metadata](../recordings/phase9/youtube/p75_reply_loss_recorded_20261107_a.json)

# Phase 8 three-log development trials

The live runner accepts the existing three-log objective in headless
Minecraft. The optional `--three-tree-fixture` places three seeded trunks
near the starting position. Each trunk has a log at eye height, so the
existing yaw-only action set can attempt all three. The fixture supplies
the environment and the server independently scores actual inventory.
The learned policy selects turns, movement and crosshair mining. The
139,255-neuron graph and policy checkpoint were preserved.

The first Minecraft 26.2 trial broke one block, collected the drop, and
crafted it into four planks. It finished with zero logs after 52 actions
and 700 game ticks. The controller now masks recipe and placement actions
for the three-log objective across all policy conditions. The regression
test checks the mask and confirms the goal stays open with two logs.

Three subsequent trials used the mask, with one world seed and three
distinct fixture layouts. The server and controller agreed on one, one,
and two logs respectively. Each trial reached the 700-tick boundary and
delivered its terminal acknowledgment. They recorded 51, 51, and 47
actions and one, one, and two confirmed block changes. No crafting
consumed a log. All three were still below the three-log target.

In the first masked trial, all 42 observations after pickup selected the
same upper block of the mined trunk. The headless three-log sensor now
prefers a visible log found by a ray at the actor's current pitch when
one is available. Other visible logs remain a fallback and visible drops
retain priority. The new ranking uses the existing rays and changes no
camera action or target visibility.

[Initial probe](../experiments/phase9/p8_three_tree_probe_20261107_a/run.json)
[Log retention trials](../experiments/phase9/p8_three_tree_probe_20261107_b/run.json)

The recorded retry on the first layout collected two logs after 46
actions. Minecraft and the controller agreed on the final inventory at
700 game ticks. The remaining target selection still repeated an upper
block. All 27 observations with two logs selected that same block. The
48.6-second MP4 passed full decoding and the window capture check on
the RTX 4050. Sampled frames show the actor and the three trunks during
gameplay.
[Verified recording](../recordings/phase9/youtube/p8_three_tree_recorded_20261107_a.json)

# Local companion preview

This opt-in mode lets a human play alongside a separate `FlyCraftAgent` survival
player in a new singleplayer test world. It does not control the human's input,
change their game mode, spawn a test tree, clear inventory, or run the evaluation
harness. Resource mode uses the existing learned controller. Follow mode uses
explicit engineered pathfinding, separately from neural evaluation.

The normal development target remains Minecraft 26.2. To build an isolated
26.3 preview for an existing Fabric 0.20.1 / Fabric API 0.165.0+26.3 profile:

```
.venv/Scripts/python.exe tools/build_minecraft_26_3.py --destination <new-build-folder>
```

Copy the resulting non-sources JAR into the stopped profile's `mods` directory.
This port updates the teleport acknowledgment and swing signatures, and omits
the obsolete GLFW window redirect because 26.3 uses SDL. It preserves the other
packet, rendered-camera and skin mixins. Do not downgrade an existing 26.3 world.
The plain Java assertion tests are exercised by the Python test suite; Gradle
`assemble` compiles/packages both mod source sets.

In that profile's game directory, create `flycraft-companion.properties` with
an exact new test-world name and absolute paths, using forward slashes:

```properties
worldName=FlyCraft Companion Test 2026-10-31
controlFile=<session-directory>/control.json
maxRunTicks=1200
projectDirectory=<FlyCraft-repository>
pythonExecutable=<FlyCraft-repository>/.venv/Scripts/python.exe
checkpointFile=<existing-evaluation-checkpoint>
bridgePort=8875
```

Create the session directory first. Also create `flycraft-headless.properties`:

```properties
companion.enabled=true
controlFile=<same-control-file>
traceFile=<session-directory>/headless
bridgePort=8875
camera.mode=bounded
camera.turnDegrees=15
motor.forwardTicks=2
motor.verifyMovement=true
camera.pitchActions=true
```

The companion only spawns in singleplayer when the world's display name exactly
matches the configuration. It waits for the human to join. Other worlds remain
ordinary play worlds. The client never enters its legacy or Phase 8 player
control adapter while companion mode is configured.

The local brain process loads lazily on `/flycraft start` and stops when the
world's server closes. Following does not require loading it. Resource mode
loads the existing checkpoint, records each session separately and disables
learning/checkpoint writes. The port is loopback-only; choose a free port and
use the same value in both files. Brain loading can take a moment; retry start
after loading if needed.

- `/flycraft follow` follows the player who executes it, pausing resource mode.
- `/flycraft status` reports the companion mode and whether it is alive.
- `/flycraft start` begins a one-log attempt with a fresh episode identity.
- `/flycraft stop` cancels the NPC's movement, mining and turning, making it stay.
- `/flycraft respawn` explicitly recovers a dead NPC. Follow also requests this
  recovery if the NPC is dead; a living NPC is not teleported by this command.

## English requests and taught names

With the English-orders build installed, address the NPC in Minecraft chat:

```text
FlyCraft, get me 3 logs
FlyCraft, could you please bring me a wooden pickaxe?
FlyCraft, make me 4 planks
FlyCraft, follow me
FlyCraft, what do you have?
FlyCraft, stop
```

`/flycraft say get me 3 logs` provides the same interface without the name prefix.
It currently accepts quantities from 1 to 16 for generic logs/wood, planks,
sticks, crafting tables/workbenches and wooden pickaxes. Specific wood species
and other items are rejected explicitly. Larger quantities can exceed the
existing policy's action/time budget; accepting a request does not guarantee
completion. Use a pitch-enabled checkpoint with `camera.pitchActions=true`.

Teach an additional name with `FlyCraft, teach timber means logs`, then say
`FlyCraft, get me 2 timber`. Names are saved per requesting player's UUID in
`learned_item_names.properties` beside `control.json`, including across restarts.
This is explicit vocabulary learning through a bounded grammar; it does not
train a general English model or change the sparse brain.

The NPC remembers who requested the task and reports collecting, returning,
delivery, failure, health, food and its own inventory. Another player's stop
or replacement request cannot take over an active task. The requester can
cancel or ask for status. Collection/crafting actions remain policy-selected.
Returning uses the separately engineered companion navigation described below.
Handoff removes existing NPC inventory and drops ordinary Minecraft items for
the requester, with the initial throw velocity set to zero so they fall at
the NPC's feet rather than flying past the requester during the pickup delay.
This is engineered delivery assistance; gravity and pickup remain vanilla.
Success requires a native pickup event and the requester's
matching inventory increase; dropping an item alone is not delivery.

`orders.jsonl` records accepted requests, taught words, task transitions and
pickup receipts. Each brain session retains separate native/controller logs.
Unsupported requests, death, an unavailable requester and timeouts are reported
as failures. This operational task awareness is not a claim of consciousness.

Following uses the owner's server position and the server collision map via
vanilla navigation with an unspawned player-sized probe. These are privileged
engineered inputs, not additional observations for the learned resource policy.
The probe never runs mob AI or modifies the world. Bounded camera turns orient
the NPC toward path waypoints; this is not learned aiming or target tracking.
Normal following walks, jumps and requests floating in water; it never
teleports to catch up. It stops near the owner with 2.5/3.5-block hysteresis,
waits beyond 40 blocks, and stops if the owner leaves or changes dimension.
Repeated failed plans or stalled movement cause bounded waiting until the
owner moves. This does not guarantee safe navigation through all hazards.

Explicit death recovery uses vanilla respawn/inventory rules, then searches
for collision-free dry ground near the owner. This initial recovery placement
can teleport the newly respawned NPC; if no suitable position is found it
retains the vanilla spawn. Human respawns use the vanilla player constructor.
Respawn, water survival and dimension transitions still need live validation.

An attempt ends when the existing controller finishes or after 1,200 game ticks
(60 game seconds). The human can continue playing and start another attempt.
The NPC uses ordinary survival physics and can be obstructed, lose a drop, or
fail to find a tree. Player help and human interference mean these interactive
sessions are not independent autonomous evaluation trials. Brain, observation
and action logs remain local; this mode is not part of the official campaign.

For milestone capture only, `recording.windowTitle=FlyCraft Recording <token>`
can label the client window. OBS's isolated collection supports explicit
`window_class` / `process_name` script settings while retaining exact-title,
WGC-only capture, ownership and heartbeat checks. Legacy recording defaults
remain `GLFW30` / `java.exe`. Verify actual capture before starting the AI.

An optional `commandFile=<absolute-path>` permits local background follow/stop
integration checks using a request identity and owner UUID. This operator
interface is never a neural observation or evaluation action. Cancel pending
requests when abandoning a test; requests currently have no expiry time.

The October 31 Minecraft recording demonstrates following, but world exit
interrupted the planned stop/resume check. It is an interactive preview, not
an independent collection trial. See [validation](companion_follow_validation.md).
This preview does not provide chat or natural-terrain reliability guarantees.
Phase 7.5 remains incomplete.

# Phase 8 observation and action contract

The policy and planner receive client-observable state through the existing
local Fabric/Python TCP bridge. The sparse 139,255-neuron graph is unchanged.
Live action decisions use its existing 18-step full-network observation
window. The default learned readout has 63 features and 10 actions. Recipe structure, semantic
perception, legal-action masking and transaction execution are engineered
assistance, shared by trained, frozen, uniform and neural-ablation conditions.

## Observations

| Observation | Source and limits |
|---|---|
| Five-sector neural input | Selected observed resource, classified by relative yaw. The headless three-log goal prefers visible logs at the actor's current pitch. Visible drops retain priority. |
| Visible logs | Fifteen first-hit rays: yaw offsets -40,-20,0,20,40 and pitch offsets -30,0,30 degrees, maximum 12 blocks; blocking geometry occludes farther blocks |
| Dropped log items | Client-rendered entities within 12 blocks, yaw +/-50 and pitch +/-45 degrees, with unobstructed line of sight; visible drops take target priority |
| Resource identity | Block/item semantic class and identity of the observed hit; this is a semantic sensor, not a learned pixel classifier |
| Distance and angle | Geometry of the visible ray hit/item; distance is used for reward/completion, while the policy receives neural features and near-state |
| Pose | Player's own client position, yaw and pitch; never an undiscovered resource position. Pitch telemetry is not a new learned feature in the preserved 63-feature readout. |
| Inventory | Counts reconstructed from vanilla server container-content, container-slot and player-inventory packets; predicted client inventory is separately checked for consistency |
| Crafting station | A crafting table found by the same visible rays within four blocks; strict modes require the actual crosshair to interact |
| Headless placement surface | When the pickaxe goal has an owned table and no visible station, existing yaw rays at current pitch can report a visible support face. Placement uses the actual crosshair within three blocks and excludes destinations that intersect the actor. |
| Optional relative pitch error | With the headless pitch readout enabled, the vertical angle in radians from the actor's current view to the selected visible hit or drop. The value is zero when no target is visible. Placement sensing also uses first-hit rays at pitch offsets −30° and +30° within the existing four-block range. |
| Placement affordance | Strict modes require the actual crosshair hit on a valid upward face; legacy mode uses a downward ray in front of the player. Both are collision-tested and within four blocks. |
| Action outcome | Command identity, primitive action, server-confirmed block change, timeout/interruption and inventory revision |
| Goal instruction | Externally supplied objective and episode identity; experiment condition and policy RNG seed are control parameters |

World seeds, fixture layout seeds, hidden block maps, future observations and
server success labels are not sent to the agent. The operator's fixture
configuration and independent scoring logs remain outside the observation
channel. The semantic sensor's field of view is an explicit abstraction and
does not reproduce the exact pixels of the main Minecraft camera.

## Action transactions

- The new runner defaults to `camera.mode=bounded`: explicit relative turns
  use a bounded tick controller, with a configurable 15-degree policy action
  step. Forward holds the normal movement key for five ticks and never resets
  pitch. Each action is followed by an observed outcome. The `instant`
  reference applies the same relative requests in a single write.
- In both strict modes (`bounded` and `instant`), `COLLECT_LOG` requires the
  actual crosshair to hit the selected visible log within three blocks.
  It never aims at a block or tracks a target. Losing the hit interrupts mining.
  Crafting-table opening and placement similarly require real crosshair hits.
  The default ten-action policy turns in yaw. The experimental headless
  `--pitch-actions` interface adds policy-selected `LOOK_UP` and `LOOK_DOWN`
  using the same bounded or instant relative actuator. Each uses the configured
  fixed turn magnitude. The actor can select either direction while away from
  its pitch limit, including when the view contains no target.
- Explicit `camera.mode=legacy` preserves the earlier Phase 8 evaluation
  interface. `COLLECT_LOG` aims at one already-visible, reachable log and sends normal
  survival mining interactions for at most 120 ticks. The server echoes the
  actual post-break block state after the ordinary block-break event. The
  client waits for this update. It does not teleport, give items, alter the
  server block directly or automatically walk to collect drops. Legacy turns
  are instantaneous and forward resets pitch. Earlier properties with no
  `camera.mode` retain this behavior for reproducibility. The primary 29/30
  result used this assisted interface and cannot be pooled with strict runs.
- Collection completes only when the observed server inventory contains the
  required logs. Mining a block and obtaining its dropped item are separate.
  The three-log objective removes recipe and placement actions from the
  policy mask so the agent retains the logs it needs. Every comparison
  condition receives this same mask.
- The optional headless memory flag remembers the columns of confirmed log
  breaks in the current episode. It omits off-pitch ray hits in those
  columns. The existing visible drop and current-pitch observations remain
  available.
- Planks, sticks, crafting tables and pickaxes use normal container clicks:
  place exact ingredients, wait for the recipe result, transfer the output,
  and wait for server inventory confirmation. A pickaxe transaction can open
  an already-observed reachable table. Recipe slot placement is an explicit
  primitive abstraction, not learned mouse control.
  The live stick, table and pickaxe objectives mask recipes outside the
  active planner subgoal for every comparison policy.
- Table placement selects an owned item and a visible ground hit, sends the
  normal use-item interaction, then waits for the echoed server block state
  and inventory update. No crafting or placement is performed without the
  corresponding sampled policy action.
- Interrupted/failed crafting returns partial ingredients through normal
  inventory clicks. Actions have deadlines. Commands are not replayed after
  missing acknowledgments or checkpoint restoration.
- After a bridge exchange fails, Fabric reports the first affected observation
  tick and the last command ID it accepted or explicitly rejected. Exchanges
  are serialized through the game-thread callback. The controller can discard
  a pending decision only when it came from that interval in the same game
  session and adapter instance, and is newer than Fabric's watermark. A
  matching game acknowledgment takes precedence. The next action is sampled
  from a fresh observation, and the
  affected episode is excluded from training. These are transport fields,
  separate from policy inputs.
- A live episode binds to its Minecraft session and Fabric adapter instance.
  A different instance cannot acknowledge a pending command for that
  episode, even if its numeric ID matches. A deliberate server restart uses
  a new episode identity and starts from fresh observations. Supervised
  completions wait for the final server inventory before writing the result.

## Evaluation boundary

The server mod explicitly echoes a full vanilla inventory-menu packet whenever
the player's own inventory changes. Vanilla prediction can otherwise suppress
matching slot updates, leaving an independent acknowledgment ledger stale.
This echo contains the player's own inventory only. The same server component
echoes blocks directly mined or placed; it supplies no hidden world map.

Recorded live runs require the companion OBS Lua recorder. A separate collection
captures only the exact Minecraft window, with microphone and desktop audio
sources absent. A local file handshake opens the trial gate only after OBS
reports active recording. Lost confirmation aborts the run; a 60-second
heartbeat watchdog stops recordings if the supervisor disappears. The client
sets GLFW focus hints to false and continues rendering on lost focus. No
desktop input, window activation, global hotkeys or remote-control server is
used. This records game trials; source editing and console work remain in
their ordinary logs.

The disposable harness resets inventory, player pose and small survival tree
fixtures and independently scores actual server inventory. It supplies no
actions. These are real game transactions in controlled flat-world scenes,
not evidence of forest search, survival, arbitrary terrain navigation or
robust natural-world generalization. World seeds and layout seeds are logged
separately. A gate used for the OBS repeat delays the scene until recording
starts; it does not choose any policy action.

`pickaxe_transaction` is a separate integration fixture with three planks,
two sticks and a nearby placed table supplied initially. It tests the
ordinary pickaxe crafting transaction, not resource acquisition. The initial
three diagnostic attempts all failed; the macro is not yet validated. Its scores
must never be pooled with from-empty-inventory `wooden_pickaxe` trials. The
agent sees only its actual own inventory and normally visible table; the
fixture supplies no policy actions or hidden coordinates.

`camera_probe` is a separate scripted motor diagnostic. It supplies explicit
angle commands and controlled starting poses, without querying the AI policy.
Its server success flag means motor checks passed, never autonomous collection
or learning. It receives no block target for aiming. See `camera_controller.md`.

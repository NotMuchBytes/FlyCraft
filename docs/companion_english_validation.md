# Companion English requests — November 26, 2026

FlyCraft now accepts a bounded, teachable English command interface in the
opt-in companion world. It supports generic logs/wood, planks, sticks, crafting
tables/workbenches and wooden pickaxes, in quantities from 1 to 16. Other
resources and specific wood species are rejected. This does not provide a
general language model, consciousness, or guaranteed collection reliability.

[Setup and examples](companion_play.md#english-requests-and-taught-names).

## What learns and what acts

`FlyCraft, teach timber means logs` saves an explicit per-player alias.
`FlyCraft, get me two timber` resolves that alias to an inventory objective.
Aliases survive reload; players can give the same alias different meanings.
The grammar, quantity parsing, task ownership and status replies are engineered.
Task awareness uses the requester, task phase, health, food and actual inventory.
The requester can cancel; a bystander's stop cannot cancel their active order.

The existing stochastic neural readout chooses resource movement, camera,
mining and crafting actions. Requested counts pass through the planner and
survive recovery replans. Companion requests disable learning/checkpoint writes.
The existing 139,255-neuron sparse graph and checkpoint files are preserved.
The graph SHA256 remains
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.
The tested pitch checkpoint is
`checkpoints/phase8/finish_20261123/progress_readout_mining.npz`, SHA256
`0dc48b845f66029cd5c5855e1835713a8c0dd6577b1c4901ffa388e0f34f38a4`.

Returning uses engineered vanilla pathfinding with the requester's position
and collision map. Those privileged inputs never enter the resource policy.
Handoff removes existing inventory, drops recipient-targeted item entities
within 1.15 blocks, and zeroes their initial throw impulse. Gravity, pickup delay
and pickup remain Minecraft mechanics. No item is created to satisfy a request.
Delivery requires the tracked parcel UUID, correct recipient and an observed
inventory increase inside native `ItemEntity.playerTouch`. A drop alone never
counts. Full pickups discard the entity and restore its stack count for feedback;
the observer explicitly handles that vanilla behavior.

## Functional live evidence

These are development diagnostics in a **controlled fixture**, with a supplied
tree and matched initial poses, not vanilla exploration, held-out reliability
evaluation or Phase 9 campaign scores. Synthetic requests travel through the
actual Fabric chat event; the fixture supplies no gameplay actions. All players
begin without logs. Existing survival physics, policy-selected actions, block
changes, NPC pickup, return and recipient pickup execute inside Minecraft 26.2.
Different attempts use fresh disposable worlds and fresh episode identities;
they are not exact action replays. [Complete evidence index](../experiments/companion/english_20261126/index.json).

| Run | Result | Resource actions | Request to delivery | Total diagnostic time |
| --- | --- | ---: | ---: | ---: |
| `english_live_4`: get one log | Delivered 1; requester 0→1 | 11 | 16.628 s | 41.047 s |
| `english_record_3`: teach timber; bring one timber | Delivered 1; requester 0→1 | 12 | 18.153 s | 75.097 s |
| `english_record_4`: reload vocabulary in a new process; get two timber | Delivered 2; requester 0→2 | 19 | 23.242 s | 77.310 s |
| `english_live_5`: reload vocabulary; get three timber | Failed; three breaks, two NPC pickups, no delivery | 120 | — | 115.590 s |
| `english_live_6`: make four planks | Crafted and delivered 4; requester 0→4 | 24 | 28.872 s | 53.657 s |
| `english_live_7`: bring a wooden pickaxe | Crafted and delivered 1; requester 0→1 | 37 | 38.886 s | 63.394 s |

Resource action counts use acknowledged native action-end events; they exclude
engineered return navigation. These few functional cases do not estimate a
success rate or a neural benefit. In particular the three-log failure remains
an underlying pickup/exploration limitation, not a successful English request.
It reported `collection_max_steps` and retained two logs in the NPC inventory.

Earlier diagnostics remain preserved: `english_live_2` physically delivered a
log but its old pickup observer missed the receipt and timed out;
`english_live_3` was an unscored busy-port hold; `english_record_1` failed before
the request because a synthetic player name exceeded the protocol's 16-character
limit; `english_record_2` collected a log but threw it outside pickup range.
The recorded teaching success in `english_record_3` has native success and
confirmed pickup receipts, but its original supervisor summary misclassified
the normal post-result server disconnect. Its raw summary is retained alongside
an explicit audit. The supervisor was corrected; `english_record_4` passed both
the native result and supervisor. No failure was relabeled as a fresh replay.

## Recording and builds

The successful teaching and vocabulary-reload milestones used OBS with one
exact-title Minecraft window source, no desktop/audio/cursor capture, and the
NVIDIA GeForce RTX 4050. The request gate opened only after independently
captured Minecraft and OBS frames matched. Original MP4 packets were preserved
and the full videos decoded successfully. Native logs remain authoritative for
inventory receipts. Local video paths and checksums are in each run's audit.

Verified milestones (local outputs, deliberately outside Git):

- `FlyCraft_English_Teaching_Delivery_Fresh3_20261126.mp4`: 31.4 seconds;
  941 fully decoded frames; native teaching/mining/delivery success, with the
  supervisor classification issue disclosed above.
- `FlyCraft_English_Vocabulary_Reload_Two_Logs_20261126.mp4`: 34.4 seconds;
  1,031 fully decoded frames; both native and supervisor success.

Both are H.264, 1920×1080 at 30 fps, from the same 854×480 Minecraft-only
source. Contact sheets were also inspected for real Minecraft gameplay and
the fixture's explicit synthetic-chat labels. The earlier failed videos remain
preserved separately and are not presented as successful milestones.

The Python suite passes **187 tests**, including pure Java grammar, ownership,
partial/replayed receipts, persisted vocabulary, count protocol validation and
count-preserving replanning. Both Fabric 26.2 and the isolated 26.3 port compile.
The port adapts teleport acknowledgments, swing and server-only inventory/drop
prediction signatures. Live English delivery is verified on **26.2**; the 26.3
build is a compiled preview, with interactive runtime verification remaining.

Use `tools/test_companion_english_live.py --help` for the opt-in disposable
diagnostic. It accepts Gradle server/client launch exports, a fixed checkpoint,
new runtime directory, a request, an optional lesson or saved vocabulary, and
optional OBS recording. It preserves a source manifest and checkpoint hash.
It enforces a 2 GiB free-disk guard, 768 MiB live RAM reserve, 1,800 MiB launch
margin (3,000 MiB for recording), and 75°C GPU limit. It uses separate loopback
ports from the running campaign and never opens a personal save.

The active staged curriculum remains on its separate frozen checkout. This
English feature does not change its seeds, policy, evaluation interface or scores.

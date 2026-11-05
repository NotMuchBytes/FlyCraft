# Companion follow validation

Reviewed November 5, 2026 (Asia/Amman); live evidence captured October 31.

## Implementation

The opt-in singleplayer companion creates a separate survival player without
taking over human controls. `/flycraft follow` selects engineered vanilla
pathfinding; `/flycraft stop` cancels NPC motion and `/flycraft start` selects
the existing neural resource controller. Neural responses from an older mode
are discarded after switching or death. The brain loads only for resource
mode. Per-session traces preserve interactive evidence separately from formal
evaluations. The world-name guard excludes ordinary play worlds.

Following has bounded yaw commands, stop/resume spacing, finite path advancement,
periodic replanning and a bounded stuck/no-route wait. Jump and water-floating
requests are implemented. A common respawn mixin preserves the NPC subtype
during explicit recovery while leaving ordinary player construction unchanged.
Initial death recovery may place the NPC on dry ground near its owner; ordinary
following has no catch-up teleport. See [usage and input disclosures](companion_play.md).

The 26.3 port is built in a separate directory, preserving the 26.2 baseline.
It updates changed packet/swing signatures and the rendered-camera callback,
and excludes the obsolete GLFW window redirect on the SDL client. OBS accepts
explicit SDL window-class/process settings while preserving legacy defaults.
The client recording helper only labels/captures the game window; it does not
change human input, menus or settings.

## Verification

The pre-follow regression suite had 100 passing tests. Final verification on
November 5 passed **101 tests in 23.052 seconds**. The follow increment
adds a Java assertion runner exercised by the Python suite: spacing/hysteresis,
yaw wrap and speed bounds, unsafe-drop refusal, jumping, no-route water-floating,
invalid poses and a 1,200-tick moving/reversing/stopping-target motor simulation.
That motor simulation is not Minecraft navigation evidence. Both Minecraft
26.2 and the deployed 26.3 source sets compiled with Gradle `assemble`; Java
assertion mains run through Python rather than a JUnit Gradle test task.
The November 5 packaging recheck initially hit a Windows lock in the old
generated headers directory; rebuilding into a fresh output directory passed
all seven assembly tasks in 17 seconds. No source change was needed. All 98
implementation files in the live-run source manifest still match the current
source bytes.

The installed 26.3 JAR SHA-256 was
`7b6f87ceb71485ada5c8dba770f7f436b4af8dd0c9fdfbd3cfe38b85da6647fa`.
The live client used the NVIDIA RTX 4050. Sampled GPU temperatures were
49, 52 and 59 C; these are not continuous peak measurements. CPU temperature
was unavailable. Minimum sampled available RAM was 757.55 MiB, briefly below
the recording guard threshold without meeting its consecutive-sample stop rule.

## Actual Minecraft result

One interactive session in the copied `FlyCraft Companion Test 2026-10-31`
world demonstrated an alive NPC following the human. No movement commands were
injected into the human player. The human used their own controls and game
commands, including teleporting to the NPC; this is not a controlled experiment.

| Descriptive trace measurement | Observed value |
| --- | ---: |
| Follow samples | 93 |
| Walking samples | 24 |
| Near-owner samples | 37 |
| Turning/unsafe-drop samples | 25 |
| No-route / waiting-to-replan samples | 2 / 5 |
| Distance to owner, minimum / maximum / last | 0.982 / 6.114 / 2.654 blocks |
| Path length from sparse position samples | 18.771 blocks |
| Movement sampled after a forward command | 12.890 blocks |
| Observed NPC deaths | 0 |

Sparse samples and human collision/teleport/interference prevent attributing
every displacement to the controller. Spacing is a stopping threshold, not a
guarantee that a human cannot walk closer. No success rate or confidence interval
is appropriate for this single interactive demonstration.

The server acknowledged the operator follow request with `alive=true` and
`following=true`. The user also issued follow in chat. The world/client exited
normally before the planned stop acknowledgment; the supervisor consequently
retains `failed_preserving_evidence` and `No server acknowledgment for stop`.
The stop/resume check is incomplete, not a passing test. Its pending stop request
was cancelled and archived so it cannot affect a future session. Respawn,
water/cliff safety, logout/dimension transitions and repeated live recovery
remain unverified. An earlier companion drowned before this follow increment;
the absence of death in this check does not prove that problem resolved.

## Recording and provenance

The milestone produced `FlyCraft_Companion_Follow_20261031.mp4`: H.264,
1920x1080, 30 fps, 104.7 seconds, 82,867,375 bytes. Full FFmpeg decoding passed.
Its SHA-256 is
`20682a7e76a60a83c18dc9d5aae8852785f9ad91db6ff2af789780e605e2a90a`.
The descriptive filename is a byte-identical copy of the original recording;
no actions were edited or replayed. Footage includes setup, actual following
and a blank tail after Minecraft exited. Independently captured Minecraft/OBS
frames matched under the predeclared RGB-error threshold (.06226 <= .10).

Local evidence is in the chat workspace `outputs/` and
`work/follow_live_20261031/`, with the raw trace retained in
`.runtime/companion_20261031/headless.1793426950651.jsonl`. Portable summaries
are preserved in `experiments/companion/follow_20261031/`.
Earlier interactive resource-companion sessions have logs but no MP4; this
follow recording does not retroactively cover them. No footage was fabricated.

## Scientific boundary and next work

Following is engineered assistance using owner coordinates and server collision
knowledge, outside the resource-policy observation contract. No neural learning,
neural contribution, autonomous log collection or natural-terrain resource
success is established here. There were zero training updates or checkpoint
writes in this increment; the 139,255-neuron architecture is preserved.

The existing controlled-fixture 27/30 log and 21/30 plank results remain
historical, separate results. Phase 7.5 and Phase 8 remain incomplete. Next
validate recorded stop/resume and explicit respawn, then return to bounded
mining-interruption, connection-loss and pickup-recovery trials with inventory
confirmation. Broader matched neural ablations remain necessary before claims
of learning gain or a large world campaign.

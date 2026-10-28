# FlyCraft Phase 9 development report

Date: 2026-10-28. Status: **in progress; not a completed 10,000-world experiment**.
Phase 8's longer-goal targets and Phase 7.5's strict 30-trial reliability gate
also remain unmet. Earlier reports, checkpoints and experimental data are kept.

## Implemented development increment

- A real dedicated-server survival actor can run without a graphical agent
  client, using the existing 139,255-neuron controller and frozen readout.
  Optional spectator rendering is separate from policy decisions.
- Bounded camera movement and crosshair-only mining are preserved. The actor
  uses ordinary mining progress, player physics and inventory item pickup.
  Headless plank transactions exist but have not been validated live.
- Terminal snapshots, inventory-ledger sealing and acknowledgment prevent
  delayed observations or late pickups from changing an expired episode.
  Missing/unexecuted terminal actions do not update the readout.
- Direct JVM launch after Gradle preparation removes concurrent build-runtime
  overhead. Bounded heaps and RAM/temperature guards remain active.
- Memory use after controlled neural initialization fell from 242.613 to
  88.180 MiB, with exact matching neural outputs over six tested windows.
  Graph architecture, normalization, population indices and checkpoints are
  unchanged. Diagnostic raw graph access is lazy.
- The latest supplied `Skin.png` is installed unchanged as a local actor skin
  (SHA256 `5f078360e27e104e3ca626996adb6f88f547bad440a72c8b4be966534ac8713c`).
  It is visibly present in the accepted recording; it is not an online account
  skin upload.
- Mandatory milestone video validation now includes actual-window image
  preflight, complete MP4 decode, checksums and preserved failed attempts.
  No footage is generated from synthetic AI actions.

## Real Minecraft results

These are small flat survival fixtures near prepared trees. They do not test
natural forest exploration or 30 independent unseen environments. All completed
headless trials used a frozen Phase 8 policy; **Phase 9 training updates: zero**.

| Attempt | Completed episodes | Actual result | Recording status |
| --- | ---: | --- | --- |
| `headless_smoke_01` | 1 | 0/1; incorrect initial spawn left the actor falling away from its fixture | Missing MP4; original data retained |
| `headless_recorded_redo_01` | 0 | RAM guard; no scored trial | No confirmed milestone MP4 |
| `headless_recorded_redo_02` | 1 | 1/1 log; block and inventory confirmed | Rejected: MP4 showed wallpaper |
| `headless_recorded_redo_03` | 0 | Client compilation failed before world launch | No MP4; launcher evidence retained |
| `headless_recorded_redo_04` | 1 | 1/1 log; block and inventory confirmed | Accepted: real Minecraft MP4, full decode and visual inspection |

Attempts reuse development seed/layout 44556777 and differ in implementation
while debugging. Do not pool their outcomes into a generalization success rate.
Each successful worker generated one world instance and ran one episode;
these are not distinct unseen seeds. No official cumulative counter is started.

The accepted redo used two sampled actions, COLLECT_LOG and FORWARD. The game
ended after 75 ticks (3.75 game seconds), with one confirmed block change and
one inventory log. Controller elapsed time was 3.747 seconds and terminal
acknowledgment arrived one tick after scoring. Both game JVMs exited with code
0. The whole supervised job, including preparation and connection, took
85.957 seconds. Peak sampled GPU temperature was 47 C; minimum available RAM
was 2355.906 MiB. Peak sampled process-tree RSS was 114.676 MiB for the bridge,
622.781 MiB for the server and 988.559 MiB for the spectator client. CPU
temperature was unavailable.

The 20.4-second accepted video contains 612 decoded H.264 frames at 30 FPS,
1920x1080 output from a 1280x720 Minecraft window. SHA256:
`a0d46504b199dc49e68d67fe068db216d6aa6e314f352e10ee74010039e26ec6`.
The recording was active before the start gate and retained through terminal
results and shutdown. A manually inspected frame shows the supplied skin in
Minecraft. Initial game tutorial/chat-warning overlays are visible; they have
not been edited out. This is a new execution, **not a replay** of the failed
original. Original missing/rejected footage remains explicitly reported.

The frozen checkpoint SHA256 was
`51f9593274dbbd87c4c9ab2877a0fc2ebd1573ae31831b8957b3b01601e427ca`.
Per-run source manifests and gameplay/action/observation logs remain local at
`experiments/phase9/<run-id>/`. The accepted MP4 and metadata are under
`recordings/phase9/`. Large runtime files, videos and raw logs are Git-ignored.

## Root causes fixed and verification

The headless prototype initially used the player's constructor position rather
than Minecraft's adjusted spawn. It now places the player at vanilla spawn
before fixture setup. The observation sector boundaries were aligned with the
graphical adapter. Terminal lifecycle checks and explicit boundary delivery
prevent stale actions/late inventory packets from being credited to a trial.

The previous recording used OBS Automatic capture with fallback window
matching. It could record wallpaper for this background OpenGL window. The
replacement uses Windows Graphics Capture and an exact unique window title.
Before AI actions, the runner compares an actual game-frame screenshot with an
independent OBS screenshot. The accepted run's normalized RGB error was 0.03066
against a 0.10 threshold. A correct preflight is not continuous frame-content
verification; exported video is also decoded and visually inspected.

The latest full suite passed **74 tests in 17.153 seconds**. Tests cover
terminal delivery, late/inconsistent inventory, missing acknowledgments,
unexecuted actions, Java launch argument handling, OBS ownership/framing and
capture configuration, real codec decode/remux/copy, image mismatch rejection,
existing autonomy/learning/checkpoint behavior, and camera kinematics.
Fabric preparation and client/server compilation passed in the accepted run.
Unit tests alone are not evidence of autonomous Minecraft success.

## Learning and neural contribution

There is no new Phase 9 training comparison or causal neural-contribution
result. A frozen checkpoint's successful two-action development episode does
not establish learning. Phase 8's assisted 29/30 one-log result and tiny strict
camera comparison remain separate in `PHASE_8_REPORT.md`; assistance differs.
The architecture still uses semantic rays, engineered goals/recovery, prepared
fixtures and bounded action transactions. These are not learned components.
The recording camera follows the actor, but never aims or moves the actor.

## Remaining work and recommendations

Complete independent multi-seed strict one-log validation before expanding
claims. Validate headless planks, interruption/disconnection recovery and
checkpoint restoration in real sessions. Implement a transactional world
scheduler, crash/resume/manual-stop protocol, separate development/final seed
sets, matched five-condition policy evaluation, dashboard and measured worker
throughput. A complete faithful replay mechanism is still absent; operator
fixture snapshots are not enough to reconstruct full game RNG state.

The 10,000-world experiment, untouched 100-world final benchmark and official
milestones have not begun. No overnight training was launched. Obtain explicit
authorization only after the development pilot and frozen configuration are
reviewable. Continue to respect the 60% weekly limit and stop starting new
development around 55%; report only actual usage telemetry.

See `docs/phase9_architecture.md`, `docs/phase9_training.md`,
`docs/phase9_recording.md` and `docs/phase9_evaluation.md` for the current
implementation boundaries.

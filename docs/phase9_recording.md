# Phase 9 recording and evidence

Every milestone requires a playable MP4. A unit-test fixture is never footage.
No new AI actions are substituted into an old episode's recording. Development
reruns are labeled `new_execution_not_replay` and retain their original attempt.

The isolated OBS collection captures only the uniquely titled Minecraft
spectator window. Windows Graphics Capture (method 2) and exact-title matching
(priority 0) are required. Automatic mode had selected a capture path which
produced the wrong image for a background OpenGL window. In particular,
`headless_recorded_redo_02` collected a real log, but its video showed wallpaper.
Its original gameplay logs remain valid; its milestone footage is rejected.
The aggregate metadata preserves this distinction and the old metadata is kept
as `run.pre_visual_review.json`. Rejected video copies use `FAILED_CAPTURE_`.

Before releasing the episode start gate, the current runner requires active
owned OBS recording, a ready spectator, the selected NVIDIA renderer, and an
image match between an actual Minecraft framebuffer screenshot and OBS's
screenshot. Images are decoded to 32x18 RGB; normalized mean absolute error
must be at most 0.10 and the game image must pass a brightness check. This
preflight catches the observed wrong capture. It is not continuous verification
of every video frame; inspect exported footage as well.

The 2026-10-29 pilot exposed another preflight failure: a one-time internal
screenshot could capture an early sky-only render while OBS showed the settled
spectator correctly. The observer now waits several rendered frames and retries
framebuffer capture until the gate opens. The runner compares recent independent
image copies, then freezes the verified proof bytes. The image-error threshold
is unchanged; no actor action starts before a match.

Earlier coordinator development episodes were all recorded, including policy
failures and operator interruption tests. Interrupted mining has a partial MP4,
explicitly marked incomplete. Its later retry is a new execution with its own
recording and attempt ID. An unscored startup recording is not a successful task
video. Preserve original failures and report missing/partial milestones.

Lua control uses complete command/status frames, ownership tokens, a 60-second
heartbeat watchdog and safe stop semantics. It refuses to take over unrelated
recordings. It never sends desktop input. Recording starts before the AI gate
and ends after terminal results and natural game shutdown. The AI cannot read
observer camera movement or capture state.

`tools/milestone_video.py` checks container, video stream, positive duration and
full FFmpeg decode. It copies an MP4 byte-for-byte or stream-copy remuxes an
existing recording without synthesizing frames. SHA256, dimensions, frame
count and duration are retained. Portable FFmpeg/ffprobe live under `.runtime`
and were downloaded with release SHA256 verification; they are not installed
system-wide. The test suite's generated video is temporary codec test data only.

Original recordings remain local. Accepted milestone exports belong under
`recordings/phase9/`; metadata under `recordings/phase9/youtube/` links policy
hashes, original episode logs, recording mode and coverage status. A new run
cannot repair missing footage from an old run. Current missing/rejected attempts
include `headless_smoke_01`, `headless_recorded_redo_01`,
`headless_recorded_redo_02` and the pre-launch compilation failure
`headless_recorded_redo_03`. These are not completed official milestones.

Additional 2026-10-29 startup failures are retained under
`headless_terminal_fix_01` and `dev_pilot_20261029`: two stopped at the RAM guard
and one encountered a Windows status-file sharing race. No scored episode
occurred. A later `dev_pilot_20261029_b` uniform-control attempt never passed
preflight and is retained as partial evidence. Its correct OBS view was not used
to bypass the failed internal screenshot. Changed configurations use new
development campaigns and preserve their source manifests.

## User-selected milestone-only recording (October 29)

The user subsequently requested **only milestone recordings**. New CLI campaigns
default to `--recording-policy milestones`; the Phase 9 schedule is episodes
1, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 7500 and 10000. An explicit
`--recording-milestones 1,10,25,30` can add the final 30-trial reliability
challenge. This frozen selection is operator metadata, never a policy input.

Routine episodes run the same survival actor/controller without any graphical
client or OBS recording, retaining game, action, observation, reward, inventory,
terminal acknowledgment and checkpoint evidence. Their absent MP4 is intentional
and labeled event-only. Milestone episodes still require the independent
spectator, verified capture gate, complete decode and unchanged video checksum.
A failed required recording cannot be silently downgraded to an event-only run.
Milestone outcomes are recorded whether the policy succeeds or fails.

Legacy campaign configurations retain their original all-episode recording
requirement. Two trials already launched under the previous 30-trial plan were
allowed to finish and their recordings retained. The source-freeze guard then
prevented additional launches. That superseded plan and its failure/success
remain separate from the new fixed-plan evaluation after the user's change.

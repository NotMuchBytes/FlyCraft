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

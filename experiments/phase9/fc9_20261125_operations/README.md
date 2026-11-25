# Official launch and user-requested host operations

The **10,000-world training campaign started on 25 November 2026**. Its frozen
plan is in `../fc9_20261125/`. Source SHA256 is
`90a18f3f4e206b93115dfd6458a9fef5aa31255f2b40e6f81955bd3d6108c1b7`.
The initial four worlds scored **3/4**: one-log 1/1, three-log 1/1, planks 1/1,
pickaxe 0/1. The failed pickaxe reached sticks but missed its fixed 1,500-tick
budget. All four readout changes passed the independent checkpoint gate. These
are sequential training outcomes, not held-out reliability scores.

All four scheduled milestone MP4s passed complete decode, episode coverage,
capture-content and hash checks. Manual sampled-frame review confirmed real
Minecraft-only footage, without desktop/screensaver capture. Normal Minecraft
tutorial overlays are visible. [Launch audit and local video paths](launch_audit.json).
Raw first-four evidence and their independent checks are archived in the repo.
Routine world directories are reclaimed only after verification; milestones,
readouts, logs and all unverified evidence remain preserved.

After the plan was frozen, the user requested a bouncing “DO NOT TOUCH”
screensaver, local clock, real completion progress and **“also shutdown once
your done”**. These are host operations, separate from the immutable Minecraft
actor/runner. `screensaver.py` is a preserved copy of the deployed temporary
desktop display. It reads the actual campaign summary; it invents no progress
or completion time. Esc closes it. Its live copy is under the chat's `work/`.

`finish_when_verified.py` is a separately deployed, read-only completion
companion. The shutdown authorization is interpreted as **after all 10,000
training world slots**, not after setup or the chat reply. It requires the
executor's completed-budget marker, no active worker, no STOP/attention request,
the unique seed/goal schedule, a frozen final checkpoint and all scheduled
milestones. It rehashes preserved graph/checkpoints and every committed episode's
audited evidence, then full-decodes all milestone MP4s again. Only then does it
wait 60 seconds, release the temporary shutdown block, and request ordinary
Windows shutdown with `/s /t 0`, **without `/f`**. Applications may still block
shutdown. Critical battery remains Windows-controlled.

The companion was started hidden with `--shutdown-on-complete`. Four synthetic
tests validate rejection of incomplete/active/stopped/contradictory campaigns,
milestone omissions, cancellation and the nonforced command. No real shutdown
was triggered in tests. The core suite passed 145 tests before live launch.

Create this file to cancel automatic completion shutdown:

`C:/Users/anass/Documents/Codex/2026-11-17/continue-developing-the-actual-flycraft-minecraft/work/completion_guard_20261125/CANCEL_SHUTDOWN`

Its neighboring `status.json` reports actual state. Creating the campaign STOP
file interrupts training safely and prevents completion shutdown. Ordinary RAM,
disk and thermal recovery is bounded and automatic; unknown/integrity failures
preserve evidence and stop. A standalone handoff cannot wake an idle Codex chat
or patch arbitrary code. Source changes require reviewed versioned continuation.

The user also requested maximum fans. The official HP OMEN Gaming Hub was
installed from Microsoft Store, but its Victus Performance Control panel reports
missing HP services and says its update will reboot the PC. That update was not
applied during training; **maximum fan speed has not been set**. The existing
75°C GPU guard remains active. No BIOS/embedded-controller writes were used.

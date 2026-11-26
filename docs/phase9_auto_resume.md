# Windows automatic resume — November 26, 2026

The user requested automatic continuation when the PC is turned on. On this
machine a limited-user Task Scheduler job and an independent per-user Startup
shortcut are installed. Both start the windowless Python bootstrap after
**Windows sign-in**, without opening Codex or a terminal. A disabled boot-task
registration check returned **Access is denied**. Pre-login startup was not
installed; Windows requires administrator rights for a boot trigger. No
password, automatic sign-in, system security setting or reboot was requested.

The installed task is `FlyCraft_AutoResume_20261126`; the fallback shortcut is
`%APPDATA%/Microsoft/Windows/Start Menu/Programs/Startup/FlyCraft Auto Resume.lnk`.
Its executable is the existing environment's `pythonw.exe`. VBScript is not
available on this Windows installation, so no script-engine dependency is used.
The persistent machine plan and live status are under
`%LOCALAPPDATA%/FlyCraft/Resume/`. The checkout it operates is
`C:/Users/anass/Documents/Codex/FlyCraft-curriculum`.

## Recovery behavior

- One OS-backed supervisor lease, the campaign coordinator lease and existing
  Minecraft worker lease prevent duplicate owners. PID checks also compare
  process creation time and command identity, preventing PID-reuse mistakes.
- A crashed supervisor restarts after a 15-second backoff and adopts an
  existing verified runner. A real test killed only the supervisor: it came
  back in about 16 seconds with the same runner and no altered/replayed game
  actions. The PC was not rebooted for this test. A second restart loaded the
  final critical-battery logic and again preserved the runner.
- A completed episode is re-audited and committed once. An ordinary interrupted
  training world with no native score keeps its evidence, consumes a generated
  world slot, retains the previous committed checkpoint and starts a fresh
  episode/seed. It never resumes a mining command or credits an unacknowledged
  action. Technical recovery is bounded to three per hour; evaluation retries
  are additionally bounded by the existing two-retry setting.
- Scored, partial-score, contradictory or interrupted recorded episodes park
  for review. A technical evaluation retry is allowed only when no score exists,
  and the new execution explicitly names the earlier attempt as `redo_of`.
- A manual `STOP`, code/config mismatch, failed quality gate, unresolved evidence
  request or unimplemented next skill prevents new launches. The watchdog
  neither changes code nor lowers a gate. `DISABLE_AUTOSTART` in the resume
  directory prevents automatic relaunch; use campaign `STOP` to pause the
  running training too.

The power guard and completion verifier are restarted/adopted separately.
The Windows sharing violation that had stopped the prior power guard is
fixed: bounded atomic-publication retries keep native protection alive even
if status publication stays locked. At unplugged battery <=5%, the guard
requests STOP and releases its shutdown block. The watchdog does not restart
guards or training at critical battery. Only a STOP proven to have been
created by that critical-battery event can be cleared automatically, after
external power is connected and charge exceeds 10%. Manual STOP remains intact.

The existing 768 MiB live RAM reserve, 2,048 MiB free-disk reserve and 75°C GPU
cutoff remain. Launch still requires a 30-second healthy window at 1,800 MiB
available RAM, or 3,000 MiB for milestone recording. Waiting for resources is
not a completed episode. CPU temperature remains unavailable. Final shutdown
still requires the complete authorized campaign and freshly verified artifacts;
the failed gate or this repair round ending cannot trigger it.

## Bounded retention repair

The first stage finished 64 training trials with 42 successes and 56 verified
updates. Its 270 completed evaluation episodes scored terrain trained 25/30,
frozen 19/30, uniform 4/30, no-neural 0/30 and shuffled 11/30. Retention was
one-log **20/30**, three-log **30/30**, planks **25/30**, pickaxe **29/30**.
The one-log gate failed; those results remain immutable. All 334 episodes were
re-audited without score changes. These are controlled fixtures, not proof of
natural-terrain or unseen-layout generalization.

Execution revision 3 archives the ledger/source/config at world 402. It starts
one reviewed 32-world repair round from the same committed checkpoint, using
three ordinary one-log retention tasks followed by one terrain task. Original
training seeds and the 10,000-world total budget are preserved. The repair has
150 newly frozen evaluation seed identities: 30 shared across the five primary
conditions and 30 per wood retention goal, for 270 fresh evaluation episodes.
The old evaluation and the natural-stage seed allocation are not reused.
The actor, reward, observation interface, action budgets and target thresholds
are unchanged. If the new candidate fails, it parks again instead of advancing.

The first repair world, official slot 403, collected a log in six actions with
a verified readout update. This is a training result, not a reliability score.
All **180 tests pass**, including restart, duplicate-ownership, critical-battery,
manual-stop, scored-evidence and repair-round separation checks.

Source, completed-stage audit, installation proof and restart-test records:
`experiments/phase9/autostart26_operations/`. The startup registration can be
recreated explicitly with `install_startup.ps1 -Plan <local-plan.json>`; cloning
the repository does not install an automatic startup task.

Microsoft documents boot-trigger administrator requirements in
[TaskFolder.RegisterTask](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskfolder-registertask).

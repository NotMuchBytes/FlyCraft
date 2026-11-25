# Temporary training power guard

The user authorized blocking ordinary shutdown on 25 November 2026, except on
critical battery. `tools/power_guard.py` owns an invisible Windows window with
an explicit shutdown-block reason and requests continuous system availability.
The display can still turn off. No power-plan settings are changed.

When unplugged at **5% battery or lower**, the guard creates the supplied
campaign STOP file, releases its shutdown block and sleep request, and exits.
This requests the existing worker's safe interruption; it cannot guarantee that
Windows will wait for checkpoint completion during critical power loss.
Windows' critical-battery action remains in force. Forced shutdown, “shut down
anyway”, a physical power-off, and loss of power can override the guard.

Example, run with the project's virtual-environment Python in a hidden process:

```powershell
.venv/Scripts/python.exe tools/power_guard.py --state-dir C:/path/to/guard-state --stop-file C:/path/to/campaign/STOP
```

`status.json` reports the current battery sample, process ID, active requests,
and exact stop/release paths. Create `RELEASE` in that state directory to remove
the guard without stopping training. This is a process-scoped guard: exiting
the process or rebooting removes it; it does not install a service or startup
task. Remove or archive a prior RELEASE file before explicitly starting it again.

Validation: unit tests cover the unplugged 5% threshold, critical STOP and
release, and manual release. A native Windows smoke test registered both API
requests, reported active at 90% unplugged, then released via its RELEASE file.
No actual shutdown or battery depletion was triggered for testing.

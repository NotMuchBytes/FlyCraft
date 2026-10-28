# FlyCraft graphics selection on Windows

Date: 2026-10-28. This records the current laptop's configuration and live
evidence. It is not a claim that all neural computation runs on the GPU.
The existing sparse SciPy brain and learning pipeline are preserved.

## Setting and verification

The dedicated executable
`C:\Users\anass\Documents\FlyCraft\.runtime\jdk-25\bin\java.exe`
now has `GpuPreference=2;` under
`HKCU\Software\Microsoft\DirectX\UserGpuPreferences`, with the executable's
absolute path as the value name. This selects the application's high-performance
GPU on this two-adapter laptop. Its prior value was absent and was recorded in
the chat workspace's `work/nvidia-gpu-preference-before.json` before changing it.
Removing that one named value restores the previous preference. No global GPU
preference, driver, display-adapter enablement or other application's setting
was changed. No desktop input or window activation was used.

Windows documents the per-application **High performance** choice in
[Graphics preferences](https://support.microsoft.com/en-us/windows/hardware/display-graphics/optimizations-for-windowed-games-in-windows-11).
The registry form is also used by the upstream
[3D Slicer installer](https://github.com/Slicer/Slicer/blob/main/CMake/SlicerCPack.cmake).

The supervised runner defaults to OpenGL, records the actual backend/device
lines, and refuses to open the trial gate until the selected device identifies
NVIDIA. A log saying only `Preferring discrete GPU` does not establish the
renderer actually used it. Unsupported selection aborts without policy trials.
The explicit `--graphics-backend` options remain available for diagnostics.

## Crash evidence and limitations

The original native application error was an access violation (`0xc0000005`)
in AMD's `atio6axx.dll`, version `32.0.22042.8003`, fault offset `0x139563`.
Windows Application Event 1000 records three instances at 15:45, 16:37 and
16:55 local time. The latter two rendered with Vulkan on the NVIDIA RTX 4050
but still crashed after Minecraft logged `Stopping!`. NVIDIA rendering alone
therefore did not solve shutdown. The exact driver-internal cause is unknown.
The event evidence is preserved in
`experiments/phase8/gpu_crash_diagnosis_20261028.json`.

After applying the application preference, `nvidia_opengl_log_before_01` logged:

```text
Using graphics backend OpenGL, using drivers: 3.3.0 NVIDIA 617.42
Using graphics device: NVIDIA GeForce RTX 4050 Laptop GPU/PCIe/SSE2 (NVIDIA Corporation)
```

That run completed three inventory-confirmed one-log trials and both the
Minecraft client and server exited with code zero. Its maximum sampled GPU
temperature was 48 C and minimum sampled available system RAM was 1385.84 MiB.
Its movie is identified in its `run.json`. This is a successful bounded live
test, not proof that every future graphics shutdown will be reliable. The
runner records nonzero/native exits separately from in-game task outcomes.

The matched bounded-camera run `nvidia_opengl_log_after_01` also exited with
code zero on both client and server. It scored 2/3 before the game deadline,
stayed at or below 48 C and retained at least 1687.29 MiB available RAM in the
samples. That task result is documented separately from graphics reliability.

All new live trials require Minecraft-only OBS recording and retain the
75 C sampled GPU guard. Three consecutive samples below the configured RAM
reserve abort owned processes. The machine supplies no CPU temperature reading.

An independent lifecycle bug also prevented a disconnected client from polling
the suite-complete file. Control polling now occurs before checking for a
player/level, allowing the test client to close normally after the server ends.
Cleanup tolerates inaccessible Windows crash-reporting processes without
terminating those OS reporters or skipping the remaining owned processes.

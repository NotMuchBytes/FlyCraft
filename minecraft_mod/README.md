# Example Mod

## Setup

For setup instructions, please see the [Fabric Documentation page](https://docs.fabricmc.net/develop/getting-started/creating-a-project#setting-up) related to the IDE that you are using.

## License

This template is available under the CC0 license. Feel free to learn from it and incorporate it in your own projects.
# Phase 7 extension

The bridge now includes optional world-session, player-pose and ray-distance
telemetry for bounded goal navigation. Legacy Phase 4–6.5 modes are retained.
`flycraft-phase7.enabled` selects a one-scene navigation smoke harness in a
fresh disposable server runtime. It places a marker and measures outcomes;
all actions still come from Python's neural readout. Resource collection and
crafting are not supported by this client yet.

Optional Gradle properties `flycraftBuildDir`, `flycraftRunDir`, and
`flycraftServer` support builds/runs outside OneDrive and a chosen loopback
test port. See `../docs/phase7_usage.md`.


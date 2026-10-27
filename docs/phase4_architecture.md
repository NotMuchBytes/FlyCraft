# Phase 4 Minecraft bridge architecture

```text
Minecraft 26.2 client raycasts
    -> visible gold target sector (five rays; no coordinates exported)
    -> local TCP newline-JSON request with client tick ID
    -> existing deterministic sensory encoder
    -> fixed 139,255-neuron bounded-rate connectome window (18 steps)
    -> annotated visual_projection activity grouped by anatomical side
    -> engineering action decoder
    -> tick-matched Minecraft client action
```

Minecraft and neural simulation remain separate processes. The Java Fabric mod owns world observation and action execution. `minecraft_bridge.py` owns graph loading, neural dynamics, readout, and logging. IPC uses Python/Java standard-library TCP on `127.0.0.1:8765`; there is no remote service or extra IPC dependency.

Only one request may be outstanding. Every request and response carries a tick ID. The client applies an action only when the response tick equals the observation tick and exceeds the last applied tick. This prevents duplicate and stale actions.

The client casts horizontal rays at -40, -20, 0, +20, and +40 degrees and reports the sector only when the first blocking hit is a gold block. It does not send target coordinates. The decoder does not receive sector labels directly; it sees only integrated continuous activity from neurons selected by `super_class=visual_projection`, split by their annotation `side`.


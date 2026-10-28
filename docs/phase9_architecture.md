# Phase 9 development architecture

Status: bounded development pilot; the 10,000-world experiment has not started.

`tools/run_phase8_live.py --headless` launches a dedicated Minecraft 26.2
survival server, an embedded survival player, and the existing Python neural
controller. The server supplies real physics, mining, crafting and item pickup.
The embedded connection uses an in-memory Netty channel; it is not a graphical
client. A single asynchronous policy request can be outstanding. Optional
`--spectator` adds an independent graphical recording client. That client's
camera follows the actor solely for filming and provides no policy observations.

The graph remains 139,255 neurons. Its normalization, neural window and learned
readout are unchanged. Releasing the raw graph after normalization and streaming
metadata selection reduced measured post-initialization controller RSS from
242.613 to 88.180 MiB. Six controlled neural windows matched exactly before and
after, including selected populations and normalized matrix bytes. The raw
graph remains available lazily to diagnostic callers. See the two retained
`experiments/phase9/runtime_memory_*.json` measurements.

Gradle prepares classes, assets and explicit Java launch specifications, then
exits before the runtime starts. `tools/java_launch.py` starts dedicated JVMs
directly with bounded heaps. The runner samples process-tree RSS, available
RAM and NVIDIA temperature. It stops after repeated RAM reserve violations or
GPU temperature reaching 75 C. CPU temperature is unavailable on this laptop.
This is not yet a multi-worker scheduler or a measured parallel throughput test.

## Observation and assistance boundary

The headless adapter exposes the same fifteen semantic collision rays used by
the graphical adapter: five yaw offsets (-40,-20,0,20,40 degrees), three pitch
offsets (-30,0,30), range 12 blocks. Rays reveal only their first collision;
visible logs and visible dropped log items supply resource sectors. Dropped
items require line of sight and field-of-view checks. Own position/orientation,
own inventory counts/revision, and action acknowledgments are exposed. Seeds,
hidden block maps, goal success labels and fixture coordinates are not policy
inputs. This is a semantic Fabric abstraction, not a pixel-only agent.

The learned readout selects actions. Camera motion uses the existing bounded
motor; interaction requires the actual crosshair to hit a reachable block.
There is no automatic block aiming. Forward movement uses normal player
physics; item pickup is vanilla inventory pickup. The adapter currently supports
one-log and plank goals. Planks use normal 2x2 inventory-menu transactions;
headless plank success remains unvalidated. More complex headless crafting is
not implemented. The old learned action set has no pitch action.

The operator creates small tree fixtures near spawn and resets episodes.
That preparation is engineered assistance, not learned tree search. Initial
fixture snapshots are operator-only audit data and are not policy observations.
They do not include complete RNG state and are not a faithful replay system.

## Episode boundary

The harness freezes a terminal inventory/pose snapshot at its scoring tick,
sets the episode inactive and waits for the controller's acknowledgment.
The controller seals that episode's inventory ledger. Later pickups cannot
change its result. Missing or unexecuted terminal actions are excluded from
learning; an acknowledgment timeout is recorded explicitly. Client and headless
adapters recheck lifecycle state before applying delayed policy responses.

## Remaining infrastructure

There is no completed serial/multi-worker training orchestrator, official seed
catalog, isolated 100-world development and final evaluation sets, dashboard,
transactional world counter, or complete resume/crash recovery protocol yet.
The existing worker can request learning, but the development headless trials
used for initial validation kept the policy frozen. A subsequent one-episode
development training trial updated the existing readout from real feedback;
its saved checkpoint loaded successfully. This does not establish improved
generalization. See `PHASE_9_REPORT.md` for the bounded results.
An official 10,000-world launch needs explicit authorization after pilot review.

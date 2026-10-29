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
one live empty-inventory plank pilot passed on October 29, with four planks
confirmed in inventory. Repeated reliability remains unvalidated. More complex
headless crafting is not implemented. The old learned action set has no pitch
action.

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

## Development coordinator

The 2026-10-29 increment checks fresh episode identities immediately before
execution. A passive terminal pickup updates inventory memory and goal progress
without adding an executed action. Its outcome bonus is recorded separately as
`unattributed_terminal_reward`; learning is suppressed when the reward cannot
be safely assigned to an acknowledged command. Later pickups remain excluded.

`autonomy/experiment.py` and `tools/run_phase9.py` implement a serial development
coordinator. Each invocation permits 1-5 episodes and at most 900 seconds. A
campaign permits up to 100 generated pilot worlds, including interrupted
instances. OS file leases prevent simultaneous coordinators and workers. The
worker detects coordinator loss and shuts down its owned processes.

Configuration, source manifest, seed catalog and checkpoint hashes are checked
before each attempt. Disjoint SHA256-derived partitions contain 100 pilot,
10,000 reserved training, 100 development-evaluation and 100 final-evaluation
seeds. Catalog creation does not generate worlds or authorize official training.
Changing behavior code requires a new development campaign.

An attempt is durable before launch. Commitment requires server/controller
agreement, terminal inventory/acknowledgment, clean game exits, checkpoint
integrity, a measured readout change matching the report and a verified MP4.
Interrupted attempts preserve evidence and leave the committed policy unchanged.
Resume uses a fresh attempt identity; reused seeds and extra generated instances
are counted separately. Pending commands are never replayed. A STOP file requests
safe interruption and its acknowledgment is archived when cleared explicitly.

Atomic state updates retain the old full file until replacement succeeds, with
bounded retries for Windows reader-sharing locks. The dashboard distinguishes
instances, seeds, episodes, nonzero updates and estimates. Its neural panel uses
actual logged features, action probabilities and peak activity; requested actions
are labeled separately from game execution.

Only verified one-log training is enabled. There is no automatic curriculum
advancement or official 10,000-world executor. Parallel throughput, full RNG
replay, long-run memory stability, natural terrain and longer goals remain
unverified. See `PHASE_9_REPORT.md` for actual results. Explicit authorization is
still required for the full experiment after pilot review.

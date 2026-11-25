# Launcher optimization and bounded control publication

25 November 2026. The user requested a faster runner after the measured
remaining duration approached nine days. The official campaign was stopped
before changing source. It retains **320 scored worlds (280 successes)** and
one unscored, generated world 321. No world count or checkpoint is reset.

World 321 exposed a Windows reader-sharing race: publishing `control.json`
raised `AccessDeniedException`, and Minecraft shut down without a score or
readout update. Its raw logs, crash evidence, world and original attention
request are preserved. The first 320 results are unaffected. The snapshot
checkpoint from world 320 is
`c8799d73bf2668b458e9296687019955e216ee01830e60c715260728baa6a819`.

## Changes under validation

1. **Continuous readiness history:** the launch monitor retains a healthy
   30-second window across episodes, sampling once a second. RAM, disk and
   thermal limits are unchanged. Pressure resets the window; stale telemetry
   cannot authorize a launch. Cold start and pressure recovery still wait.
2. **Verified launch exports:** prepare Gradle/Loom's server/client arguments
   once, then validate the manifest, source, exact hardware profile and SHA256
   of every exported dependency/config/class artifact before each direct JVM
   launch. The current cache binds 217 files (131.9 MiB). No Gradle JVM is
   needed for each new world. Every world/server/agent episode is still new.
3. **Bounded atomic publication:** the harness retries only Windows access-
   denied replacement errors for up to one second, leaving the old complete
   JSON visible until atomic replacement succeeds. A persistent lock still
   fails closed. A native Windows/JDK test verified transient recovery and
   preservation of both original and temporary files under permanent locking.

The actor, planner, neural graph, learning rules, observations, action masks,
camera/movement sizes, fixture layouts, tick rate, episode budgets and success
rules are unchanged. The only harness edit replaces its atomic publication
call; the revision tool verifies that restriction against archived source.
There is no aiming, collection scripting, gameplay time acceleration or
parallel learning. Startup optimizations cannot remove the time spent playing.

## Validation and continuation rules

Separate development runs compare legacy, cache-only and cache plus continuous
readiness with the same checkpoint, world/layout seed IDs, policy RNG, relative
fixtures, action/tick budgets and interface. Two one-log seeds isolate the
changes; recorded pickaxe runs check the longer profile and cached spectator.
All runs disable learning and are excluded from the official campaign.

Fresh Minecraft processes may choose translated absolute spawn coordinates
and different entity/drop RNG despite identical world seeds. These are not
exact replays. Initial snapshots and relative geometry are checked, gameplay
outcomes are preserved, and launcher/waiting time is measured separately from
episode duration. Differences in task success are not treated as evidence of
policy improvement or launcher equivalence by themselves.

Before resuming, the continuation tool requires passing automated checks and
eight independently verified fresh pilot episodes. It archives the original
configuration, source files, source manifest, ledger and attention record;
then records a new execution revision and cache hash. Prior results keep their
original implementation hashes. The original seed catalog, readout chain,
10,000-world total budget, recording schedule and untouched final evaluation
remain in place. With world 321 consumed, continuation starts at world 322.

The completion/shutdown companion checks each episode against its recorded,
permitted execution revision. It must be restarted with that version-aware
validator before resuming the campaign. The power guard remains active through
this work.

## Verified adoption

All **155 automated tests passed** in 19.698 seconds. The separate eight-episode
pilot passed all evidence checks, with seven goal successes, one preserved
ordinary policy failure and **zero learning updates**. Relative initial fixture
geometry, empty inventories, checkpoint, seed IDs and interface were verified;
absolute spawn translations and full entity RNG were not fixed. Both recorded
pickaxes succeeded and their original MP4s passed full decode/content/coverage
checks plus sampled manual review. Normal tutorial overlays remain visible.

| Development configuration | One-log two-trial batch | Mean routine worker overhead | Warmed time outside worker |
|---|---:|---:|---:|
| Legacy export and per-episode readiness | 147.46 s | 27.73 s | 32.40 s |
| Cached export, per-episode readiness | 133.41 s | 20.24 s | 31.87 s |
| Cached export, continuous readiness | 93.37 s | 20.09 s | 2.10 s |

Worker overhead excludes actual episode duration. The batch times include cold
readiness and gameplay, whose outcomes vary across fresh executions; they are
not a controlled learning comparison. The recorded pickaxe batches took
140.95 seconds (legacy) and 105.37 seconds (cached/continuous), each including
cold readiness and spectator startup. No overnight completion is promised.

The reviewed continuation was applied as **execution revision 2**, source SHA256
`00c2b393b74b2ae6bdabb67705893a2472932d28eb2d3d8ac876641f38bfd6da`,
starting at world **322**. It retained all 320 scores, unscored world 321,
the complete seed catalog and the existing readout chain. The original attention
record was archived with a separate resolution. The version-aware completion
watcher was restarted and completion shutdown re-enabled; the power guard stayed
active throughout. The new runner has resumed actual official Minecraft trials.

[Machine-readable pilot validation, timings, episode proofs and video paths](performance_validation_0002.json).
This revision changes execution overhead and publication reliability only.

The user subsequently chose to replace the remaining wood-only budget with a
broader staged curriculum as new skills pass validation. The performance fix
remains useful to that work; its four-goal training progress is a preserved
foundation, not evidence that the additional Minecraft skills already exist.

The first six official revision-2 worlds (322–327) also passed independent
audits, with four successes and two preserved three-log failures. Excluding the
first cold-readiness cycle, their mean complete coordinator cycle was
**48.39 seconds**, versus **82.47 seconds** over the preceding 100 legacy
worlds: about **41% less time per world** in these different samples. This
supports a provisional 5–6-day estimate for the unchanged wood-only workload,
not a promised duration for the broader curriculum. The latter requires new
skills and live timings. [Initial resumed-run evidence](post_revision_322_327.json).

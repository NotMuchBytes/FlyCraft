# Terrain recovery round 2 — November 27, 2026

The user requested continuation after the completed round-1 quality gate failed.
The previous checkpoint, seed catalogs, 636 episode attempts and gate remain
preserved in `before_round2_at434/`. This is an explicit bounded training
revision, not an automatic gate bypass or a retry of a failed scored episode.

## Diagnosis

The locked round-1 candidate scored 19/30 terrain, against frozen transfer
12/30, uniform 0/30, no-neural 0/30 and shuffled-neural 13/30. Eight matched
seeds succeeded only with the trained candidate and one only with frozen
transfer. All four retained wood goals passed: one log 26/30, three logs 27/30,
planks 21/30 and wooden pickaxe 25/30. The primary threshold remains 24/30.

All eleven trained terrain failures saw a log but never completed a block
break. Their median fraction of actions spent turning was 76.25%. Their
trajectories moved several blocks, so this is not simply a stationary spawn
failure or a failure to issue jumps. Nine failures involved left-side trunks.
The first gate's 25/30 used different seeds; frozen transfer also dropped from
19/30 to 12/30. These observations do not isolate forgetting from evaluation
difficulty. Both completed catalogs are now development evidence, not future
held-out evaluation. See `gate_diagnosis.json` and `analyze_gate.py`.

## Frozen recovery protocol

Start at checkpoint SHA256
`795281b35f1e0ee0e04fe818e41b0ca9cd82e9212fee9ac9d084305dfd916828`.
Run exactly 96 additional training-world slots: eight twelve-world cycles,
each containing two primary terrain episodes before each of the four wood
retention goals. This gives 64 terrain episodes and eight episodes per wood
goal. Aborted generated worlds still count toward the 10,000-world budget.
The training catalog and its order are unchanged. Training starts at world
435; this round ends no later than world 530.

Then lock the resulting candidate and run 270 evaluation episodes: 30 primary
seeds across trained, frozen, uniform, no-neural and shuffled-neural, plus 30
retention trials per wood goal. The 150 new seed identities in
`repair_terrain_2` exclude all earlier catalog identities, observed seeds and
reserved final-evaluation identities. This small fixture generator can still
repeat geometry; seed disjointness is not a novel-layout generalization claim.
No evaluation scores select intermediate checkpoints or alter this schedule.

Pass thresholds stay 24/30 primary, 24/30 one log, 21/30 three logs, 21/30
planks and 15/30 pickaxe. The actor, reward, observations, original graph,
policy features, source hash and launch cache remain unchanged. The one
protocol change is joint rehearsal with a larger, predeclared training dose.
This revision is not a controlled causal test of the training mixture alone.

`round2_protocol.json` preserves authorization and archive hashes;
`round2_config.json` and `round2_seeds.json` freeze the successor plan.
`install_round2.py` checks the preceding gate, exact state, baseline tests,
checkpoint, frozen implementation and absent stop/fix markers before installing.
It is a one-shot operational migration, not a general launcher.

The existing sign-in recovery supervisor runs the successor plan. RAM, disk,
temperature, battery and verified-completion shutdown guards remain active.
Only scheduled milestones are filmed, including training world 500. The
English companion stays in the separate development checkout and is not
introduced into this frozen campaign. The original final evaluation is unused.

## Verified restart

The sign-in supervisor launched `fc9_stage25_terrain_00637`, training world
435, without relaxing its checks. It succeeded after 72 acknowledged actions
and 1,128 server ticks. Native evidence confirms a block break and one log in
inventory; the independent checker accepted the terminal evidence. The measured
readout weight delta norm is `0.011433638415420014`, matching the reported
update. Both checkpoint hashes and the unchanged original graph were checked.
See `first_episode_audit.json` and `first_episode/`. This is a verified restart,
not a claim that the recovery round or terrain gate has passed.

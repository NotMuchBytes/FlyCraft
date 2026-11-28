# Retention-focused recovery — November 28, 2026

The user requested continued autonomous work after the completed round-2
failure. Failed gates remain preserved; this is a reviewed new training round,
not permission to skip a gate. The 10,000-world cap and all resource guards stay.

## Completed round 2

The fixed 96-slot batch and all 270 fresh evaluation episodes finished. The
trained terrain candidate scored 28/30, frozen transfer 14/30, uniform 2/30,
no-neural 0/30 and shuffled-neural 14/30. Trained terrain's descriptive Wilson
95% interval is 78.7%–98.2%. These prepared teaching arenas have repeated
geometry; the result does not establish natural exploration or unrestricted
Minecraft skill. Recipe abstractions, semantic rays, masks and planner remain
engineered assistance. The original 139,255-neuron graph remains frozen; only
the linear readout learns.

Wood retention scored 20/30 one log, 30/30 three logs, 18/30 planks and 27/30
wooden pickaxes. Terrain passes its 24/30 point threshold, but the joint gate
fails one-log (24 required) and planks (21 required). Three logs require 21
and pickaxe 15. All thresholds are unchanged.

| Task / condition | Success | Median actions | Median worker seconds |
| --- | ---: | ---: | ---: |
| Terrain trained | 28/30 | 22 | 37.817 |
| Terrain frozen | 14/30 | 80.5 | 78.546 |
| Terrain uniform | 2/30 | 86.5 | 78.988 |
| Terrain no-neural | 0/30 | 80 | 79.094 |
| Terrain shuffled | 14/30 | 81 | 78.477 |
| One-log retention | 20/30 | 9 | 26.958 |
| Three-log retention | 30/30 | 30 | 46.184 |
| Plank retention | 18/30 | 10 | 28.315 |
| Pickaxe retention | 27/30 | 49 | 60.269 |

The native action traces show five one-log failures without a break and five
with breaks but no pickup. All twelve failed plank attempts end with no logs:
nine have no confirmed break, three have breaks without pickup. Their median
turning fraction is 64.1%. The observed regression precedes crafting. Jumps
are being selected; another automatic jump retry is not justified. This is a
diagnosis from the completed evidence, not a causal proof of forgetting: the
fresh catalogs also differ in difficulty. Raw evidence hashes, failure details
and intervals are in `round2_diagnosis.json`; the sealed evidence recheck is
in `round2_reaudit.json`.

## Predeclared round 3

Start from the last trained checkpoint, run 00732, SHA256
`2210e5921c29bb5ec05f828a86cf45c95d8c033e4d3ca74f96f530d860f332f2`.
Use exactly 128 additional generated training-world slots, worlds 531–658:

1. Terrain, one log, planks, terrain, one log, planks, three logs, pickaxe.
2. Repeat that eight-task cycle exactly sixteen times.

This gives 32 terrain, 32 one-log, 32 plank, 16 three-log and 16 pickaxe slots.
It replaces the earlier terrain-heavy mixture with more short-flat rehearsal.
The aggregate dose also changes; it is not an isolated causal test of mixture.
No actor, reward, observation, mask, actuator, per-task budget or training-seed
order changes. Aborted generated worlds consume their slots as before.

Then lock the resulting checkpoint before using any new evaluation seed. Run
30 primary seeds under all five conditions plus 30 seeds per retained wood
goal: 270 episodes. The 150 new seed identities exclude every existing catalog,
previous attempt and locally recorded diagnostic seed. The original final
evaluation is untouched. These seeds may still repeat fixture geometry.
No checkpoint selection from intermediate evaluation or successful-seed fishing
is permitted. Each failed gate remains archived and requires a fresh diagnosis
before another bounded revision.

`install_round3.py` is one-shot and checks both automated baselines, sealed
re-audit, exact failed state, hashes, original graph, absent STOP/fix request and
the campaign lock. It archives state/config/seeds before publishing the new
plan. The existing supervisor resumes it; no second supervisor is started.
The frozen runtime source hash remains
`bb23a1bb328bdf7dee4676f7318a95a69efeedecf0cad5020872f1bb9389868b`.

Successful completion of **all** joint gates permits the existing natural
exploration stage, with its own fresh evaluation and retention gates. Later
stone/food/survival/combat/Nether stages remain implementation work. This
recovery is not completion of Phase 9 or authorization to relabel wood runs
as those later skills. Milestone-only OBS/NVIDIA capture and full MP4 decode
remain required when a scheduled recorded world is reached.

## Verified release

The frozen checkout passed 183 automated tests in 28.832 seconds; the separate
English-enabled development checkout passed 187 in 31.486 seconds. The native
evidence checker then reverified all 270 completed round-2 episodes, original
evidence hashes, unchanged scores and zero evaluation updates.

Execution revision 5 was installed at the archived failed gate. The existing
supervisor launched world 531 (`fc9_stage25_terrain_01003`) without a duplicate
coordinator. It succeeded in ten actions, with one independently confirmed
break and one log in terminal inventory. The measured readout weight delta
norm is `0.03734140027624806`, matching the reported update. The original
graph and runtime source remain unchanged. `first_episode_audit.json` and
`first_episode/` preserve the recheck and copied native evidence. This is a
training result, not an evaluation gate or a natural-world claim.

The existing world-500 milestone MP4 still matches its full-decode evidence:
2,178 decoded frames, 72.6 seconds, SHA256
`8ec9415a48d309b6d9e4a9ae23b05b21bd03d263e8e068e1ad351f75245ac989`.
Its scheduled Minecraft-only RTX 4050 capture metadata is preserved under
`recordings/phase9/youtube/fc9_stage25_terrain_00702.json`. No recording was
invented for this unrecorded routine restart, and no action sequence was
altered to create footage.

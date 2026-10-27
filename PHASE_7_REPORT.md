# FlyCraft — Phase 7 development report

Date: 2026-10-27 (Asia/Amman)

Project: `C:\Users\anass\Documents\FlyCraft`

## 1. Result and implemented features

The Phase 7 engineering capabilities are implemented and tested: high-level
goals, dependency-based subgoals, learned action selection, persistent memory,
multi-step policy updates, bounded recovery, performance-gated curriculum and
measurable evaluation. The preserved brain has 139,255 neurons. A real Fabric
navigation smoke test passed.

Demonstrated behavior has narrower limits. Final held-out wooden-pickaxe
success was **160/300 (53.33%) in simulation**, below the 70% criterion.
Multi-log collection was also inconsistent at 62%. Minecraft resource
collection and crafting have not been implemented or tested. Phase 7 does
not establish robust autonomous Minecraft intelligence.

Supported simulator objectives are `navigate_object`, `collect_nearby`,
`find_collect`, `collect_multiple`, `craft_simple` and `wooden_pickaxe`.
The live bridge accepts `navigate_object` only and rejects unsupported goals.

## 2. Inspection, baseline and files

Inspected the existing simulator, sensory/readout interfaces, Phase 5 policy,
reward/training pipeline, Minecraft client/server harness, checkpoints, tests,
evaluation tools and phase reports. Existing artifacts document the earlier
negative neural results and the subsequent stable visual-projection readout.
The historical Phase 6.5 live result was 4/9 trained versus 2/9 baseline.
Those historical experiments were reviewed, not all rerun.

Before modification, **23/23 tests passed in 4.738 seconds**. The graph was
then loaded and all six sensory windows recomputed twice with three workers:
139,255 neurons, 19,773,733 raw edges, 3,732,460 retained edges. All cached
features and repeated full activity states matched exactly. Validation took
5.389 seconds. Graph SHA-256 remained
`37054b0640ae353dcb7f68e8032da6ed2014e4698a24fd48ee95a58a9397c32d`.

| Added/modified files | Purpose |
|---|---|
| `autonomy/goal_manager.py`, `subgoal_planner.py` | Validated priorities/dependencies, observation completion, recipe planning |
| `autonomy/memory.py`, `features.py` | Bounded persistent experience and policy context |
| `autonomy/curriculum.py`, `recovery.py`, `metrics.py` | Performance gates, bounded recovery, rollout metrics |
| `autonomy/agent.py`, `world.py`, `bridge.py`, `__init__.py` | Learning/execution loop, World2D resource extension, live navigation |
| `learning/policy.py` | Compatible expanded readout, masks, entropy, atomic metadata checkpoints |
| `tools/train_phase7.py`, `evaluate_phase7.py` | Bounded training/resume and matched evaluations |
| `tools/validate_phase7_brain.py`, `check_phase7_tests.py` | Real-graph and regression evidence |
| `tools/summarize_phase7.py`, `analyze_phase7_live.py` | Aggregate and real-game log analysis |
| `tests/test_autonomy.py`, `test_autonomy_bridge.py`, `test_phase7_cli.py` | 22 added automated tests |
| `minecraft_bridge.py` | Optional autonomy mode and persistent log handle |
| `minecraft_mod/.../FlyCraftClient.java`, `FlyCraftMod.java`, `Phase7Harness.java` | Additive telemetry, stale/world guards, bounded smoke scene |
| `minecraft_mod/build.gradle` | Configurable build/runtime directories and test server address |
| `minecraft_mod/dist/flycraft-bridge-phase7-0.1.0.jar` | New built mod; previous jar preserved |
| `README.md`, `DEVELOPMENT_LOG.md`, `minecraft_mod/README.md`, `docs/phase7_design.md`, `docs/phase7_usage.md` | Documentation and commands |
| `checkpoints/phase7/`, `experiments/phase7/` | New checkpoints, raw attempts and measured results |

The existing directory has no Git repository. No Git repository was
initialized, no commit was created, and nothing was pushed.

## 3. Architecture decisions

Preserved the graph, neuron dynamics, input cohorts, visual-projection
population, 18-step observation protocol and Fabric TCP bridge. Phase 7
extends the existing linear policy readout to 63 features and 10 actions
(630 weights). Its original default 4x4 interface/checkpoints remain usable.
The new inputs combine the four connectome-derived features with explicit
goal, inventory and recent-experience context. No separate AI model was added.

The planner supplies recipe requirements and dependency structure. The
environment supplies interaction affordances. Every executable action,
including collection and crafting, is sampled by the learned policy. No
successful-sequence playback or automatic crafting is used. The simulator
does provide a selected-resource sensor and simplified mechanics; this is
substantial engineering assistance, retained in the frozen-policy controls.

Memory covers recent observations/actions, failures, inventory, obstacle
encounters, world-specific environmental facts, goal progress and attempt
statistics. Checkpoints also store RNG, curriculum, goal/recovery state,
trajectory and a pending action. Optional simulator snapshots support exact
mid-action restoration. The Python checkpoint does not save Minecraft worlds.

## 4. Learning algorithm and training metrics

Used the existing episodic REINFORCE update with discounted delayed returns,
moving scalar baseline, gradient clipping and entropy regularization. Final
configuration: learning rate 0.05, gamma 0.99, baseline retention 0.95,
gradient clip 5, entropy coefficient 0.02, 120-action episodes and at most
four recovery events.

Rewards measure same-visible-target geometric progress, required production,
root completion and action/failure costs. Surplus production no longer earns
progress reward. Successful and unsuccessful attempts both participate in
learning. Reuse occurs through learned weights and retained context.

Three final runs transferred their respective Phase 5/6.5 policies and
trained for 1,200 additional episodes each. All used a 180-second maximum
wall budget. They finished in approximately 42.72, 40.16 and 41.90 seconds.

| Training seed | Phase 7 episodes | Nonzero parameter updates | Weight-change norm from frozen transfer |
|---|---:|---:|---:|
| 11 | 1,200 | 1,200 | 2.51 |
| 29 | 1,200 | 1,199 | 2.53 |
| 47 | 1,200 | 1,200 | 2.65 |

All three advanced through levels 1–5 using separate 40-world evaluations
with a 70% success threshold. Seed 29 passed the pickaxe promotion criterion
on some curriculum evaluations, but its final unseen-seed success was 67%.
Final performance takes precedence over a favorable intermediate window.

Raw final runs: `experiments/phase7/curriculum_v3_seed{11,29,47}.jsonl` and
their `.summary.json` files. Earlier interrupted runs exposed an invalidated
inventory-root recovery bug. The completed `v2` experiments exposed surplus
crafting rewards and a subgoal-credit counting issue. All earlier logs and
checkpoints are retained; final claims use corrected `v3` results.

## 5. Automated and integration tests

**45/45 automated tests passed**, with zero failures, errors or skips. They
cover goal decomposition, dependency cycles/priorities/failure propagation,
consumed ingredients, missing resources, resource loss, bounded recovery,
memory/world isolation, performance-based curriculum, exact mid-action
checkpoint restoration, delayed failure learning, seeded reproduction,
unchanged evaluation weights and legacy/autonomous TCP compatibility.

An actual CLI test compares 20 uninterrupted episodes with 10 episodes plus
10 resumed episodes and obtains identical policy weights, baseline, RNG and
memory. Every simulator goal has a bounded end-to-end rollout test. The
recipe-mechanics fixture explicitly uses scripted actions as a mechanics
test; it is not counted as learned-behavior evidence.

The final suite also passed **after the project move**, in 14.222 seconds.
Evidence: `experiments/phase7/tests_after_move.{json,log}`. The Fabric build
passed offline before and after relocation; the final relocated build took
14 seconds. Earlier OneDrive build-lock failures are documented below.

## 6. Held-out evaluation and comparison with Phase 6.5

Each trained policy was evaluated on the same 100 unseen procedural world
seeds per goal: 300 policy/world rollouts per goal, representing 100 shared
world layouts and three training seeds. Training and promotion worlds were
separate from the final evaluation domain. Evaluation freezes all parameters.

The strongest learning comparison holds the new planner, masks, sensors and
recovery constant and changes only frozen transferred versus trained weights.
Uniform controls are deduplicated across repeated identical evaluations.

| Goal | Uniform + same planner | Frozen Phase 6.5 transfer + new actions | Phase 7 trained | Actions per trained success |
|---|---:|---:|---:|---:|
| Navigate object | 42.00% | 90.00% | 99.00% | 13.56 |
| Collect nearby log | 32.00% | 39.33% | 100.00% | 16.35 |
| Find and collect | 15.00% | 30.67% | 99.33% | 30.02 |
| Collect three logs | 1.00% | 2.00% | 62.00% | 29.83 |
| Craft planks | 14.00% | 33.67% | 99.00% | 28.27 |
| Obtain wooden pickaxe | 1.00% | 0.00% | 53.33% | 65.75 |

The original four-action policy scored 90% mean navigation success in the new
envelope and could not collect or craft. This action-set limitation is not
learning evidence; the frozen expanded-policy comparison above controls for it.
The historical live Phase 6.5 44.44% result uses different tasks and decision
limits and cannot be compared numerically with these simulation percentages.

Trained failed goals numbered 3, 0, 2, 114, 3 and 140 respectively. Local
progress following recovery occurred on 8/8, 12/12, 15/15, 227/335, 6/6 and
80/128 recovery events. These are operational recovery metrics, not proof
that recovery caused those successes. Seed 29's no-recovery ablation scored
69% versus 68% on three-log collection and 64% versus 67% on pickaxes; benefits
are mixed and small in this sample.

Seed 29's shuffled-neural control retained 98–100% on the easier tasks and
50% pickaxe success versus 67% with aligned features. Goal context and action
priors therefore account for considerable performance. The pickaxe difference
suggests a contribution from aligned neural features in that run; it does not
show that the connectome learned or establish a general biological advantage.

Obstacle stress success was 94%, 84% and 94% for the three policies. Full
metrics include time-to-success, failed actions, subgoal completion and
recovery histories. Simulator times are CPU rollout durations, not Minecraft
game time. See `experiments/phase7/aggregate_v3.json` and
`evaluation_v3_seed{11,29,47}.{json,jsonl}`.

## 7. Real Minecraft demonstration

Ran Minecraft 26.2 / Fabric Loader 0.19.5 in fresh project-local flat worlds,
with a real client, server and the full sparse neural process. The harness
placed a gold marker and independently measured distance. It supplied no
movement actions.

The initial attempt stopped too early because the ray-hit distance criterion
was looser than the server's center-distance criterion. It failed server
evaluation at 1.848 blocks. OneDrive also briefly blocked reopening the log.
Fixed completion geometry, kept the log handle open, added a regression test,
and stopped client requests at terminal goal status. The original logs remain.

The corrected fresh-world attempt passed: the server measured **1.437 blocks
after 100 ticks**. The controller completed after **8 sampled actions** and
4.169 seconds from its first decision. Nine responses include eight full
neural windows and the terminal idle response. There were zero bridge errors,
client request failures or stale actions in this attempt. The trained readout
was frozen; this demonstrates execution, not live learning.

Evidence: `experiments/phase7/live_metrics.json` and
`live_attempt2_{server.log,client.log,bridge.jsonl}`. Only one corrected live
navigation scene was tested. Resource collection, crafting and unseen-seed
Minecraft generalization are untested. Test client, server and service were
stopped; no training job was left running.

## 8. Resources and project relocation

Used cached exact neural responses for training and three shared-memory
workers for the full-network validation. Short independent training/evaluation
runs used CPU; a GPU training stack was unnecessary. Sampled GPU temperatures
were 48–50°C. A CPU temperature reading was unavailable, so no CPU temperature
measurement or continuous thermal guarantee is claimed.

Reported Codex weekly usage was 2% initially, 3%, 4%, then 5%, below the
user's 55% development-stop and 60% maximum thresholds. No usage reset was used.

At the user's request, moved the entire project from OneDrive Desktop to
`C:\Users\anass\Documents\FlyCraft`. Verified all **231 data/checkpoint files,
348,041,570 bytes**, against SHA-256 hashes taken before the move: every hash
matched. The old workspace junction now points to Documents; its previous
link was retained as `FlyCraftProject.previous-location`. Updated environment
activation paths and regenerated nine existing console launchers without
changing package versions; old launchers were backed up in the chat's work
folder. Python, pip, all tests and the offline Fabric build work after moving.

## 9. Known limitations

- Pickaxe and multi-log goals remain below the final reliability threshold;
  earlier curriculum success is not sufficient evidence of retained mastery.
- Learning is confined to a small interface/readout. The sparse connectome
  remains fixed, and meaningful descending-neuron control is still absent.
- Simulated collection is an instant explicit interaction; Minecraft mining,
  inventory screens, recipe transactions and station placement are not bridged.
- Recovery can choose an unhelpful alternative or fail after bounded retries.
  Remembered obstacles summarize encounters rather than construct a route map.
- The simulator's selected target and legal-action masks simplify perception
  and exploration. Easy-task neural shuffling results reveal action-prior and
  goal-context confounds.
- Delayed rewards use whole-episode returns without a learned value function;
  long sequences remain high-variance. Surplus reward farming was corrected,
  but reward specification still needs adversarial testing.
- Live evidence is one corrected, simple creative-world navigation scene.
  There is no demonstrated autonomous survival or reliable Minecraft pickaxe.

## 10. Recommendations for Phase 8

1. Add observed Minecraft mining/inventory/crafting transactions with action
   acknowledgments and interrupted-action tests, starting with one log.
2. Require repeated held-out mastery and retention checks across earlier
   curriculum levels; introduce bounded mixed-level rehearsal to reduce forgetting.
3. Study return variance and a transparent value baseline or temporally
   extended learned skills within the existing readout architecture.
4. Test target-absent, depleted, occluded, multi-object and misleading-affordance
   worlds. Expand neural, memory and recovery ablations over all training seeds.
5. Run matched live baselines on multiple disposable world seeds before any
   claim of robust autonomous Minecraft behavior.

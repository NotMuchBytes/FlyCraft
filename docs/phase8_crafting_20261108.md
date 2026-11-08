# Phase 8 headless crafting and multi-log trials

The headless Minecraft adapter now fills the vanilla inventory and workbench
menus for planks, sticks, crafting tables, and wooden pickaxes. It verifies the
recipe result before moving it and checks the resulting inventory count.
The place action uses the actual crosshair and the vanilla block placement
interaction, and checks both the placed block and the consumed item.
Workbenches are observed through the existing bounded sight rays. A pickaxe
craft opens the workbench under the crosshair. The action uses no automatic
aim.

For the stick, table and pickaxe objectives, the controller masks recipes
outside the active planner subgoal. Navigation remains available and the
same mask applies to all comparison policies. The policy still chooses
each action. This is engineered recipe assistance, and the existing
139,255-neuron graph and checkpoint were used without training updates.

## First live transactions

In Minecraft 26.2 the prepared workbench trial consumed three planks and two
sticks and confirmed one wooden pickaxe in one policy action and nine game
ticks. The workbench was at eye height for this yaw-only actor. This trial
exercises the workbench recipe with prepared ingredients.

The empty-inventory crafting-table trial confirmed one table in 11 actions and
174 ticks. The empty-inventory sticks trial broke one log but failed to pick
it up within 500 ticks. It attempted no stick recipe. These three development
episodes used the same controlled layout and kept structured logs.
[Run manifest](../experiments/phase9/p8_craft_transactions_20261108_a/run.json)

## Placement and the full chain

The first prepared placement recording stopped at the RAM guard before
gameplay. The original 3.3-second startup MP4 is preserved. A server-only
diagnostic then showed two rejected placement attempts. At both attempts,
the proposed table block overlapped the actor's body. The adapter now
checks that collision before offering the action. The prepared retry has
a stone support face one block farther away.
[Startup recording metadata](../recordings/phase9/youtube/p8_place_pickaxe_recorded_20261108_a.json)
[Placement failure trace manifest](../experiments/phase9/p8_place_pickaxe_probe_20261108_a/run.json)

The prepared retry placed the owned table and crafted one wooden pickaxe in
four actions and 31 game ticks. Minecraft acknowledged the changed block and
consumed table item. The workbench then consumed three planks and two sticks.
The server and controller independently confirmed the pickaxe in inventory.
The 16.1-second Minecraft-only MP4 passed full decoding.
[Verified placement and pickaxe recording](../recordings/phase9/youtube/p8_place_pickaxe_recorded_20261108_b.json)

The first full pickaxe trial began with empty inventory. It confirmed three
block breaks, then consumed three collected logs to make planks, sticks and
a crafting table. The trial ended at 1,500 ticks with six planks, four sticks,
one table and zero pickaxes after 110 actions. This flat layout offered few
reachable placement faces at the actor's eye height after mining. The revised
three-tree pickaxe fixture supplies a visible stone face and still begins with
empty inventory. The bridge can report a visible placement surface through
the current-pitch sight rays when the actor owns a table. Placement still
requires the actor to put the actual crosshair on a valid face.
[First full-chain run](../experiments/phase9/p8_pickaxe_from_empty_20261108_a/run.json)

The recorded full-chain retry succeeded from empty inventory in **103 actions
and 1,396 game ticks**. The server confirmed three log breaks, and the policy
collected the logs, chose the plank, stick and table recipes, placed the table
against the fixture's stone support, and selected the pickaxe recipe. Final
inventory contained one wooden pickaxe, three planks and two sticks. The
controller agreed with the independent server score and the terminal
exchange was acknowledged. This verifies the full chain on one controlled
layout. The 86.833-second original OBS MP4 passed full decoding and
Minecraft-window verification on the RTX 4050.
[Full-chain recording metadata](../recordings/phase9/youtube/p8_pickaxe_from_empty_recorded_20261108_a.json)

## Memory probe

The optional `--remember-mined-columns` flag remembers columns of confirmed
log breaks for the current episode. It excludes only off-pitch standing log
hits in those columns. Current-pitch log hits and visible drops still enter
the normal selection. No new world data enter the sensor. Three development
repeats at 700 ticks collected two logs each, matching the prior ranking
variant's terminal inventories. In the first trial the actor found the third
trunk again but only reached 4.15 blocks by its last sighting. The flag stays
opt-in pending evidence of an improvement.
[Memory trials](../experiments/phase9/p8_three_tree_memory_20261108_a/run.json)

With the same memory flag and a 1,500-tick limit, the policy collected
three logs on two of the same three development layouts. The successful
episodes ended at 646 and 1,212 ticks. The other ended at 1,500 ticks with
two logs. Changes in episode length and game RNG prevent attributing the
result to the memory flag alone.
[Extended trials](../experiments/phase9/p8_three_tree_extended_20261108_a/run.json)

The fixed held-out plan pairs the two long goals on 30 layout seeds
across six Minecraft worlds. It freezes the policy, uses a 1,500-tick
limit and scores actual server inventory. The pickaxe layout includes
the stone support and both goals begin with empty inventory. Results
from development retries remain separate.
[Held-out plan](../experiments/phase9/phase8_completion_bench_20261108/plan.json)

The first completed world block scored **4/5 three-log** and **0/5
wooden-pickaxe**. Every outcome had acknowledged terminal inventory
delivery. Three pickaxe episodes ended holding a table. One never
observed a support face after crafting the table. One requested a
placement and Minecraft reported no confirmed block change. The other
observed a valid placement affordance without selecting it. Two further
pickaxe episodes ran out of time before crafting a table.
[First held-out block](../experiments/phase9/p8_completion_bench_20261108_1/run.json)

The preselected three-log recording repeated the first held-out layout in
a fresh execution. It collected three logs in 57 actions and 887 game ticks.
The original 60.567-second Minecraft-window MP4 passed full decoding and
capture verification. This recording is separate from the scored trials.
[Verified three-log recording](../recordings/phase9/youtube/p8_three_tree_completion_recorded_20261108_a.json)

## Held-out results through two worlds

| Goal | Confirmed successes | Descriptive 95% Wilson interval | Median actions |
| --- | ---: | ---: | ---: |
| Three logs | 7/10 | 39.7%–89.2% | 69 |
| Wooden pickaxe | 0/10 | 0%–27.8% | 107.5 |

All 20 episodes had acknowledged terminal delivery. The three collection
failures ended with two logs. Six pickaxe failures stopped after crafting
a table, three after crafting sticks, and one after crafting planks. These
are grouped by the last confirmed crafting stage. The layouts share two
worlds, so the intervals describe this sample and do not account for
world clustering. The recorded from-empty success is a development
trial and is outside the held-out count.

The second world finished at the 55% weekly Codex stop point for starting
new development. Both gameplay milestones have verified development MP4s.
[Second held-out block](../experiments/phase9/p8_completion_bench_20261108_2/run.json)

## Partial third world

The existing frozen evaluation resumed at the user's request. The RAM
guard stopped world block 3 after five scored episodes. Its lowest sample
was about 418 MiB. A fresh run completed the interrupted third-layout
pickaxe trial with the same world and layout seeds, checkpoint, policy
seed and deadline. It finished with a crafting table, six planks and
four sticks. The retry generated a new world instance, so absolute spawn
and game RNG could differ. It scored the missing layout once.

The cumulative held-out result is **8/13 for three logs** and **0/13 for
wooden pickaxes**. In the first two worlds, six pickaxe failures crafted
a table. Two saw a valid placement affordance and one selected it.
The third world's fourth and fifth layout pairs and blocks 4–6 remain
unstarted, leaving 17 trials per goal. The preselected held-out pickaxe
recording is pending. These resumed scored trials used structured logs.
[Interrupted block](../experiments/phase9/p8_completion_bench_20261108_3/run.json)
[Same-layout retry](../experiments/phase9/p8_completion_bench_20261108_3_pair3_retry/run.json)
[Per-episode held-out results](../experiments/phase9/phase8_completion_bench_20261108/results.json)

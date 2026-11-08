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

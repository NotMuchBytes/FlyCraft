package org.flycraft.bridge;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Blocks;

/** Deterministic Minecraft task definitions and outcome-only evaluation. */
public final class Phase6Harness {
	private static final int DECISION_TICKS = 10;
	private static final Scenario[] SCENARIOS = {
		new Scenario("T1_ORIENT", 6101, -40.0, 7.0, 8, true),
		new Scenario("T1_ORIENT", 6102, 40.0, 7.0, 8, true),
		new Scenario("T1_ORIENT", 6103, -20.0, 7.0, 8, true),
		new Scenario("T2_APPROACH", 6201, 0.0, 4.5, 18, false),
		new Scenario("T2_APPROACH", 6202, -20.0, 5.0, 18, false),
		new Scenario("T2_APPROACH", 6203, 20.0, 5.5, 18, false),
		new Scenario("T3_GENERALIZE", 6301, -40.0, 6.0, 20, false),
		new Scenario("T3_GENERALIZE", 6302, 40.0, 7.0, 20, false),
		new Scenario("T3_GENERALIZE", 6303, 0.0, 8.0, 20, false)
	};
	private static final Map<UUID, RunState> STATES = new HashMap<>();

	private Phase6Harness() {
	}

	public static void tick(MinecraftServer server) {
		long now = server.getTickCount();
		for (ServerPlayer player : server.getPlayerList().getPlayers()) {
			RunState state = STATES.computeIfAbsent(player.getUUID(), ignored -> new RunState(player));
			if (state.complete || now < state.nextStartTick) {
				continue;
			}
			if (!state.active) {
				state.scenarioIndex++;
				if (state.scenarioIndex >= SCENARIOS.length) {
					state.complete = true;
					FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE6 suite_complete episodes={}", SCENARIOS.length);
					continue;
				}
				start(player, state, SCENARIOS[state.scenarioIndex], now);
				continue;
			}
			evaluate(player, state, SCENARIOS[state.scenarioIndex], now);
		}
	}

	private static void start(ServerPlayer player, RunState state, Scenario scenario, long now) {
		ServerLevel level = player.level();
		clearTarget(level, state);
		player.teleportTo(level, state.originX, state.originY, state.originZ, Set.of(), 0.0F, 0.0F, true);
		double radians = Math.toRadians(scenario.bearingDegrees);
		double x = state.originX - Math.sin(radians) * scenario.distance;
		double z = state.originZ + Math.cos(radians) * scenario.distance;
		state.target = BlockPos.containing(x, player.getEyeY(), z);
		level.setBlockAndUpdate(state.target, Blocks.GOLD_BLOCK.defaultBlockState());
		state.targetX = state.target.getX() + 0.5;
		state.targetZ = state.target.getZ() + 0.5;
		state.startedAt = now;
		state.active = true;
		state.initialDistance = distance(player, state);
		state.initialAngleError = Math.abs(angleError(player, state));
		FlyCraftMod.LOGGER.info(
				"FLYCRAFT_PHASE6 episode_start episode={} task={} seed={} max_steps={} target={} initial_distance={} initial_angle_error={}",
				state.scenarioIndex + 1, scenario.taskId, scenario.seed, scenario.maxDecisions, state.target,
				state.initialDistance, state.initialAngleError);
	}

	private static void evaluate(ServerPlayer player, RunState state, Scenario scenario, long now) {
		long elapsedTicks = now - state.startedAt;
		double finalDistance = distance(player, state);
		double finalAngleError = Math.abs(angleError(player, state));
		boolean success = scenario.orientationOnly ? finalAngleError <= 10.0 && elapsedTicks >= DECISION_TICKS : finalDistance <= 1.6;
		boolean timeout = elapsedTicks >= (long) scenario.maxDecisions * DECISION_TICKS;
		if (!success && !timeout) {
			return;
		}
		double reward = (state.initialDistance - finalDistance)
				+ 0.20 * Math.toRadians(state.initialAngleError - finalAngleError)
				+ (success ? 3.0 : 0.0);
		int decisions = (int) Math.ceil(elapsedTicks / (double) DECISION_TICKS);
		FlyCraftMod.LOGGER.info(
				"FLYCRAFT_PHASE6 episode_end episode={} task={} seed={} success={} termination={} steps={} reward={} initial_distance={} final_distance={} initial_angle_error={} final_angle_error={}",
				state.scenarioIndex + 1, scenario.taskId, scenario.seed, success, success ? "success" : "timeout", decisions,
				reward, state.initialDistance, finalDistance, state.initialAngleError, finalAngleError);
		clearTarget(player.level(), state);
		state.active = false;
		state.nextStartTick = now + 20;
	}

	private static double distance(ServerPlayer player, RunState state) {
		return Math.hypot(state.targetX - player.getX(), state.targetZ - player.getZ());
	}

	private static double angleError(ServerPlayer player, RunState state) {
		double dx = state.targetX - player.getX();
		double dz = state.targetZ - player.getZ();
		double targetYaw = Math.toDegrees(Math.atan2(-dx, dz));
		double difference = targetYaw - player.getYRot();
		return (difference + 180.0) % 360.0 - 180.0;
	}

	private static void clearTarget(ServerLevel level, RunState state) {
		if (state.target != null && level.getBlockState(state.target).is(Blocks.GOLD_BLOCK)) {
			level.setBlockAndUpdate(state.target, Blocks.AIR.defaultBlockState());
		}
		state.target = null;
	}

	private record Scenario(String taskId, int seed, double bearingDegrees, double distance, int maxDecisions, boolean orientationOnly) {
	}

	private static final class RunState {
		private int scenarioIndex = -1;
		private long startedAt;
		private long nextStartTick;
		private boolean active;
		private boolean complete;
		private BlockPos target;
		private double targetX;
		private double targetZ;
		private double initialDistance;
		private double initialAngleError;
		private final double originX;
		private final double originY;
		private final double originZ;

		private RunState(ServerPlayer player) {
			this.originX = player.getX();
			this.originY = player.getY();
			this.originZ = player.getZ();
		}
	}
}

package org.flycraft.bridge;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.nio.file.Files;
import java.nio.file.Path;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;

import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Blocks;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class FlyCraftMod implements ModInitializer {
	public static final String MOD_ID = "flycraft_bridge";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);
	private static final String[] TEST_PHASES = {"left", "center", "right", "not_visible"};
	private static final Map<UUID, TestState> TEST_STATES = new HashMap<>();

	@Override
	public void onInitialize() {
		LOGGER.info("FlyCraft bridge initialized");
		if (Files.exists(Path.of("flycraft-phase7.enabled"))) {
			LOGGER.info("FLYCRAFT_PHASE7 enabled");
			ServerTickEvents.END_SERVER_TICK.register(Phase7Harness::tick);
		} else if (Files.exists(Path.of("flycraft-phase6.enabled"))) {
			LOGGER.info("FLYCRAFT_PHASE6 enabled");
			ServerTickEvents.END_SERVER_TICK.register(Phase6Harness::tick);
		} else if (Boolean.getBoolean("flycraft.autotest") || Files.exists(Path.of("flycraft-autotest.enabled"))) {
			LOGGER.info("FLYCRAFT_AUTOTEST enabled");
			ServerTickEvents.END_SERVER_TICK.register(FlyCraftMod::runAutotest);
		}
	}

	private static void runAutotest(MinecraftServer server) {
		long now = server.getTickCount();
		for (ServerPlayer player : server.getPlayerList().getPlayers()) {
			TestState state = TEST_STATES.computeIfAbsent(player.getUUID(), ignored -> new TestState(now, player));
			if (!state.configured || now - state.phaseStartedAt >= 140) {
				if (state.configured) {
					state.phase = (state.phase + 1) % TEST_PHASES.length;
				}
				state.phaseStartedAt = now;
				state.configured = true;
				configurePhase(player, state, TEST_PHASES[state.phase]);
			}
		}
	}

	private static void configurePhase(ServerPlayer player, TestState state, String phase) {
		ServerLevel level = player.level();
		if (state.target != null && level.getBlockState(state.target).is(Blocks.GOLD_BLOCK)) {
			level.setBlockAndUpdate(state.target, Blocks.AIR.defaultBlockState());
		}
		state.target = null;
		player.teleportTo(level, state.originX, state.originY, state.originZ, Set.of(), 0.0F, 0.0F, true);
		if (!phase.equals("not_visible")) {
			double offset = switch (phase) {
				case "left" -> -20.0;
				case "right" -> 20.0;
				default -> 0.0;
			};
			double radians = Math.toRadians(offset);
			double targetX = state.originX - Math.sin(radians) * 7.0;
			double targetZ = state.originZ + Math.cos(radians) * 7.0;
			state.target = BlockPos.containing(targetX, player.getEyeY(), targetZ);
			level.setBlockAndUpdate(state.target, Blocks.GOLD_BLOCK.defaultBlockState());
		}
		LOGGER.info("FLYCRAFT_AUTOTEST phase={} server_tick={} target={}", phase, state.phaseStartedAt, state.target);
	}

	private static final class TestState {
		private int phase;
		private long phaseStartedAt;
		private boolean configured;
		private BlockPos target;
		private final double originX;
		private final double originY;
		private final double originZ;

		private TestState(long phaseStartedAt, ServerPlayer player) {
			this.phaseStartedAt = phaseStartedAt;
			this.originX = player.getX();
			this.originY = player.getY();
			this.originZ = player.getZ();
		}
	}
}

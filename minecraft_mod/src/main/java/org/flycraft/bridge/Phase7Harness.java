package org.flycraft.bridge;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Blocks;

/** Single navigation smoke scene. Supplies no actions to the neural controller. */
public final class Phase7Harness {
	private static final Map<UUID, Scene> SCENES = new HashMap<>();
	private Phase7Harness() { }

	public static void tick(MinecraftServer server) {
		for (ServerPlayer player : server.getPlayerList().getPlayers()) {
			Scene scene = SCENES.get(player.getUUID());
			if (scene == null) {
				player.setYRot(0.0F);
				player.setXRot(0.0F);
				BlockPos target = BlockPos.containing(player.getX(), player.getEyeY(), player.getZ() + 4.0);
				player.level().setBlockAndUpdate(target, Blocks.GOLD_BLOCK.defaultBlockState());
				scene = new Scene(target, server.getTickCount());
				SCENES.put(player.getUUID(), scene);
				FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE7 scene_start target={}", target);
			}
			if (scene.complete) continue;
			double distance = Math.hypot(scene.target.getX() + 0.5 - player.getX(), scene.target.getZ() + 0.5 - player.getZ());
			long elapsed = server.getTickCount() - scene.started;
			if (distance <= 1.6 || elapsed >= 1400) {
				scene.complete = true;
				FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE7 scene_end success={} distance={} ticks={}", distance <= 1.6, distance, elapsed);
			}
		}
	}

	private static final class Scene {
		final BlockPos target;
		final long started;
		boolean complete;
		Scene(BlockPos target, long started) { this.target = target; this.started = started; }
	}
}

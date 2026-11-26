package org.flycraft.bridge;

import java.util.*;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ClientboundBlockUpdatePacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.ItemStack;

/** Echo only the player's own inventory and directly interacted blocks. Never selects actions. */
public final class Phase8ServerObservations {
    private static final Map<UUID, List<ItemStack>> inventories = new HashMap<>();
    private static final Map<ServerPlayer, BlockPos> placements = new HashMap<>();
    public static void initialize() {
        PlayerBlockBreakEvents.AFTER.register((world, player, pos, old, entity) -> {
            if (player instanceof ServerPlayer serverPlayer)
                serverPlayer.connection.send(new ClientboundBlockUpdatePacket(pos, world.getBlockState(pos)));
        });
        UseBlockCallback.EVENT.register((player, world, hand, hit) -> {
            if (player instanceof ServerPlayer serverPlayer) placements.put(serverPlayer, hit.getBlockPos().relative(hit.getDirection()));
            return InteractionResult.PASS;
        });
        ServerTickEvents.END_SERVER_TICK.register(Phase8ServerObservations::tick);
    }
    private static void tick(MinecraftServer server) {
        for (var entry : placements.entrySet())
            entry.getKey().connection.send(new ClientboundBlockUpdatePacket(entry.getValue(), entry.getKey().level().getBlockState(entry.getValue())));
        placements.clear();
        Set<UUID> connected = new HashSet<>();
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            connected.add(player.getUUID());
            List<ItemStack> previous = inventories.get(player.getUUID());
            List<ItemStack> current = new ArrayList<>();
            for (int i = 0; i < player.getInventory().getContainerSize(); i++) current.add(player.getInventory().getItem(i).copy());
            boolean changed = previous == null || previous.size() != current.size();
            if (!changed) for (int i = 0; i < current.size(); i++)
                if (!ItemStack.matches(previous.get(i), current.get(i))) { changed = true; break; }
            if (changed) {
                inventories.put(player.getUUID(), current);
                // Vanilla may suppress updates matching client prediction. Explicitly echo actual own-inventory state.
                player.inventoryMenu.sendAllDataToRemote();
            }
        }
        inventories.keySet().retainAll(connected);
    }
}

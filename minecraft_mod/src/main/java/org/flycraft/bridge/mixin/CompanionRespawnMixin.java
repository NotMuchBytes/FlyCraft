package org.flycraft.bridge.mixin;

import com.mojang.authlib.GameProfile;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ClientInformation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import org.flycraft.bridge.HeadlessAgent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Preserve the embedded actor subtype only during its explicitly owned respawn. */
@Mixin(PlayerList.class)
public abstract class CompanionRespawnMixin {
    @Redirect(method="respawn",at=@At(value="NEW",target="net/minecraft/server/level/ServerPlayer"))
    private ServerPlayer flycraftRespawn(MinecraftServer server,ServerLevel level,GameProfile profile,ClientInformation information) {
        return HeadlessAgent.createRespawnPlayer(server,level,profile,information);
    }
}

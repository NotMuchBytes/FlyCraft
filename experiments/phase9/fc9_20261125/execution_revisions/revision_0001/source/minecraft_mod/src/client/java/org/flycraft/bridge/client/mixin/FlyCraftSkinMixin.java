package org.flycraft.bridge.client.mixin;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.core.ClientAsset;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.player.PlayerModelType;
import net.minecraft.world.entity.player.PlayerSkin;
import org.flycraft.bridge.client.FlyCraftClient;
import org.flycraft.bridge.client.Phase8Client;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** User-supplied appearance only; no change to the agent or its observations. */
@Mixin(AbstractClientPlayer.class)
public abstract class FlyCraftSkinMixin {
    private static final java.util.Set<java.util.UUID> FLYCRAFT_SKIN_LOGGED=new java.util.HashSet<>();
    private static final PlayerSkin FLYCRAFT_SKIN=new PlayerSkin(
        new ClientAsset.ResourceTexture(Identifier.fromNamespaceAndPath("flycraft_bridge","flycraft_skin"),
            Identifier.fromNamespaceAndPath("flycraft_bridge","textures/entity/flycraft.png")),
        null,null,PlayerModelType.WIDE,false);
    @Inject(method="getSkin",at=@At("RETURN"),cancellable=true)
    private void flycraftSkin(CallbackInfoReturnable<PlayerSkin> callback) {
        var self=(AbstractClientPlayer)(Object)this;
        boolean agent=self.getGameProfile().name().equals("FlyCraftAgent")
            || self==Minecraft.getInstance().player && (Phase8Client.INSTANCE!=null || FlyCraftClient.INSTANCE!=null);
        if(agent) {
            callback.setReturnValue(FLYCRAFT_SKIN);
            if(FLYCRAFT_SKIN_LOGGED.add(self.getUUID())) org.flycraft.bridge.FlyCraftMod.LOGGER.info(
                "FLYCRAFT_SKIN selected actor={} texture={}",self.getUUID(),FLYCRAFT_SKIN.body().texturePath());
        }
    }
}

package org.flycraft.bridge.client.mixin;

import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.*;
import org.flycraft.bridge.client.Phase8Client;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientPacketListener.class)
public class Phase8PacketMixin {
    @Inject(method = "handleBlockUpdate", at = @At("TAIL"))
    private void flycraftBlock(ClientboundBlockUpdatePacket packet, CallbackInfo ci) {
        if (Phase8Client.INSTANCE != null) Phase8Client.INSTANCE.blockPacket(packet.getPos(), packet.getBlockState());
    }
    @Inject(method = "handleContainerContent", at = @At("TAIL"))
    private void flycraftContents(ClientboundContainerSetContentPacket packet, CallbackInfo ci) {
        if (Phase8Client.INSTANCE != null) Phase8Client.INSTANCE.contentsPacket(packet.containerId(), packet.items());
    }
    @Inject(method = "handleContainerSetSlot", at = @At("TAIL"))
    private void flycraftSlot(ClientboundContainerSetSlotPacket packet, CallbackInfo ci) {
        if (Phase8Client.INSTANCE != null) Phase8Client.INSTANCE.slotPacket(packet.getContainerId(), packet.getSlot(), packet.getItem());
    }
    @Inject(method = "handleSetPlayerInventory", at = @At("TAIL"))
    private void flycraftInventory(ClientboundSetPlayerInventoryPacket packet, CallbackInfo ci) {
        if (Phase8Client.INSTANCE != null) Phase8Client.INSTANCE.inventoryPacket(packet.slot(), packet.contents());
    }
}

package org.flycraft.bridge.mixin;

import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import org.flycraft.bridge.CompanionSession;
import org.flycraft.bridge.HeadlessAgent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Observe vanilla pickup only; never changes item or player behavior. */
@Mixin(ItemEntity.class)
public abstract class CompanionPickupMixin {
    @Unique private int flycraftCount,flycraftInventory;
    @Unique private String flycraftItem;
    @Inject(method="playerTouch",at=@At("HEAD"))
    private void beforePickup(Player recipient,CallbackInfo ci) {
        ItemEntity entity=(ItemEntity)(Object)this;flycraftCount=0;
        if(!CompanionSession.tracksDelivery(entity.getUUID(),recipient.getUUID())) return;
        flycraftItem=HeadlessAgent.itemKind(entity.getItem());flycraftCount=entity.getItem().getCount();
        flycraftInventory=HeadlessAgent.itemCount(recipient,flycraftItem);
    }
    @Inject(method="playerTouch",at=@At("RETURN"))
    private void afterPickup(Player recipient,CallbackInfo ci) {
        if(flycraftCount==0) return;
        ItemEntity entity=(ItemEntity)(Object)this;
        // Vanilla discards a fully picked-up entity, then restores its stack
        // count for pickup feedback. A count-only comparison misses that case.
        // The order ledger also requires the recipient's inventory increase.
        int units=entity.isRemoved() ? flycraftCount : flycraftCount-entity.getItem().getCount();
        CompanionSession.pickupObserved(entity.getUUID(),recipient,units,flycraftInventory,HeadlessAgent.itemCount(recipient,flycraftItem));
        flycraftCount=0;
    }
}

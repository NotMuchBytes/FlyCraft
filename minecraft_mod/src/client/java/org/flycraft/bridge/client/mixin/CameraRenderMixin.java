package org.flycraft.bridge.client.mixin;

import net.minecraft.client.DeltaTracker;
import net.minecraft.client.renderer.GameRenderer;
import org.flycraft.bridge.client.Phase8Client;
import org.flycraft.bridge.client.FlyCraftClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Read-only rendered-view instrumentation. Does not steer the camera. */
@Mixin(GameRenderer.class)
public abstract class CameraRenderMixin {
    @Inject(method="render",at=@At("TAIL"))
    private void flycraftCameraRendered(DeltaTracker tracker,boolean renderWorld,CallbackInfo callback) {
        var camera=((GameRenderer)(Object)this).mainCamera();
        if(Phase8Client.INSTANCE!=null) Phase8Client.INSTANCE.renderedCamera(camera.yRot(),camera.xRot());
        else if(FlyCraftClient.INSTANCE!=null) FlyCraftClient.INSTANCE.renderedCamera(camera.yRot(),camera.xRot());
    }
}

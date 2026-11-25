package org.flycraft.bridge.client.mixin;

import com.mojang.blaze3d.platform.Window;
import java.nio.file.Files;
import java.nio.file.Path;
import org.lwjgl.glfw.GLFW;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Test windows remain visible to OBS without requesting keyboard focus. */
@Mixin(Window.class)
public abstract class Phase8WindowMixin {
    @Redirect(method = "createGlfwWindow", at = @At(value = "INVOKE", target = "Lorg/lwjgl/glfw/GLFW;glfwCreateWindow(IILjava/lang/CharSequence;JJ)J"))
    private static long flycraftBackgroundWindow(int width, int height, CharSequence title, long monitor, long share) {
        if (Files.exists(Path.of("flycraft-phase8-client.properties"))) {
            GLFW.glfwWindowHint(GLFW.GLFW_FOCUSED, GLFW.GLFW_FALSE);
            GLFW.glfwWindowHint(GLFW.GLFW_FOCUS_ON_SHOW, GLFW.GLFW_FALSE);
        }
        return GLFW.glfwCreateWindow(width, height, title, monitor, share);
    }
}

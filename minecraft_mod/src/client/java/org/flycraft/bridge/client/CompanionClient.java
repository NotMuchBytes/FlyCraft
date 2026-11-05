package org.flycraft.bridge.client;

import java.io.*;
import java.nio.file.*;
import java.util.Properties;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import org.flycraft.bridge.FlyCraftMod;

/** Read-only recording support. Never changes human input, menus or settings. */
public final class CompanionClient {
    public static CompanionClient INSTANCE;
    private final Properties config=new Properties();
    private boolean capturing;
    private long frames,lastCapture;
    public void initialize() {
        INSTANCE=this;
        try(var reader=Files.newBufferedReader(Path.of("flycraft-companion.properties"))) { config.load(reader); }
        catch(IOException error) { throw new IllegalStateException(error); }
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            String title=config.getProperty("recording.windowTitle","");
            if(!title.isEmpty()) client.getWindow().setTitle(title);
        });
        FlyCraftMod.LOGGER.info("FlyCraft companion mode: human input remains under player control");
    }
    public void rendered() {
        var client=Minecraft.getInstance(); frames++;
        String framePath=config.getProperty("recording.frameFile","");
        String gatePath=config.getProperty("recording.captureGate","");
        if(framePath.isEmpty() || client.level==null || capturing || frames-lastCapture<40
            || !gatePath.isEmpty() && Files.exists(Path.of(gatePath))) return;
        capturing=true; lastCapture=frames;
        Screenshot.takeScreenshot(client.gameRenderer.mainRenderTarget(),image -> {
            try(image) {
                Path file=Path.of(framePath); Path temporary=file.resolveSibling(file.getFileName()+".tmp");
                image.writeToFile(temporary);
                Files.move(temporary,file,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
            } catch(IOException error) { FlyCraftMod.LOGGER.warn("Companion recording frame will retry",error); }
            finally { capturing=false; }
        });
    }
}

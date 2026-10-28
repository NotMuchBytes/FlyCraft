package org.flycraft.bridge.client;

import com.google.gson.*;
import java.io.*;
import java.nio.file.*;
import java.util.Properties;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.*;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import org.flycraft.bridge.FlyCraftMod;
import org.flycraft.bridge.control.CameraMotion;

/** Recording-only camera. Never sends observations or actions to the policy. */
public final class SpectatorClient {
    public static SpectatorClient INSTANCE;
    private Path controlFile,readyFile;
    private Path frameFile;
    private String windowTitle;
    private boolean frameRequested;
    private double distance,height,side;
    private boolean firstPerson,initialized;
    private long tick;
    public void initialize() {
        INSTANCE=this;
        var properties=new Properties();
        try(var reader=Files.newBufferedReader(Path.of("flycraft-spectator.properties"))) { properties.load(reader); }
        catch(IOException error) { throw new IllegalStateException(error); }
        controlFile=Path.of(properties.getProperty("controlFile")); readyFile=Path.of(properties.getProperty("readyFile"));
        frameFile=Path.of(properties.getProperty("frameFile")); windowTitle=properties.getProperty("windowTitle");
        distance=Double.parseDouble(properties.getProperty("distance","6"));
        height=Double.parseDouble(properties.getProperty("height","3"));
        side=Double.parseDouble(properties.getProperty("side","2"));
        firstPerson=properties.getProperty("view","third_person").equals("first_person");
        if(!Double.isFinite(distance+height+side) || distance<2 || distance>12 || height<1 || height>8 || Math.abs(side)>8)
            throw new IllegalArgumentException("Invalid recording-camera geometry");
        ClientTickEvents.END_CLIENT_TICK.register(this::tick);
        FlyCraftMod.LOGGER.info("FLYCRAFT_SPECTATOR enabled; recording camera has no policy connection");
    }
    private void tick(Minecraft client) {
        tick++;
        client.getWindow().setTitle(windowTitle);
        if(tick%5==0) try {
            var control=JsonParser.parseString(Files.readString(controlFile)).getAsJsonObject();
            if(control.get("suite_complete").getAsBoolean()) { client.stop(); return; }
        } catch(Exception ignored) { }
        if(client.player==null || client.level==null || client.gameMode==null
            || client.gameMode.getPlayerMode()!=net.minecraft.world.level.GameType.SPECTATOR) return;
        Entity actor=client.level.players().stream().filter(p -> p.getName().getString().equals("FlyCraftAgent")).findFirst().orElse(null);
        if(actor==null) return;
        boolean settled=firstPerson;
        if(firstPerson) client.setCameraEntity(actor);
        else {
            client.setCameraEntity(client.player);
            client.options.setCameraType(CameraType.FIRST_PERSON);
            double yaw=Math.toRadians(actor.getYRot());
            Vec3 desired=actor.position().add(Math.sin(yaw)*distance+Math.cos(yaw)*side,
                height-client.player.getEyeHeight(),-Math.cos(yaw)*distance+Math.sin(yaw)*side);
            Vec3 delta=desired.subtract(client.player.position());
            Vec3 step=delta.scale(.25);
            if(step.length()>.4) step=step.normalize().scale(.4);
            Vec3 position=client.player.position().add(step);
            client.player.setPos(position.x,position.y,position.z); client.player.setDeltaMovement(Vec3.ZERO);
            Vec3 look=actor.position().add(0,1.15,0).subtract(client.player.getEyePosition());
            double aimYaw=Math.toDegrees(Math.atan2(-look.x,look.z));
            double aimPitch=-Math.toDegrees(Math.atan2(look.y,Math.hypot(look.x,look.z)));
            double currentYaw=client.player.getYRot(),currentPitch=client.player.getXRot();
            client.player.setYRot((float)(currentYaw+Math.clamp(CameraMotion.wrap(aimYaw-currentYaw)*.3,-6,6)));
            client.player.setXRot((float)Math.clamp(currentPitch+Math.clamp((aimPitch-currentPitch)*.3,-4.5,4.5),-90,90));
            settled=position.distanceTo(desired)<.25 && Math.abs(CameraMotion.wrap(aimYaw-client.player.getYRot()))<2
                && Math.abs(aimPitch-client.player.getXRot())<2;
        }
        if(!initialized && settled) {
            initialized=true;
            try { Files.writeString(readyFile,"{\"ready\":true,\"role\":\"recording_only\"}",StandardOpenOption.CREATE_NEW); }
            catch(IOException error) { throw new IllegalStateException(error); }
            FlyCraftMod.LOGGER.info("FLYCRAFT_SPECTATOR ready actor={} view={}",actor.getUUID(),firstPerson ? "first_person" : "third_person");
        }
    }
    public void rendered() {
        if(!initialized || frameRequested) return;
        frameRequested=true;
        var client=Minecraft.getInstance();
        Screenshot.takeScreenshot(client.gameRenderer.mainRenderTarget(),image -> {
            try(image) { image.writeToFile(frameFile); }
            catch(IOException error) { throw new IllegalStateException(error); }
        });
    }
}

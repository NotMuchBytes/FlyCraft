package org.flycraft.bridge;

import com.google.gson.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;

/** Opt-in local play session; neural resource mode and engineered follow mode. */
public final class CompanionSession {
    private static HeadlessAgent actor;
    private static Path controlFile;
    private static String worldName;
    private static long started=-1, serial;
    private static int maxTicks;
    private static Properties configuration;
    private static Process bridge;
    private static Path bridgeLog;
    private static String lastRequest="";

    public static void initialize() {
        var config=new Properties();
        try(var reader=Files.newBufferedReader(Path.of("flycraft-companion.properties"))) { config.load(reader); }
        catch(IOException error) { throw new IllegalStateException(error); }
        configuration=config;
        worldName=config.getProperty("worldName");
        controlFile=Path.of(config.getProperty("controlFile"));
        maxTicks=Integer.parseInt(config.getProperty("maxRunTicks","1200"));
        if(worldName==null || worldName.isBlank() || maxTicks<20 || maxTicks>2400)
            throw new IllegalArgumentException("Companion needs an exact world name and a 1-120 second run bound");
        ServerTickEvents.END_SERVER_TICK.register(CompanionSession::tick);
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            if(actor!=null) { instruction(false,true); actor.close(); actor=null; }
            if(bridge!=null) { bridge.destroy(); bridge=null; }
            started=-1;
        });
        CommandRegistrationCallback.EVENT.register((dispatcher,registries,environment) ->
            dispatcher.register(Commands.literal("flycraft")
                .then(Commands.literal("start").executes(context -> {
                    if(actor==null || !matches(context.getSource().getServer())) {
                        context.getSource().sendFailure(Component.literal("Open the companion world: "+worldName)); return 0;
                    }
                    if(!actor.alive()) { context.getSource().sendFailure(Component.literal("FlyCraft is dead. /flycraft respawn or /flycraft follow brings it back.")); return 0; }
                    actor.stopCompanion(context.getSource().getServer().getTickCount()); instruction(false,true);
                    if(bridge==null || !bridge.isAlive()) startBridge();
                    if(!bridgeReady()) {
                        context.getSource().sendFailure(Component.literal("FlyCraft's brain is still loading or unavailable. Try /flycraft status shortly.")); return 0;
                    }
                    serial++; started=-1; instruction(true,false);
                    context.getSource().sendSuccess(() -> Component.literal("FlyCraft started: one log, at most "+maxTicks/20+" game seconds. /flycraft stop pauses it."),false);
                    return 1;
                }))
                .then(Commands.literal("follow").executes(context -> {
                    if(actor==null || !matches(context.getSource().getServer())) {
                        context.getSource().sendFailure(Component.literal("Open the companion world: "+worldName)); return 0;
                    }
                    var owner=context.getSource().getPlayerOrException();
                    instruction(false,true); started=-1;
                    actor.follow(context.getSource().getServer(),owner);
                    context.getSource().sendSuccess(() -> Component.literal("FlyCraft is following you using companion pathfinding. /flycraft stop makes it stay."),false); return 1;
                }))
                .then(Commands.literal("respawn").executes(context -> {
                    if(actor==null || !matches(context.getSource().getServer())) return 0;
                    instruction(false,true); started=-1;
                    actor.respawnCompanion(context.getSource().getServer(),context.getSource().getPlayerOrException());
                    context.getSource().sendSuccess(() -> Component.literal("FlyCraft is alive. /flycraft follow starts following."),false); return 1;
                }))
                .then(Commands.literal("stop").executes(context -> {
                    if(actor==null || !matches(context.getSource().getServer())) return 0;
                    instruction(false,true); started=-1;
                    actor.stopCompanion(context.getSource().getServer().getTickCount());
                    context.getSource().sendSuccess(() -> Component.literal("FlyCraft paused. You can keep playing."),false); return 1;
                }))
                .then(Commands.literal("status").executes(context -> {
                    context.getSource().sendSuccess(() -> Component.literal(actor==null ? "Open companion world: "+worldName : !actor.alive() ? "FlyCraft is dead; /flycraft follow respawns it and follows you." : actor.following() ? "FlyCraft follow mode: "+actor.companionStatus() : "FlyCraft ready. /flycraft follow; /flycraft start for neural resource mode."),false); return 1;
                }))));
    }

    private static boolean matches(MinecraftServer server) {
        return server.isSingleplayer() && worldName.equals(server.getWorldData().getLevelName());
    }

    private static boolean bridgeReady() {
        if(bridge==null || !bridge.isAlive() || bridgeLog==null) return false;
        try { return Files.readString(bridgeLog).contains("\"status\": \"ready\""); }
        catch(IOException error) { return false; }
    }

    private static void startBridge() {
        try {
            Path project=Path.of(configuration.getProperty("projectDirectory")).toAbsolutePath();
            Path python=Path.of(configuration.getProperty("pythonExecutable")).toAbsolutePath();
            Path checkpoint=Path.of(configuration.getProperty("checkpointFile")).toAbsolutePath();
            if(!Files.isRegularFile(python) || !Files.isRegularFile(checkpoint)
                || !Files.isRegularFile(project.resolve("minecraft_bridge.py"))) throw new IOException("Companion runtime files unavailable");
            Path evidence=controlFile.resolveSibling("session_"+serial); Files.createDirectories(evidence);
            bridgeLog=evidence.resolve("bridge_launcher.log");
            bridge=new ProcessBuilder(python.toString(),"-u",project.resolve("minecraft_bridge.py").toString(),
                "--host","127.0.0.1","--port",configuration.getProperty("bridgePort","8875"),
                "--phase8-checkpoint",checkpoint.toString(),"--phase8-results",evidence.resolve("controller.jsonl").toString(),
                "--phase8-control",controlFile.toString(),"--log",evidence.resolve("bridge.jsonl").toString())
                .directory(project.toFile()).redirectErrorStream(true).redirectOutput(bridgeLog.toFile()).start();
            FlyCraftMod.LOGGER.info("FLYCRAFT_COMPANION brain pid={} evidence={}",bridge.pid(),evidence);
        } catch(IOException error) { throw new IllegalStateException("Cannot start the local companion brain",error); }
    }

    private static void instruction(boolean active,boolean complete) {
        var value=new JsonObject();
        value.addProperty("episode_id","companion_"+serial);
        value.addProperty("goal","one_log"); value.addProperty("condition","trained");
        value.addProperty("train",false); value.addProperty("policy_seed",91000+serial);
        value.addProperty("active",active); value.addProperty("suite_complete",complete);
        try {
            Path temporary=controlFile.resolveSibling(controlFile.getFileName()+".tmp");
            Files.writeString(temporary,value.toString());
            Files.move(temporary,controlFile,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
        } catch(IOException error) { throw new IllegalStateException(error); }
    }

    private static void tick(MinecraftServer server) {
        if(!matches(server)) return;
        if(actor==null) {
            if(server.getPlayerList().getPlayers().isEmpty()) return;
            serial=System.currentTimeMillis(); started=-1; instruction(false,true);
            actor=new HeadlessAgent();
            server.getPlayerList().broadcastSystemMessage(Component.literal("FlyCraft companion: /flycraft follow follows you; /flycraft stop makes it stay. /flycraft start selects neural resource mode."),false);
        }
        if(server.getTickCount()%5==0) {
            try {
                var control=JsonParser.parseString(Files.readString(controlFile)).getAsJsonObject();
                if(control.get("active").getAsBoolean() && !control.get("suite_complete").getAsBoolean()) {
                    if(started<0) started=server.getTickCount();
                    if(server.getTickCount()-started>=maxTicks) { instruction(false,true); started=-1;
                        server.getPlayerList().broadcastSystemMessage(Component.literal("FlyCraft's short attempt has ended. /flycraft start tries again."),false); }
                }
            } catch(IOException error) { throw new IllegalStateException(error); }
        }
        actor.tick(server);
        if(actor.ready() && server.getTickCount()%5==0) processLocalRequest(server);
        if(!actor.alive() && started>=0) { instruction(false,true); started=-1; }
    }

    /** Optional operator-only file control for background integration checks.
     * Never part of neural observations, and never enabled by an eval runner. */
    private static void processLocalRequest(MinecraftServer server) {
        String configured=configuration.getProperty("commandFile","");
        if(configured.isEmpty()) return;
        Path file=Path.of(configured);
        if(!Files.isRegularFile(file)) return;
        try {
            var request=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
            String id=request.get("request_id").getAsString();
            if(id.equals(lastRequest)) return;
            lastRequest=id;
            var owner=server.getPlayerList().getPlayer(UUID.fromString(request.get("owner_uuid").getAsString()));
            if(owner==null || owner.getGameProfile().name().equals("FlyCraftAgent")) return;
            String command=request.get("command").getAsString();
            if(!command.equals("follow") && !command.equals("stop")) return;
            instruction(false,true); started=-1;
            if(command.equals("follow")) actor.follow(server,owner);
            else actor.stopCompanion(server.getTickCount());
            var result=new JsonObject(); result.addProperty("request_id",id); result.addProperty("command",command);
            result.addProperty("alive",actor.alive()); result.addProperty("following",actor.following());
            result.addProperty("server_tick",server.getTickCount());
            Files.writeString(Path.of(file+".ack"),result.toString());
            Files.move(file,file.resolveSibling(file.getFileName()+".processed_"+System.currentTimeMillis()));
            FlyCraftMod.LOGGER.info("FLYCRAFT_COMPANION operator_request {}",result);
        } catch(Exception error) { FlyCraftMod.LOGGER.warn("Companion operator request failed",error); }
    }
}

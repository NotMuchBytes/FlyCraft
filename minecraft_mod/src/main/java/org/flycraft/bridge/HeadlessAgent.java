package org.flycraft.bridge;

import com.google.gson.*;
import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import io.netty.util.ReferenceCountUtil;
import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.core.*;
import net.minecraft.network.Connection;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.*;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.tags.*;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.item.*;
import net.minecraft.world.level.*;
import net.minecraft.world.phys.*;
import org.flycraft.bridge.control.*;

/** Server-only adapter: visible semantic rays, own inventory, vanilla survival
 * physics/interactions. It never chooses a gameplay action or aims at a target. */
public final class HeadlessAgent implements AutoCloseable {
    private static final Gson JSON=new Gson();
    private final Path controlFile;
    private final BufferedWriter trace;
    private final Properties properties;
    private final CameraDriver camera;
    private final int forwardTicks;
    private final boolean verifyMovement;
    private Vec3 movementStart=Vec3.ZERO;
    private final ExecutorService io=Executors.newSingleThreadExecutor(r -> {
        Thread thread=new Thread(r,"flycraft-headless-ipc"); thread.setDaemon(true); return thread;
    });
    private final AtomicBoolean pending=new AtomicBoolean();
    private Actor player;
    private EmbeddedChannel channel;
    private JsonObject control,ack;
    private String episode="",stopped="",terminalHandled="",action="";
    private long commandId,actionStarted,readyAt,inventoryRevision=1;
    private Map<String,Integer> previousInventory=Map.of();
    private static final ThreadLocal<HeadlessAgent> RESPAWNING=new ThreadLocal<>();
    private CompanionFollower follower;
    private long modeRevision,followCommand;
    private boolean deathReported;
    private String followStatus="paused";
    private BlockHitResult miningHit;
    private final CameraDriver.View view=new CameraDriver.View() {
        public double yaw() { return player.getYRot(); }
        public double pitch() { return player.getXRot(); }
        public void set(double yaw,double pitch) { player.setYRot((float)yaw); player.setXRot((float)pitch); }
    };

    public HeadlessAgent() {
        properties=new Properties();
        try(var reader=Files.newBufferedReader(Path.of("flycraft-headless.properties"))) {
            properties.load(reader); controlFile=Path.of(properties.getProperty("controlFile"));
            Path tracePath=Path.of(properties.getProperty("traceFile"));
            if(Boolean.parseBoolean(properties.getProperty("companion.enabled","false")))
                tracePath=tracePath.resolveSibling(tracePath.getFileName()+"."+System.currentTimeMillis()+".jsonl");
            trace=Files.newBufferedWriter(tracePath,StandardOpenOption.CREATE_NEW);
        } catch(IOException error) { throw new IllegalStateException(error); }
        forwardTicks=Integer.parseInt(properties.getProperty("motor.forwardTicks","5"));
        verifyMovement=Boolean.parseBoolean(properties.getProperty("motor.verifyMovement","true"));
        if(forwardTicks<1 || forwardTicks>10) throw new IllegalArgumentException("Invalid forward duration");
        properties.putIfAbsent("camera.mode","bounded"); camera=new CameraDriver(properties);
    }

    private static final class Actor extends ServerPlayer {
        private final MinecraftServer owner;
        int forwardTicks;
        long lastPhysicsTick=-1,physicsTicks;
        Actor(MinecraftServer server,ServerLevel level,CommonListenerCookie cookie) {
            this(server,level,cookie.gameProfile(),cookie.clientInformation());
        }
        Actor(MinecraftServer server,ServerLevel level,GameProfile profile,ClientInformation information) {
            super(server,level,profile,information); owner=server;
        }
        @Override public void tick() {
            if(lastPhysicsTick==owner.getTickCount()) return;
            lastPhysicsTick=owner.getTickCount(); physicsTicks++;
            zza=forwardTicks>0 ? 1F : 0F; xxa=0; yya=0;
            if(forwardTicks>0) forwardTicks--;
            super.tick();
            // A normal client connection invokes doTick from its packet listener.
            // This embedded connection has no network listener tick; invoke it
            // once here, retaining Player's normal travel, gravity and item touch.
            doTick();
            level().getChunkSource().move(this);
        }
    }

    private void spawn(MinecraftServer server) {
        if(!Boolean.parseBoolean(properties.getProperty("companion.enabled","false"))
            && !server.getPlayerList().getPlayers().isEmpty()) throw new IllegalStateException("Headless environment must start without players");
        UUID id=UUID.nameUUIDFromBytes(Path.of("").toAbsolutePath().toString().getBytes(StandardCharsets.UTF_8));
        var cookie=CommonListenerCookie.createInitial(new GameProfile(id,"FlyCraftAgent"),false);
        player=new Actor(server,server.overworld(),cookie);
        var connection=new Connection(PacketFlow.SERVERBOUND);
        channel=new EmbeddedChannel(connection);
        server.getPlayerList().placeNewPlayer(connection,player,cookie);
        player.setGameMode(GameType.SURVIVAL);
        BlockPos spawn=player.adjustSpawnLocation(server.overworld(),server.overworld().getRespawnData().pos());
        player.teleportTo(server.overworld(),spawn.getX()+.5,spawn.getY(),spawn.getZ()+.5,Set.of(),0,0,true);
        player.setDeltaMovement(Vec3.ZERO);
        player.connection.handleAcceptPlayerLoad(new ServerboundPlayerLoadedPacket());
        event("spawn",Map.of("player",id.toString(),"mode",player.gameMode().name(),"graphical_client",false,
            "position_xyz",List.of(player.getX(),player.getY(),player.getZ())));
    }

    public void tick(MinecraftServer server) {
        if(player==null) { spawn(server); return; }
        if(!Boolean.parseBoolean(properties.getProperty("companion.enabled","false")))
            for(ServerPlayer observer:server.getPlayerList().getPlayers())
                if(observer!=player && !observer.isSpectator()) observer.setGameMode(GameType.SPECTATOR);
        player.tick(); drainPackets();
        long tick=server.getTickCount();
        if(!player.isAlive()) {
            cancel("player_died",tick); follower=null; followStatus="dead";
            if(!deathReported) { modeRevision++; deathReported=true; event("companion_death",Map.of("server_tick",tick)); }
            return;
        }
        if(follower!=null) {
            var step=follower.tick(server,player); var movement=step.movement();
            camera.velocity(view,++followCommand,movement.yawRate(),0,tick,5);
            camera.tick(view,tick); player.setYHeadRot(player.getYRot());
            player.forwardTicks=movement.forward() ? 1 : 0;
            player.setJumping(movement.jump()); player.setSprinting(movement.sprint());
            if(!followStatus.equals(step.status()) || tick%20==0) event("companion_follow",Map.of(
                "server_tick",tick,"status",step.status(),"distance",step.distance(),"path_nodes",step.pathNodes(),
                "position_xyz",List.of(player.getX(),player.getY(),player.getZ()),"yaw",player.getYRot(),
                "movement",movement,"assistance","vanilla_pathfinding_not_neural"));
            followStatus=step.status();
            if(step.status().equals("owner_unavailable")) stopCompanion(tick);
            return;
        }
        if(tick%5==0) {
            try { control=JsonParser.parseString(Files.readString(controlFile)).getAsJsonObject(); }
            catch(Exception error) { cancel("control_unavailable",tick); return; }
        }
        if(control==null) return;
        if(control.get("suite_complete").getAsBoolean()) { cancel("suite_complete",tick); return; }
        String next=control.get("episode_id").getAsString();
        if(!episode.equals(next)) {
            cancel("episode_interrupted",tick); episode=next; ack=null; readyAt=tick+15;
            camera.reset(view,episode);
            event("episode_observed",Map.of("episode_id",episode,"position",position(),"inventory",inventory()));
        }
        camera.tick(view,tick);
        boolean terminal=control.has("terminal");
        if(terminal) {
            cancel("episode_boundary",tick);
            if(terminalHandled.equals(episode)) return;
        } else if(!control.get("active").getAsBoolean()) return;
        if(!terminal && !action.isEmpty()) { advance(tick); return; }
        if(!terminal && camera.busy()) return;
        if(tick%5!=0 || !terminal && (tick<readyAt || stopped.equals(episode)) || !pending.compareAndSet(false,true)) return;
        JsonObject request=observe(tick);
        String expected=episode;
        long expectedMode=modeRevision;
        long observationNanos=System.nanoTime();
        io.execute(() -> {
            try(var socket=new Socket()) {
                socket.connect(new java.net.InetSocketAddress("127.0.0.1",Integer.parseInt(properties.getProperty("bridgePort","8765"))),1500);
                socket.setSoTimeout(15_000);
                var writer=new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(),StandardCharsets.UTF_8));
                var reader=new BufferedReader(new InputStreamReader(socket.getInputStream(),StandardCharsets.UTF_8));
                writer.write(request.toString()); writer.newLine(); writer.flush();
                String line=reader.readLine();
                if(line==null) throw new IOException("Bridge closed without response");
                JsonObject response=JsonParser.parseString(line).getAsJsonObject();
                server.execute(() -> {
                    try {
                        if(modeRevision!=expectedMode || !player.isAlive()) return;
                        if(!response.get("status").getAsString().equals("ok")) throw new IllegalStateException(response.toString());
                        if(!expected.equals(episode) || server.getTickCount()-tick>40) { cancel("stale_response",server.getTickCount()); return; }
                        if(response.has("terminal_acknowledged") && response.get("terminal_acknowledged").getAsBoolean()) terminalHandled=episode;
                        if(!response.get("autonomy_status").getAsString().equals("running")) { stopped=episode; cancel("controller_done",server.getTickCount()); return; }
                        if(response.get("observe_only").getAsBoolean()) return;
                        try { control=JsonParser.parseString(Files.readString(controlFile)).getAsJsonObject(); }
                        catch(IOException error) { throw new IllegalStateException("Lifecycle changed before action execution",error); }
                        if(!expected.equals(control.get("episode_id").getAsString())
                            || !expected.equals(response.get("episode_id").getAsString())) {
                            cancel("episode_replaced_before_execution",server.getTickCount()); return;
                        }
                        if(control.has("terminal") || !control.get("active").getAsBoolean()) {
                            ack=JSON.toJsonTree(Map.of("command_id",response.get("command_id").getAsLong(),
                                "action",response.get("action").getAsString(),"status","not_executed",
                                "error","episode_ended_before_execution","block_changed",false)).getAsJsonObject();
                            return;
                        }
                        start(response.get("action").getAsString(),response.get("command_id").getAsLong(),tick,observationNanos,server.getTickCount());
                    } finally { pending.set(false); }
                });
            } catch(Exception error) {
                server.execute(() -> { if(modeRevision!=expectedMode) { pending.set(false); return; } cancel("bridge_connection_lost",server.getTickCount()); pending.set(false); readyAt=server.getTickCount()+20;
                    event("bridge_error",Map.of("error",error.toString())); });
            }
        });
    }

    public boolean alive() { return player!=null && player.isAlive(); }
    public boolean ready() { return player!=null; }
    public boolean following() { return follower!=null; }
    public String companionStatus() { return followStatus; }
    public void stopCompanion(long tick) {
        modeRevision++; follower=null;
        if(player!=null) { cancel("companion_paused",tick); player.setJumping(false); player.setSprinting(false); }
        followStatus=alive() ? "paused" : "dead";
    }
    public void follow(MinecraftServer server,ServerPlayer owner) {
        if(!Boolean.parseBoolean(properties.getProperty("companion.enabled","false"))) throw new IllegalStateException("Companion mode required");
        stopCompanion(server.getTickCount());
        if(!alive()) respawnCompanion(server,owner);
        camera.reset(view,"companion_follow"); followCommand=0;
        follower=new CompanionFollower(player,owner); followStatus="following";
        event("companion_follow_started",Map.of("owner",owner.getUUID().toString(),"assistance","vanilla_pathfinding_not_neural"));
    }
    public static ServerPlayer createRespawnPlayer(MinecraftServer server,ServerLevel level,GameProfile profile,ClientInformation information) {
        HeadlessAgent agent=RESPAWNING.get();
        if(agent!=null && agent.player.getUUID().equals(profile.id())) return new Actor(server,level,profile,information);
        return new ServerPlayer(server,level,profile,information);
    }
    public void respawnCompanion(MinecraftServer server,ServerPlayer owner) {
        if(!Boolean.parseBoolean(properties.getProperty("companion.enabled","false"))) throw new IllegalStateException("Companion mode required");
        stopCompanion(server.getTickCount());
        if(alive()) return;
        RESPAWNING.set(this);
        try { player=(Actor)server.getPlayerList().respawn(player,false,net.minecraft.world.entity.Entity.RemovalReason.KILLED); }
        finally { RESPAWNING.remove(); }
        player.connection.handleAcceptPlayerLoad(new ServerboundPlayerLoadedPacket());
        deathReported=false; inventoryRevision++; previousInventory=Map.of();
        // Explicit companion recovery only. A fresh life may be placed beside
        // its owner; subsequent following walks and never teleports to catch up.
        for(int radius=2;radius<=8;radius++) for(int dy=0;dy<=8;dy++) for(int dx=-radius;dx<=radius;dx++) for(int dz=-radius;dz<=radius;dz++) {
            if(Math.max(Math.abs(dx),Math.abs(dz))!=radius) continue;
            BlockPos pos=owner.blockPosition().offset(dx,dy,dz); var level=owner.level();
            if(!level.getWorldBorder().isWithinBounds(pos) || !level.getFluidState(pos).isEmpty()
                || !level.getFluidState(pos.above()).isEmpty()
                || !level.getBlockState(pos.below()).isFaceSturdy(level,pos.below(),Direction.UP)) continue;
            Vec3 target=Vec3.atBottomCenterOf(pos);
            if(!level.noCollision(player,player.getBoundingBox().move(target.subtract(player.position())))) continue;
            player.teleportTo(level,target.x,target.y,target.z,Set.of(),owner.getYRot(),0,true);
            player.setDeltaMovement(Vec3.ZERO); drainPackets();
            event("companion_respawn",Map.of("placement","safe_owner_adjacent","server_tick",server.getTickCount(),
                "health",player.getHealth(),"inventory",inventory(),"position_xyz",List.of(player.getX(),player.getY(),player.getZ())));
            followStatus="paused"; return;
        }
        event("companion_respawn",Map.of("placement","vanilla_spawn_no_safe_owner_position","server_tick",server.getTickCount()));
        followStatus="paused";
    }

    private void drainPackets() {
        channel.runPendingTasks();
        Object packet;
        while((packet=channel.readOutbound())!=null) {
            if(packet instanceof ClientboundPlayerPositionPacket position)
                player.connection.handleAcceptTeleportPacket(new ServerboundAcceptTeleportationPacket(position.id()));
            ReferenceCountUtil.release(packet);
        }
    }

    private record Target(String kind,String id,Vec3 point,double distance,double angle,BlockHitResult hit) { }
    private double bearing(Vec3 point) {
        return Math.toRadians(CameraMotion.wrap(Math.toDegrees(Math.atan2(-(point.x-player.getX()),point.z-player.getZ()))-player.getYRot()));
    }
    private BlockHitResult ray(Vec3 end) {
        return player.level().clip(new ClipContext(player.getEyePosition(),end,ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,player));
    }
    private BlockHitResult crosshair() { return ray(player.getEyePosition().add(player.getLookAngle().scale(3))); }
    private Target sense() {
        Vec3 eye=player.getEyePosition(); Target target=null;
        for(double dy:new double[]{-40,-20,0,20,40}) for(double dp:new double[]{-30,0,30}) {
            double yaw=Math.toRadians(player.getYRot()+dy),pitch=Math.toRadians(Math.clamp(player.getXRot()+dp,-85,85));
            Vec3 direction=new Vec3(-Math.sin(yaw)*Math.cos(pitch),-Math.sin(pitch),Math.cos(yaw)*Math.cos(pitch));
            BlockHitResult hit=ray(eye.add(direction.scale(12)));
            double distance=eye.distanceTo(hit.getLocation());
            if(hit.getType()==HitResult.Type.BLOCK && player.level().getBlockState(hit.getBlockPos()).is(BlockTags.LOGS)
                && (target==null || distance<target.distance))
                target=new Target("block",hit.getBlockPos().toShortString(),hit.getLocation(),distance,bearing(hit.getLocation()),hit);
        }
        for(ItemEntity item:player.level().getEntitiesOfClass(ItemEntity.class,player.getBoundingBox().inflate(12))) {
            if(!item.getItem().is(ItemTags.LOGS)) continue;
            Vec3 point=item.position().add(0,.1,0),delta=point.subtract(eye);
            double distance=delta.length(),pitch=-Math.toDegrees(Math.atan2(delta.y,Math.hypot(delta.x,delta.z)));
            if(distance<=12 && Math.abs(bearing(point))<=Math.toRadians(50) && Math.abs(pitch-player.getXRot())<=45
                && ray(point).getType()==HitResult.Type.MISS && (target==null || !target.kind.equals("drop") || distance<target.distance))
                target=new Target("drop","item:"+item.getId(),point,distance,bearing(point),null);
        }
        return target;
    }
    private static String kind(ItemStack stack) {
        if(stack.is(ItemTags.LOGS)) return "log"; if(stack.is(ItemTags.PLANKS)) return "planks";
        if(stack.is(Items.STICK)) return "sticks"; if(stack.is(Items.CRAFTING_TABLE)) return "crafting_table";
        if(stack.is(Items.WOODEN_PICKAXE)) return "wooden_pickaxe"; return "other";
    }
    private Map<String,Integer> inventory() {
        Map<String,Integer> counts=new LinkedHashMap<>();
        for(String key:new String[]{"log","planks","sticks","crafting_table","table_placed","wooden_pickaxe"}) counts.put(key,0);
        for(int slot=0;slot<player.getInventory().getContainerSize();slot++) {
            ItemStack stack=player.getInventory().getItem(slot); String key=kind(stack);
            if(counts.containsKey(key)) counts.merge(key,stack.getCount(),Integer::sum);
        }
        if(!counts.equals(previousInventory)) { inventoryRevision++; previousInventory=new LinkedHashMap<>(counts); }
        return counts;
    }
    private List<Double> position() { return List.of(player.getX(),player.getZ(),Math.toRadians(player.getYRot())); }
    private JsonObject observe(long tick) {
        Target target=sense(); BlockHitResult center=crosshair(); Map<String,Integer> items=inventory();
        boolean mineable=target!=null && target.kind.equals("block") && target.distance<=3 && center.getType()==HitResult.Type.BLOCK
            && center.getBlockPos().equals(target.hit.getBlockPos());
        List<String> allowed=new ArrayList<>(List.of("NO_OP","TURN_LEFT","TURN_RIGHT","FORWARD"));
        if(mineable) allowed.add("COLLECT_LOG");
        if(items.get("log")>=1) allowed.add("CRAFT_PLANKS");
        Map<String,Object> telemetry=new LinkedHashMap<>();
        telemetry.put("session_id",player.getUUID().toString()); telemetry.put("position",position());
        telemetry.put("game_mode",player.gameMode().name()); telemetry.put("inventory",items);
        telemetry.put("inventory_revision",inventoryRevision); telemetry.put("inventory_consistent",true);
        telemetry.put("visible",target!=null); telemetry.put("near",mineable || target!=null && target.distance<=1);
        telemetry.put("target_distance",target==null ? -1 : target.distance); telemetry.put("target_angle",target==null ? 0 : target.angle);
        telemetry.put("target_id",target==null ? "" : target.id); telemetry.put("target_kind",target==null ? "none" : target.kind);
        telemetry.put("station_visible",false); telemetry.put("allowed_actions",allowed);
        telemetry.put("view_yaw_degrees",player.getYRot()); telemetry.put("view_pitch_degrees",player.getXRot());
        String sector="not_visible";
        if(target!=null) {
            double degrees=Math.toDegrees(target.angle);
            sector=degrees < -30 ? "far_left" : degrees < -10 ? "left" : degrees < 10 ? "center" : degrees < 30 ? "right" : "far_right";
        }
        JsonObject request=JSON.toJsonTree(Map.of("tick_id",tick,"control",control,"telemetry",telemetry,"sector",sector)).getAsJsonObject();
        if(ack!=null) request.add("ack",ack.deepCopy());
        return request;
    }

    private void start(String selected,long id,long observationTick,long observationNanos,long tick) {
        if(id<=commandId) return;
        commandId=id; action=selected; actionStarted=tick; readyAt=tick+10;
        event("action_start",Map.of("command_id",id,"action",action,"server_tick",tick,"position",position(),"inventory",inventory()));
        switch(action) {
            case "NO_OP" -> { }
            case "TURN_LEFT","TURN_RIGHT" -> {
                double degrees=Double.parseDouble(properties.getProperty("camera.turnDegrees","15"));
                if(!Double.isFinite(degrees) || degrees<=0 || degrees>45) throw new IllegalArgumentException("Invalid turn magnitude");
                var accepted=camera.relative(view,id,action.equals("TURN_LEFT") ? -degrees : degrees,0,observationTick,tick,observationNanos);
                if(!accepted.accepted()) finish("failed",accepted.reason(),false,tick);
            }
            case "FORWARD" -> { movementStart=player.position(); player.forwardTicks=forwardTicks; readyAt=tick+forwardTicks; }
            case "COLLECT_LOG" -> {
                miningHit=crosshair();
                if(miningHit.getType()!=HitResult.Type.BLOCK || !player.level().getBlockState(miningHit.getBlockPos()).is(BlockTags.LOGS)) {
                    finish("failed","invalid_crosshair_log",false,tick); return;
                }
                player.gameMode.handleBlockBreakAction(miningHit.getBlockPos(),ServerboundPlayerActionPacket.Action.START_DESTROY_BLOCK,
                    miningHit.getDirection(),player.level().getMaxY(),(int)id);
                readyAt=tick+120;
            }
            case "CRAFT_PLANKS" -> {
                int source=-1;
                for(int slot=0;slot<player.inventoryMenu.slots.size();slot++) {
                    var entry=player.inventoryMenu.getSlot(slot);
                    if(entry.container==player.getInventory() && entry.getItem().is(ItemTags.LOGS)) { source=slot; break; }
                }
                if(source<0 || !player.inventoryMenu.getCarried().isEmpty()) { finish("failed","crafting_input_unavailable",false,tick); return; }
                // Exactly one log enters the ordinary 2x2 inventory recipe.
                var menu=player.inventoryMenu;
                int before=inventory().get("planks");
                menu.clicked(source,0,ContainerInput.PICKUP,player);
                menu.clicked(1,1,ContainerInput.PICKUP,player);
                menu.clicked(source,0,ContainerInput.PICKUP,player);
                menu.clicked(0,0,ContainerInput.QUICK_MOVE,player);
                finish(inventory().get("planks")>=before+4 ? "success" : "failed",
                    inventory().get("planks")>=before+4 ? "" : "crafting_output_missing",false,tick);
            }
            default -> finish("failed","unsupported_headless_action",false,tick);
        }
    }
    private void advance(long tick) {
        if(action.equals("TURN_LEFT") || action.equals("TURN_RIGHT")) {
            if(!camera.busy()) finish(camera.completion().equals("settled") ? "success" : "failed",camera.completion().equals("settled") ? "" : camera.completion(),false,tick);
        } else if(action.equals("COLLECT_LOG")) {
            BlockPos pos=miningHit.getBlockPos(); var state=player.level().getBlockState(pos);
            if(!state.is(BlockTags.LOGS)) { finish("success","",true,tick); return; }
            BlockHitResult center=crosshair();
            if(center.getType()!=HitResult.Type.BLOCK || !center.getBlockPos().equals(pos)) { cancel("mining_aim_lost",tick); return; }
            if(tick>=readyAt) { cancel("mining_timeout",tick); return; }
            player.swing(net.minecraft.world.InteractionHand.MAIN_HAND);
            if(state.getDestroyProgress(player,player.level(),pos)*(tick-actionStarted+1)>=1)
                player.gameMode.handleBlockBreakAction(pos,ServerboundPlayerActionPacket.Action.STOP_DESTROY_BLOCK,
                    miningHit.getDirection(),player.level().getMaxY(),(int)commandId);
        } else if(tick>=readyAt) finish("success","",false,tick);
    }
    private void finish(String status,String error,boolean changed,long tick) {
        MovementFeedback.Result motion=null;
        if(action.equals("FORWARD")) {
            motion=MovementFeedback.measure(movementStart.x,movementStart.z,player.getX(),player.getZ());
            if(verifyMovement && status.equals("success") && !motion.moved()) { status="failed"; error="movement_blocked"; }
        }
        ack=JSON.toJsonTree(Map.of("command_id",commandId,"action",action,"status",status,"error",error,
            "block_changed",changed,"inventory_revision",inventoryRevision,"ticks",tick-actionStarted)).getAsJsonObject();
        if(motion!=null) {
            ack.addProperty("movement_distance",motion.distance()); ack.addProperty("movement_confirmed",motion.moved());
            ack.addProperty("movement_feedback_enabled",verifyMovement);
        }
        event("action_end",Map.of("ack",ack,"server_tick",tick,"position",position(),"inventory",inventory(),"physics_ticks",player.physicsTicks));
        action=""; player.forwardTicks=0; readyAt=tick+1;
    }
    private void cancel(String reason,long tick) {
        player.forwardTicks=0;
        if(camera.busy()) camera.cancel(reason,true);
        if(!action.isEmpty()) {
            if(action.equals("COLLECT_LOG") && miningHit!=null)
                player.gameMode.handleBlockBreakAction(miningHit.getBlockPos(),ServerboundPlayerActionPacket.Action.ABORT_DESTROY_BLOCK,
                    miningHit.getDirection(),player.level().getMaxY(),(int)commandId);
            finish("interrupted",reason,false,tick);
        }
    }
    private void event(String event,Map<String,?> value) {
        try { trace.write(JSON.toJson(Map.of("event",event,"episode_id",episode,"wall_time_unix_ms",System.currentTimeMillis(),"data",value))); trace.newLine(); trace.flush(); }
        catch(IOException error) { throw new IllegalStateException(error); }
    }
    @Override public void close() {
        io.shutdownNow(); camera.close();
        if(channel!=null) channel.finishAndReleaseAll();
        try { trace.close(); } catch(IOException error) { throw new IllegalStateException(error); }
    }
}

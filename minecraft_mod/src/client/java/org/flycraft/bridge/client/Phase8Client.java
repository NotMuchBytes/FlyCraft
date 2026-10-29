package org.flycraft.bridge.client;

import com.google.gson.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.inventory.*;
import net.minecraft.world.item.*;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.*;
import org.flycraft.bridge.FlyCraftMod;
import org.flycraft.bridge.control.CameraDriver;
import org.flycraft.bridge.control.MovementFeedback;

/** Visible sensing and bounded vanilla interaction transactions, never a planner. */
public final class Phase8Client {
    public static Phase8Client INSTANCE;
    private static final String[] ITEMS = {"log", "planks", "sticks", "crafting_table", "table_placed", "wooden_pickaxe"};
    private final Minecraft client = Minecraft.getInstance();
    private final ExecutorService io = Executors.newSingleThreadExecutor(r -> { Thread t = new Thread(r, "flycraft-phase8-ipc"); t.setDaemon(true); return t; });
    private final AtomicBoolean pending = new AtomicBoolean();
    private final Map<BlockPos, BlockState> serverBlocks = new HashMap<>();
    private final Map<BlockPos, Long> blockVersions = new HashMap<>();
    private Map<String, Integer> authoritative = new HashMap<>();
    private ItemStack[] serverInventory;
    private long inventoryRevision, blockRevision, tick, readyAt, actionStarted, actionId, initialBlockVersion, initialInventoryVersion;
    private String episode = "", stoppedEpisode = "", action = "", stage = "";
    private String terminalHandledEpisode="";
    private JsonObject control, lastAck;
    private BlockHitResult targetHit, groundHit, stationHit, visibleStationHit, miningHit, placementHit;
    private Target sensed;
    private int craftCell, craftSubstage, sourceSlot;
    private int[] craftSlots;
    private String craftInput, craftOutput;
    private int initialOutput, expectedOutput;
    private long lastCraftClick;
    private Path taskPath;
    private CameraDriver camera;
    private CameraProbe cameraProbe;
    private boolean strictInteractions;
    private double turnDegrees=15;
    private int forwardTicks=5;
    private boolean verifyMovement;
    private Vec3 movementStart=Vec3.ZERO;
    private String captureWindowTitle;
    private final CameraDriver.View cameraView=new CameraDriver.View() {
        public double yaw() { return client.player.getYRot(); }
        public double pitch() { return client.player.getXRot(); }
        public void set(double yaw,double pitch) { client.player.setYRot((float)yaw); client.player.setXRot((float)pitch); }
    };

    public void initialize() {
        INSTANCE = this;
        Properties properties = new Properties();
        try (Reader reader = Files.newBufferedReader(Path.of("flycraft-phase8-client.properties"))) { properties.load(reader); }
        catch (IOException e) { throw new IllegalStateException("Phase 8 client needs its control-file configuration", e); }
        taskPath = Path.of(properties.getProperty("controlFile"));
        captureWindowTitle=properties.getProperty("capture.windowTitle","");
        String cameraMode=properties.getProperty("camera.mode","legacy");
        strictInteractions=!cameraMode.equals("legacy");
        forwardTicks=Integer.parseInt(properties.getProperty("motor.forwardTicks","5"));
        verifyMovement=Boolean.parseBoolean(properties.getProperty("motor.verifyMovement","true"));
        if(forwardTicks<1 || forwardTicks>10) throw new IllegalArgumentException("Invalid forward duration");
        if(strictInteractions) {
            camera=new CameraDriver(properties);
            turnDegrees=Double.parseDouble(properties.getProperty("camera.turnDegrees","15"));
            if(!Double.isFinite(turnDegrees) || turnDegrees<=0 || turnDegrees>45) throw new IllegalArgumentException("invalid turn step");
            if(Boolean.parseBoolean(properties.getProperty("camera.probe","false")))
                cameraProbe=new CameraProbe(camera,Path.of(properties.getProperty("camera.probeFile")));
            Runtime.getRuntime().addShutdownHook(new Thread(() -> { if(cameraProbe!=null) cameraProbe.close(); camera.close(); },"flycraft-camera-close"));
        }
        ClientTickEvents.END_CLIENT_TICK.register(c -> onTick());
        FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 client enabled");
    }

    public void blockPacket(BlockPos pos, BlockState state) {
        if (serverBlocks.size() > 256) { serverBlocks.clear(); blockVersions.clear(); }
        serverBlocks.put(pos.immutable(), state);
        blockVersions.put(pos.immutable(), ++blockRevision);
    }
    public void renderedCamera(double yaw,double pitch) { if(camera!=null) camera.rendered(yaw,pitch); }

    private void ensureServerInventory() {
        if (client.player != null && (serverInventory == null || serverInventory.length != client.player.getInventory().getContainerSize())) {
            serverInventory = new ItemStack[client.player.getInventory().getContainerSize()];
            Arrays.fill(serverInventory, ItemStack.EMPTY);
        }
    }
    private AbstractContainerMenu packetMenu(int containerId) {
        if (client.player == null) return null;
        return containerId == 0 ? client.player.inventoryMenu : client.player.containerMenu.containerId == containerId ? client.player.containerMenu : null;
    }
    public void contentsPacket(int containerId, List<ItemStack> items) {
        ensureServerInventory(); AbstractContainerMenu menu = packetMenu(containerId);
        if (menu == null) return;
        for (int i = 0; i < Math.min(items.size(), menu.slots.size()); i++) updateServerSlot(menu.getSlot(i), items.get(i));
        publishServerInventory();
    }
    public void slotPacket(int containerId, int slot, ItemStack stack) {
        ensureServerInventory(); AbstractContainerMenu menu = packetMenu(containerId);
        if (menu == null || slot < 0 || slot >= menu.slots.size()) return;
        updateServerSlot(menu.getSlot(slot), stack); publishServerInventory();
    }
    public void inventoryPacket(int slot, ItemStack stack) {
        ensureServerInventory();
        if (serverInventory != null && slot >= 0 && slot < serverInventory.length) { serverInventory[slot] = stack.copy(); publishServerInventory(); }
    }
    private void updateServerSlot(Slot slot, ItemStack stack) {
        int index = slot.getContainerSlot();
        if (slot.container == client.player.getInventory() && index >= 0 && index < serverInventory.length) serverInventory[index] = stack.copy();
    }
    private void publishServerInventory() {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (String key : ITEMS) counts.put(key, 0);
        for (ItemStack stack : serverInventory) {
            String key = itemKind(stack);
            if (counts.containsKey(key)) counts.merge(key, stack.getCount(), Integer::sum);
        }
        authoritative = counts; inventoryRevision++;
    }

    private Map<String, Integer> inventory() {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (String key : ITEMS) counts.put(key, 0);
        for (int i = 0; i < client.player.getInventory().getContainerSize(); i++) {
            ItemStack stack = client.player.getInventory().getItem(i);
            String kind = itemKind(stack);
            if (counts.containsKey(kind)) counts.merge(kind, stack.getCount(), Integer::sum);
        }
        return counts;
    }

    private static String itemKind(ItemStack stack) {
        if (stack.is(ItemTags.LOGS)) return "log";
        if (stack.is(ItemTags.PLANKS)) return "planks";
        if (stack.is(Items.STICK)) return "sticks";
        if (stack.is(Items.CRAFTING_TABLE)) return "crafting_table";
        if (stack.is(Items.WOODEN_PICKAXE)) return "wooden_pickaxe";
        return "other";
    }

    private void onTick() {
        tick++;
        if(!captureWindowTitle.isEmpty()) client.getWindow().setTitle(captureWindowTitle);
        // The server can close before our final poll. Read the lifecycle signal
        // even on the disconnected screen so an owned test client exits normally.
        if (tick % 5 == 0) {
            try { control = JsonParser.parseString(Files.readString(taskPath)).getAsJsonObject(); }
            catch (Exception ignored) { return; }
        }
        if (control != null && control.get("suite_complete").getAsBoolean()) { cancel(""); client.stop(); return; }
        if (client.player == null || client.level == null || client.gameMode == null) {
            cancel("connection_lost"); return;
        }
        if(camera!=null) camera.tick(cameraView,tick);
        if (tick % 5 == 0 && control != null) {
            String nextEpisode = control.get("episode_id").getAsString();
            if (!nextEpisode.equals(episode)) {
                cancel("episode_interrupted"); episode = nextEpisode; lastAck = null; readyAt = tick + 15;
                serverBlocks.clear(); blockVersions.clear();
                if(camera!=null) camera.reset(cameraView,episode);
            }
        }
        if (control == null) return;
        boolean terminal=control.has("terminal");
        if(terminal) {
            cancel("episode_boundary");
            if(terminalHandledEpisode.equals(episode)) return;
        } else if(!control.get("active").getAsBoolean()) return;
        if(cameraProbe!=null) { cameraProbe.beforeTick(cameraView,tick); cameraProbe.tick(cameraView,tick); return; }
        if (!terminal && !action.isEmpty()) { advanceAction(); return; }
        if(!terminal && camera!=null && camera.busy()) return;
        if (tick % 5 != 0 || !terminal && (tick < readyAt || stoppedEpisode.equals(episode)) || !pending.compareAndSet(false, true)) return;
        JsonObject request = observe();
        String expectedEpisode = episode;
        long observationTick = tick;
        long observationNanos = System.nanoTime();
        io.execute(() -> {
            try (Socket socket = new Socket()) {
                socket.connect(new InetSocketAddress("127.0.0.1", 8765), 1500); socket.setSoTimeout(15_000);
                BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8));
                BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
                writer.write(request.toString()); writer.newLine(); writer.flush();
                String line = reader.readLine();
                if (line == null) throw new IOException("bridge closed without response");
                JsonObject response = JsonParser.parseString(line).getAsJsonObject();
                if (!response.get("status").getAsString().equals("ok")) throw new IOException(response.toString());
                client.execute(() -> {
                    if (client.player == null || !episode.equals(expectedEpisode) || tick - observationTick > 40) { cancel("stale_response"); return; }
                    if(response.has("terminal_acknowledged") && response.get("terminal_acknowledged").getAsBoolean())
                        terminalHandledEpisode=episode;
                    if (response.has("autonomy_status") && !response.get("autonomy_status").getAsString().equals("running")) {
                        cancel(""); stoppedEpisode = episode;
                        FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 controller_done episode={} status={}", episode, response.get("autonomy_status")); return;
                    }
                    if (response.get("observe_only").getAsBoolean()) { readyAt = tick + 5; return; }
                    try { control=JsonParser.parseString(Files.readString(taskPath)).getAsJsonObject(); }
                    catch(Exception error) { cancel("control_unavailable_before_execution"); return; }
                    if(!expectedEpisode.equals(control.get("episode_id").getAsString())
                        || !expectedEpisode.equals(response.get("episode_id").getAsString())) {
                        cancel("episode_replaced_before_execution"); return;
                    }
                    if(control.has("terminal") || !control.get("active").getAsBoolean()) {
                        lastAck=new JsonObject();
                        lastAck.addProperty("command_id",response.get("command_id").getAsLong());
                        lastAck.addProperty("action",response.get("action").getAsString());
                        lastAck.addProperty("status","not_executed");
                        lastAck.addProperty("error","episode_ended_before_execution");
                        lastAck.addProperty("block_changed",false);
                        return;
                    }
                    startAction(response.get("action").getAsString(), response.get("command_id").getAsLong(),observationTick,observationNanos);
                });
            } catch (Exception error) {
                client.execute(() -> { cancel("minecraft_connection_lost"); readyAt = tick + 20; });
                FlyCraftMod.LOGGER.error("FLYCRAFT_PHASE8 bridge_error episode={}", expectedEpisode, error);
            } finally { pending.set(false); }
        });
    }

    private record Target(String kind, String id, Vec3 point, double distance, double angle) { }
    private double angle(Vec3 point) {
        double desired = Math.toDegrees(Math.atan2(-(point.x - client.player.getX()), point.z - client.player.getZ()));
        return Math.toRadians(org.flycraft.bridge.control.CameraMotion.wrap(desired-client.player.getYRot()));
    }

    private boolean visible(Vec3 point) {
        Vec3 eye = client.player.getEyePosition(), delta = point.subtract(eye);
        double pitch = -Math.toDegrees(Math.atan2(delta.y, Math.hypot(delta.x, delta.z)));
        return delta.length() <= 12 && Math.abs(angle(point)) <= Math.toRadians(50)
            && Math.abs(pitch - client.player.getXRot()) <= 45
            && client.level.clip(new ClipContext(eye, point, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, client.player)).getType() == HitResult.Type.MISS;
    }

    private void sense() {
        sensed = null; targetHit = groundHit = stationHit = visibleStationHit = null;
        Vec3 eye = client.player.getEyePosition();
        for (double yawOffset : new double[]{-40, -20, 0, 20, 40}) {
            for (double pitchOffset : new double[]{-30, 0, 30}) {
                double yaw = Math.toRadians(client.player.getYRot() + yawOffset), pitch = Math.toRadians(Math.clamp(client.player.getXRot() + pitchOffset, -85, 85));
                Vec3 direction = new Vec3(-Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
                BlockHitResult hit = client.level.clip(new ClipContext(eye, eye.add(direction.scale(12)), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, client.player));
                if (hit.getType() != HitResult.Type.BLOCK) continue;
                BlockState state = client.level.getBlockState(hit.getBlockPos());
                double distance = eye.distanceTo(hit.getLocation());
                if (state.is(Blocks.CRAFTING_TABLE) && distance <= 4) visibleStationHit = hit;
                if (state.is(BlockTags.LOGS) && (sensed == null || distance < sensed.distance)) {
                    targetHit = hit; sensed = new Target("block", hit.getBlockPos().toShortString(), hit.getLocation(), distance, angle(hit.getLocation()));
                }
            }
        }
        // Dropped resources are observed only with line of sight and within the camera field of view.
        Target drop = null;
        for (Entity entity : client.level.entitiesForRendering()) {
            if (!(entity instanceof ItemEntity item) || !item.getItem().is(ItemTags.LOGS)) continue;
            Vec3 point = entity.getBoundingBox().getCenter();
            if (visible(point) && (drop == null || eye.distanceTo(point) < drop.distance))
                drop = new Target("drop", "item:" + entity.getId(), point, eye.distanceTo(point), angle(point));
        }
        if (drop != null) sensed = drop;
        // Placement ray is a visible, downward look, not a hidden-ground search.
        Vec3 ahead = client.player.position().add(-Math.sin(Math.toRadians(client.player.getYRot())) * 1.5, 0.1, Math.cos(Math.toRadians(client.player.getYRot())) * 1.5);
        BlockHitResult ground = client.level.clip(new ClipContext(eye, ahead.add(0, -1, 0), ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, client.player));
        if(strictInteractions) {
            BlockHitResult center=crosshair(4);
            if(validPlacement(center)) groundHit=center;
            if(center.getType()==HitResult.Type.BLOCK && client.level.getBlockState(center.getBlockPos()).is(Blocks.CRAFTING_TABLE)) stationHit=center;
        } else {
            if (validPlacement(ground)) groundHit = ground;
            stationHit=visibleStationHit;
        }
    }

    private boolean validPlacement(BlockHitResult hit) {
        if (hit == null || hit.getType() != HitResult.Type.BLOCK || hit.getDirection() != Direction.UP
                || client.player.getEyePosition().distanceTo(hit.getLocation()) > 4) return false;
        BlockPos pos = hit.getBlockPos().relative(hit.getDirection());
        AABB occupied = new AABB(pos.getX(), pos.getY(), pos.getZ(), pos.getX() + 1, pos.getY() + 1, pos.getZ() + 1);
        return client.level.getBlockState(pos).canBeReplaced() && !occupied.intersects(client.player.getBoundingBox())
                && client.level.noCollision(occupied) && !client.level.getBlockState(hit.getBlockPos()).is(Blocks.CRAFTING_TABLE);
    }

    private BlockHitResult crosshair(double range) {
        Vec3 eye=client.player.getEyePosition();
        return client.level.clip(new ClipContext(eye,eye.add(client.player.getLookAngle().scale(range)),ClipContext.Block.COLLIDER,ClipContext.Fluid.NONE,client.player));
    }
    private boolean aimedAt(BlockHitResult target,double range) {
        if(target==null) return false;
        BlockHitResult actual=crosshair(range);
        return actual.getType()==HitResult.Type.BLOCK && actual.getBlockPos().equals(target.getBlockPos());
    }

    private JsonObject observe() {
        sense();
        JsonObject request = new JsonObject(), telemetry = new JsonObject();
        request.addProperty("tick_id", tick); request.add("control", control.deepCopy());
        String sector = "not_visible";
        if (sensed != null) { double degrees = Math.toDegrees(sensed.angle); sector = degrees < -30 ? "far_left" : degrees < -10 ? "left" : degrees < 10 ? "center" : degrees < 30 ? "right" : "far_right"; }
        request.addProperty("sector", sector);
        telemetry.addProperty("session_id", client.player.getUUID().toString() + ":" + System.identityHashCode(client.level));
        JsonArray pose = new JsonArray(); pose.add(client.player.getX()); pose.add(client.player.getZ()); pose.add(Math.toRadians(client.player.getYRot())); telemetry.add("position", pose);
        telemetry.addProperty("visible", sensed != null); telemetry.addProperty("target_distance", sensed == null ? -1 : sensed.distance);
        telemetry.addProperty("target_angle", sensed == null ? 0 : sensed.angle);
        telemetry.addProperty("target_id", sensed == null ? "" : sensed.id); telemetry.addProperty("target_kind", sensed == null ? "none" : sensed.kind);
        boolean mineable = targetHit != null && sensed != null && sensed.kind.equals("block") && sensed.distance <= 3.0
                && (!strictInteractions || aimedAt(targetHit,3));
        telemetry.addProperty("near", mineable || sensed != null && sensed.distance <= 1.0);
        telemetry.addProperty("station_visible", visibleStationHit != null); telemetry.addProperty("game_mode", client.gameMode.getPlayerMode().name());
        telemetry.addProperty("view_yaw_degrees",client.player.getYRot()); telemetry.addProperty("view_pitch_degrees",client.player.getXRot());
        Map<String, Integer> current = inventory();
        telemetry.add("inventory", new Gson().toJsonTree(authoritative));
        telemetry.addProperty("inventory_revision", inventoryRevision);
        telemetry.addProperty("inventory_consistent", current.equals(authoritative));
        JsonArray allowed = new JsonArray(); for (String value : new String[]{"NO_OP", "TURN_LEFT", "TURN_RIGHT", "FORWARD"}) allowed.add(value);
        if (mineable) allowed.add("COLLECT_LOG");
        if (current.get("log") >= 1) allowed.add("CRAFT_PLANKS");
        if (current.get("planks") >= 2) allowed.add("CRAFT_STICKS");
        if (current.get("planks") >= 4) allowed.add("CRAFT_TABLE");
        if (current.get("crafting_table") >= 1 && groundHit != null && (!strictInteractions || aimedAt(groundHit,4))) allowed.add("PLACE_TABLE");
        if (current.get("planks") >= 3 && current.get("sticks") >= 2 && stationHit != null && (!strictInteractions || aimedAt(stationHit,4))) allowed.add("CRAFT_PICKAXE");
        telemetry.add("allowed_actions", allowed); request.add("telemetry", telemetry);
        if (lastAck != null) request.add("ack", lastAck.deepCopy());
        return request;
    }

    private void aim(Vec3 point) {
        Vec3 delta = point.subtract(client.player.getEyePosition());
        client.player.setYRot((float)Math.toDegrees(Math.atan2(-delta.x, delta.z)));
        client.player.setXRot((float)-Math.toDegrees(Math.atan2(delta.y, Math.hypot(delta.x, delta.z))));
    }

    private void startAction(String selected, long id,long observationTick,long observationNanos) {
        if (id <= 0 || id <= actionId) { readyAt = tick + 5; return; }
        actionId = id; action = selected; actionStarted = tick; stage = "";
        initialInventoryVersion = inventoryRevision; initialBlockVersion = blockRevision;
        FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 action_start episode={} id={} action={}", episode, id, action);
        switch (action) {
            case "NO_OP" -> readyAt = tick + 10;
            case "TURN_LEFT", "TURN_RIGHT" -> {
                double amount=action.equals("TURN_LEFT") ? -turnDegrees : turnDegrees;
                if(camera==null) { client.player.setYRot((float)(client.player.getYRot()+amount)); readyAt=tick+8; }
                else {
                    var accepted=camera.relative(cameraView,id,amount,0,observationTick,tick,observationNanos);
                    if(!accepted.accepted()) { finish("failed",accepted.reason(),false); return; }
                    readyAt=tick+camera.motion().config().relativeTimeoutTicks();
                }
            }
            case "FORWARD" -> { movementStart=client.player.position(); if(!strictInteractions) client.player.setXRot(0); client.options.keyUp.setDown(true); readyAt = tick + forwardTicks; }
            case "COLLECT_LOG" -> {
                if (targetHit == null || sensed == null || !sensed.kind.equals("block") || sensed.distance > 3) { finish("failed", "invalid_block", false); return; }
                if(strictInteractions && !aimedAt(targetHit,3)) { finish("failed","not_aimed_at_log",false); return; }
                miningHit = strictInteractions ? crosshair(3) : targetHit;
                if(!strictInteractions) aim(miningHit.getLocation());
                client.gameMode.startDestroyBlock(miningHit.getBlockPos(), miningHit.getDirection()); readyAt = tick + 120;
            }
            case "PLACE_TABLE" -> {
                if (!validPlacement(groundHit)) { finish("failed", "no_valid_visible_placement", false); return; }
                placementHit = groundHit; int slot = inventorySlot("crafting_table");
                if (slot < 0) { finish("failed", "missing_table", false); return; }
                if (slot >= 9) {
                    int menuSlot = findInventoryMenuSlot(slot);
                    client.gameMode.handleContainerInput(client.player.containerMenu.containerId, menuSlot, 0, ContainerInput.SWAP, client.player); slot = 0;
                }
                if(strictInteractions && !aimedAt(placementHit,4)) { finish("failed","not_aimed_at_placement",false); return; }
                client.player.getInventory().setSelectedSlot(slot); if(!strictInteractions) aim(placementHit.getLocation());
                var interaction = client.gameMode.useItemOn(client.player, InteractionHand.MAIN_HAND, placementHit);
                FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 placement_attempt id={} slot={} held={} hit={} interaction={}",
                    actionId, slot, client.player.getMainHandItem(), placementHit.getBlockPos(), interaction);
                readyAt = tick + 50;
            }
            default -> beginCraft();
        }
    }

    private void advanceAction() {
        if(camera!=null && (action.equals("TURN_LEFT") || action.equals("TURN_RIGHT"))) {
            if(!camera.busy()) finish(camera.completion().equals("settled") ? "success" : "failed",camera.completion().equals("settled") ? "" : camera.completion(),false);
            return;
        }
        if (action.equals("COLLECT_LOG")) {
            BlockPos pos = miningHit.getBlockPos();
            BlockState confirmed = serverBlocks.get(pos);
            if (blockVersions.getOrDefault(pos, 0L) > initialBlockVersion && confirmed != null && !confirmed.is(BlockTags.LOGS)) {
                finish("success", "", true); return;
            }
            if (tick >= readyAt) { finish("failed", "mining_timeout", false); return; }
            if (client.level.getBlockState(pos).is(BlockTags.LOGS)) {
                if(strictInteractions && !aimedAt(miningHit,3)) { finish("interrupted","mining_aim_lost",false); return; }
                client.gameMode.continueDestroyBlock(pos, miningHit.getDirection()); client.player.swing(InteractionHand.MAIN_HAND);
            }
            return;
        }
        if (action.equals("PLACE_TABLE")) {
            BlockPos pos = placementHit.getBlockPos().relative(placementHit.getDirection());
            BlockState confirmed = serverBlocks.get(pos);
            if (blockVersions.getOrDefault(pos, 0L) > initialBlockVersion && confirmed != null && confirmed.is(Blocks.CRAFTING_TABLE) && inventoryRevision > initialInventoryVersion) { finish("success", "", true); return; }
            if (tick >= readyAt) finish("failed", "placement_timeout", false);
            return;
        }
        if (action.startsWith("CRAFT_")) { advanceCraft(); return; }
        if (tick >= readyAt) { client.options.keyUp.setDown(false); finish("success", "", false); }
    }

    private int inventorySlot(String kind) {
        for (int i = 0; i < 36; i++) if (itemKind(client.player.getInventory().getItem(i)).equals(kind)) return i;
        return -1;
    }
    private int findInventoryMenuSlot(int inventorySlot) {
        for (Slot slot : client.player.containerMenu.slots)
            if (slot.container == client.player.getInventory() && slot.getContainerSlot() == inventorySlot) return slot.index;
        return -1;
    }
    private void click(int slot, int button, ContainerInput input) {
        client.gameMode.handleContainerInput(client.player.containerMenu.containerId, slot, button, input, client.player);
        lastCraftClick = tick;
    }

    private void beginCraft() {
        craftCell = craftSubstage = 0; stage = "fill"; lastCraftClick = tick;
        switch (action) {
            case "CRAFT_PLANKS" -> { craftInput = "log"; craftOutput = "planks"; expectedOutput = 4; craftSlots = new int[]{1}; }
            case "CRAFT_STICKS" -> { craftInput = "planks"; craftOutput = "sticks"; expectedOutput = 4; craftSlots = new int[]{1,3}; }
            case "CRAFT_TABLE" -> { craftInput = "planks"; craftOutput = "crafting_table"; expectedOutput = 1; craftSlots = new int[]{1,2,3,4}; }
            case "CRAFT_PICKAXE" -> {
                craftInput = "planks"; craftOutput = "wooden_pickaxe"; expectedOutput = 1; craftSlots = new int[]{1,2,3,5,8};
                if (stationHit == null) { finish("failed", "station_unavailable", false); return; }
                if(strictInteractions && !aimedAt(stationHit,4)) { finish("failed","not_aimed_at_station",false); return; }
                if(!strictInteractions) aim(stationHit.getLocation());
                client.gameMode.useItemOn(client.player, InteractionHand.MAIN_HAND, stationHit); stage = "open";
            }
            default -> { finish("failed", "unknown_action", false); return; }
        }
        initialOutput = authoritative.getOrDefault(craftOutput, 0); readyAt = tick + 300;
        if (!action.equals("CRAFT_PICKAXE") && client.player.containerMenu instanceof CraftingMenu) client.player.closeContainer();
    }

    private void advanceCraft() {
        if (tick >= readyAt) { finish("failed", "crafting_timeout", false); return; }
        if (tick - lastCraftClick < 3) return;
        if (stage.equals("open")) {
            if (client.player.containerMenu instanceof CraftingMenu) stage = "fill";
            return;
        }
        if (stage.equals("result")) {
            if (authoritative.getOrDefault(craftOutput, 0) >= initialOutput + expectedOutput && inventoryRevision > initialInventoryVersion) {
                if (client.player.containerMenu instanceof CraftingMenu) client.player.closeContainer();
                finish("success", "", false);
            }
            return;
        }
        if (craftCell >= craftSlots.length) {
            ItemStack result = client.player.containerMenu.getSlot(0).getItem();
            if (!itemKind(result).equals(craftOutput)) return;
            initialInventoryVersion = inventoryRevision; click(0, 0, ContainerInput.QUICK_MOVE); stage = "result"; return;
        }
        String ingredient = action.equals("CRAFT_PICKAXE") && craftCell >= 3 ? "sticks" : craftInput;
        if (craftSubstage == 0) {
            int inventorySlot = inventorySlot(ingredient);
            if (inventorySlot < 0) { finish("failed", "crafting_missing_resource", false); return; }
            sourceSlot = findInventoryMenuSlot(inventorySlot);
            if (sourceSlot < 0) { finish("failed", "invalid_inventory_slot", false); return; }
            click(sourceSlot, 0, ContainerInput.PICKUP); craftSubstage = 1;
        } else if (craftSubstage == 1) {
            click(craftSlots[craftCell], 1, ContainerInput.PICKUP); craftSubstage = 2;
        } else {
            if (!client.player.containerMenu.getCarried().isEmpty()) click(sourceSlot, 0, ContainerInput.PICKUP);
            else lastCraftClick = tick;
            craftCell++; craftSubstage = 0;
        }
    }

    private void finish(String status, String error, boolean changed) {
        MovementFeedback.Result motion=null;
        if(action.equals("FORWARD")) {
            motion=MovementFeedback.measure(movementStart.x,movementStart.z,client.player.getX(),client.player.getZ());
            if(verifyMovement && status.equals("success") && !motion.moved()) { status="failed"; error="movement_blocked"; }
        }
        client.options.keyUp.setDown(false); client.options.keyAttack.setDown(false); client.gameMode.stopDestroyBlock();
        if (!status.equals("success") && action.startsWith("CRAFT_")) {
            // Return partially placed ingredients through normal inventory clicks.
            if (!client.player.containerMenu.getCarried().isEmpty() && sourceSlot >= 0 && sourceSlot < client.player.containerMenu.slots.size())
                click(sourceSlot, 0, ContainerInput.PICKUP);
            int grid = client.player.containerMenu instanceof CraftingMenu ? 9 : 4;
            for (int slot = 1; slot <= grid; slot++) if (client.player.containerMenu.getSlot(slot).hasItem())
                click(slot, 0, ContainerInput.QUICK_MOVE);
            if (client.player.containerMenu instanceof CraftingMenu) client.player.closeContainer();
        }
        lastAck = new JsonObject(); lastAck.addProperty("command_id", actionId); lastAck.addProperty("action", action);
        lastAck.addProperty("status", status); lastAck.addProperty("error", error); lastAck.addProperty("block_changed", changed);
        lastAck.addProperty("inventory_revision", inventoryRevision); lastAck.addProperty("ticks", tick - actionStarted);
        if(motion!=null) {
            lastAck.addProperty("movement_distance",motion.distance()); lastAck.addProperty("movement_confirmed",motion.moved());
            lastAck.addProperty("movement_feedback_enabled",verifyMovement);
        }
        FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 action_end episode={} ack={}", episode, lastAck);
        boolean cameraTurn=camera!=null && (action.equals("TURN_LEFT") || action.equals("TURN_RIGHT"));
        action = ""; readyAt = tick + (cameraTurn ? 1 : 8);
    }

    private void cancel(String error) {
        if(camera!=null && camera.busy()) camera.cancel(error,true);
        if (client.player != null && client.gameMode != null && !action.isEmpty()) finish("interrupted", error, false);
        if (client.options != null) { client.options.keyUp.setDown(false); client.options.keyAttack.setDown(false); }
        action = "";
    }
}

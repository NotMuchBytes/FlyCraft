package org.flycraft.bridge;

import com.google.gson.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import net.fabricmc.fabric.api.event.player.PlayerBlockBreakEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ClientboundBlockUpdatePacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.*;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;

/** Disposable survival test fixtures and outcome scoring. No policy actions. */
public final class Phase8Harness {
    private record Trial(String condition, String goal, long seed, boolean train) { }
    private static List<Trial> trials;
    private static Path controlFile, resultsFile;
    private static Path startGate;
    private static Path cameraProbeResult;
    private static int index = -1, warmup, between, maxTicks;
    private static boolean active, complete;
    private static long started, programStarted, policySeed;
    private static double originX, originZ;
    private static int groundY;
    private static int maxSeconds;
    private static boolean initialized;
    private static boolean threeTrees;
    private static boolean headlessFixture;
    private static boolean unplacedTable;
    private static JsonObject terminal;
    private static int terminalWait;
    private static String trialIdPrefix;
    private static final Map<ServerPlayer, BlockPos> placements = new HashMap<>();

    public static void initialize() {
        try {
            Properties config = new Properties();
            try (Reader reader = Files.newBufferedReader(Path.of("flycraft-phase8.properties"))) { config.load(reader); }
            controlFile = Path.of(config.getProperty("controlFile"));
            resultsFile = Path.of(config.getProperty("resultsFile"));
            if (config.containsKey("startGate")) startGate = Path.of(config.getProperty("startGate"));
            if (config.containsKey("cameraProbeResult")) cameraProbeResult=Path.of(config.getProperty("cameraProbeResult"));
            if (Files.exists(resultsFile)) throw new IllegalStateException("refusing to overwrite Phase 8 results");
            maxTicks = Integer.parseInt(config.getProperty("maxTrialTicks", "1200"));
            maxSeconds = Integer.parseInt(config.getProperty("maxSeconds", "600"));
            policySeed = Long.parseLong(config.getProperty("policySeed", "9001"));
            trialIdPrefix = config.getProperty("trialIdPrefix", "trial_");
            if (!trialIdPrefix.matches("[A-Za-z0-9_-]+"))
                throw new IllegalArgumentException("Invalid trial identity prefix");
            threeTrees = Boolean.parseBoolean(config.getProperty("fixture.threeTrees", "false"));
            headlessFixture = Boolean.parseBoolean(config.getProperty("fixture.headless", "false"));
            unplacedTable = Boolean.parseBoolean(config.getProperty("fixture.unplacedTable", "false"));
            trials = new ArrayList<>();
            for (String line : Files.readAllLines(Path.of(config.getProperty("trialsFile")))) {
                if (line.isBlank() || line.startsWith("#")) continue;
                String[] columns = line.split(",");
                trials.add(new Trial(columns[0], columns[1], Long.parseLong(columns[2]), columns.length > 3 && Boolean.parseBoolean(columns[3])));
            }
            programStarted = System.nanoTime();
            FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 harness trials={}", trials.size());
        } catch (IOException error) { throw new IllegalStateException(error); }
    }

    private static String episodeId() {
        return trialIdPrefix + String.format(Locale.ROOT, "%04d", Math.max(index, 0));
    }

    private static void instruction(boolean enabled, boolean done) {
        JsonObject control = new JsonObject();
        control.addProperty("episode_id", episodeId());
        Trial trial = trials.get(Math.clamp(index, 0, trials.size() - 1));
        control.addProperty("goal", trial.goal); control.addProperty("condition", trial.condition);
        control.addProperty("train", trial.train); control.addProperty("policy_seed", policySeed);
        control.addProperty("active", enabled); control.addProperty("suite_complete", done);
        if (terminal != null) control.add("terminal", terminal.deepCopy());
        // No fixture coordinates, world/layout seeds, future states or success labels.
        try {
            Path temporary = controlFile.resolveSibling(controlFile.getFileName() + ".tmp");
            Files.writeString(temporary, control.toString());
            Files.move(temporary, controlFile, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException error) { throw new IllegalStateException(error); }
    }

    public static void tick(MinecraftServer server) {
        if (complete) return;
        if ((System.nanoTime() - programStarted) / 1_000_000_000L > maxSeconds) { finishSuite(server, "wall_budget"); return; }
        if (startGate != null && !Files.exists(startGate)) return;
        if (terminal != null) {
            boolean acknowledged=false;
            Path acknowledgment=Path.of(controlFile.toString()+".ack");
            try {
                if(Files.exists(acknowledgment)) acknowledged=JsonParser.parseString(Files.readString(acknowledgment))
                    .getAsJsonObject().get("episode_id").getAsString().equals(episodeId());
            } catch(Exception ignored) { }
            if(!acknowledged && ++terminalWait<100) return;
            JsonObject delivery=new JsonObject();
            delivery.addProperty("episode_id",episodeId());
            delivery.addProperty("acknowledged",acknowledged); delivery.addProperty("wait_ticks",terminalWait);
            try { Files.writeString(Path.of(resultsFile.toString()+".delivery.jsonl"),delivery+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND); }
            catch(IOException error) { throw new IllegalStateException(error); }
            FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 terminal_delivery {}",delivery);
            terminal=null;
        }
        if (server.getPlayerList().getPlayers().isEmpty()) return;
        ServerPlayer player = server.getPlayerList().getPlayers().getFirst();
        if (!initialized) {
            originX = Math.floor(player.getX()) + 0.5; originZ = Math.floor(player.getZ()) + 0.5;
            groundY = (int)Math.floor(player.getY()); initialized = true; between = 20;
        }
        if (warmup > 0) {
            if (--warmup == 0) { active = true; started = server.getTickCount(); instruction(true, false); }
            return;
        }
        if (!active) {
            if (--between > 0) return;
            index++;
            if (index >= trials.size()) { finishSuite(server, "complete"); return; }
            prepare(player, trials.get(index)); warmup = 20; return;
        }
        Trial trial = trials.get(index);
        Map<String, Integer> counts = inventory(player);
        boolean success = switch (trial.goal) {
            case "one_log" -> counts.get("log") >= 1;
            case "three_logs" -> counts.get("log") >= 3;
            case "planks" -> counts.get("planks") >= 4;
            case "sticks" -> counts.get("sticks") >= 4;
            case "crafting_table" -> counts.get("crafting_table") >= 1;
            case "wooden_pickaxe", "pickaxe_transaction" -> counts.get("wooden_pickaxe") >= 1;
            default -> false;
        };
        long elapsed = server.getTickCount() - started;
        boolean probeComplete=false;
        if(trial.goal.equals("camera_probe") && cameraProbeResult!=null && Files.exists(cameraProbeResult)) {
            try {
                JsonObject probe=JsonParser.parseString(Files.readString(cameraProbeResult)).getAsJsonObject();
                probeComplete=true; success=probe.get("success").getAsBoolean();
            } catch(Exception ignored) { }
        }
        if (success || probeComplete || elapsed >= maxTicks) {
            JsonObject result = new JsonObject();
            result.addProperty("episode_id", episodeId());
            result.addProperty("condition", trial.condition); result.addProperty("goal", trial.goal);
            result.addProperty("layout_seed", trial.seed); result.addProperty("success", success);
            result.addProperty("ticks", elapsed); result.addProperty("train", trial.train);
            result.add("inventory", new Gson().toJsonTree(counts));
            try { Files.writeString(resultsFile, result + "\n", StandardOpenOption.CREATE, StandardOpenOption.APPEND); }
            catch (IOException error) { throw new IllegalStateException(error); }
            FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 episode_end {}", result);
            active = false; between = 40;
            if(!trial.goal.equals("camera_probe")) {
                // Final own-player state, captured at exactly the scoring boundary.
                // It contains no goal-success label, map or fixture seed.
                terminal=new JsonObject(); terminalWait=0;
                terminal.addProperty("server_tick",server.getTickCount());
                terminal.add("inventory",new Gson().toJsonTree(counts));
                terminal.add("position",new Gson().toJsonTree(new double[]{player.getX(),player.getZ(),Math.toRadians(player.getYRot())}));
                instruction(false,false);
            }
        }
    }

    private static Map<String, Integer> inventory(ServerPlayer player) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (String key : new String[]{"log", "planks", "sticks", "crafting_table", "wooden_pickaxe"}) counts.put(key, 0);
        for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++) {
            ItemStack stack = player.getInventory().getItem(slot);
            String kind = stack.is(ItemTags.LOGS) ? "log" : stack.is(ItemTags.PLANKS) ? "planks" : stack.is(Items.STICK) ? "sticks" : stack.is(Items.CRAFTING_TABLE) ? "crafting_table" : stack.is(Items.WOODEN_PICKAXE) ? "wooden_pickaxe" : "other";
            if (counts.containsKey(kind)) counts.merge(kind, stack.getCount(), Integer::sum);
        }
        return counts;
    }

    private static void prepare(ServerPlayer player, Trial trial) {
        instruction(false, false);
        var level = player.level();
        player.closeContainer(); player.setGameMode(GameType.SURVIVAL); player.getInventory().clearContent();
        player.inventoryMenu.getCraftSlots().clearContent(); player.inventoryMenu.setCarried(ItemStack.EMPTY);
        for (int x = -7; x <= 7; x++) for (int z = -7; z <= 7; z++) for (int y = 0; y <= 5; y++)
            level.setBlock(BlockPos.containing(originX + x, groundY + y, originZ + z), Blocks.AIR.defaultBlockState(), 2);
        for (ItemEntity item : level.getEntitiesOfClass(ItemEntity.class, new AABB(originX - 12, groundY - 2, originZ - 12, originX + 12, groundY + 8, originZ + 12))) item.discard();
        player.teleportTo(level, originX, groundY, originZ, Set.of(), 0, 0, true);
        player.setDeltaMovement(0, 0, 0); player.setHealth(20); player.getFoodData().setFoodLevel(20);
        player.inventoryMenu.sendAllDataToRemote();
        if (trial.goal.equals("pickaxe_transaction")) {
            // Isolated transaction test ONLY. Never include this fixture in
            // from-empty-inventory wooden-pickaxe autonomy success rates.
            player.getInventory().add(new ItemStack(Items.OAK_PLANKS, 3));
            player.getInventory().add(new ItemStack(Items.STICK, 2));
            int stationDistance = unplacedTable ? 3 : 2;
            if (headlessFixture)
                level.setBlockAndUpdate(BlockPos.containing(originX, groundY, originZ + stationDistance), Blocks.OAK_PLANKS.defaultBlockState());
            BlockPos station = BlockPos.containing(originX, groundY + (headlessFixture ? 1 : 0), originZ + stationDistance);
            if (unplacedTable) player.getInventory().add(new ItemStack(Items.CRAFTING_TABLE));
            level.setBlockAndUpdate(station, (unplacedTable ? Blocks.STONE : Blocks.CRAFTING_TABLE).defaultBlockState());
            player.inventoryMenu.sendAllDataToRemote();
            FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 transaction_fixture id={} goal=pickaxe_transaction prepared_ingredients=true", index);
            initialState(player,trial);
            return;
        }
        Random rng = new Random(trial.seed);
        if (threeTrees && (trial.goal.equals("three_logs") || trial.goal.equals("wooden_pickaxe"))) {
            // Separate trunks offer three logs at eye height to the yaw-only policy.
            for (int lane = -1; lane <= 1; lane++) {
                double bearing = lane * 38 + (rng.nextDouble() - 0.5) * 8;
                double distance = (lane == 0 ? 2.2 : 4.1) + rng.nextDouble() * 0.5;
                placeTree(level, Math.toRadians(bearing), distance);
            }
            if (trial.goal.equals("wooden_pickaxe")) {
                // A visible face for horizontal, crosshair-only placement on flat ground.
                BlockPos support = BlockPos.containing(originX, groundY, originZ + 5);
                level.setBlockAndUpdate(support, Blocks.STONE.defaultBlockState());
                level.setBlockAndUpdate(support.above(), Blocks.STONE.defaultBlockState());
            }
        } else {
            double bearing = Math.toRadians(-40 + rng.nextDouble() * 80);
            placeTree(level, bearing, 2.0 + rng.nextDouble() * 1.5);
        }
        FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 episode_start id={} condition={} goal={} layout_seed={}", index, trial.condition, trial.goal, trial.seed);
        initialState(player,trial);
    }

    private static void placeTree(ServerLevel level, double bearing, double distance) {
        int x = (int)Math.floor(originX - Math.sin(bearing) * distance), z = (int)Math.floor(originZ + Math.cos(bearing) * distance);
        for (int y = 0; y < 3; y++) level.setBlockAndUpdate(new BlockPos(x, groundY + y, z), Blocks.OAK_LOG.defaultBlockState());
        for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++)
            level.setBlockAndUpdate(new BlockPos(x + dx, groundY + 3, z + dz), Blocks.OAK_LEAVES.defaultBlockState());
    }

    private static void initialState(ServerPlayer player,Trial trial) {
        JsonObject state=new JsonObject();
        state.addProperty("episode_id",episodeId());
        state.addProperty("world_seed",player.level().getSeed()); state.addProperty("layout_seed",trial.seed);
        state.addProperty("goal",trial.goal); state.addProperty("server_tick",player.level().getServer().getTickCount());
        state.addProperty("game_mode",player.gameMode().name());
        state.add("position_xyz_yaw_pitch",new Gson().toJsonTree(new double[]{player.getX(),player.getY(),player.getZ(),player.getYRot(),player.getXRot()}));
        state.add("inventory",new Gson().toJsonTree(inventory(player)));
        JsonArray blocks=new JsonArray();
        for(int x=-7;x<=7;x++) for(int z=-7;z<=7;z++) for(int y=0;y<=5;y++) {
            BlockPos position=BlockPos.containing(originX+x,groundY+y,originZ+z);
            var block=player.level().getBlockState(position);
            if(!block.isAir()) blocks.add(new Gson().toJsonTree(Map.of("position",List.of(position.getX(),position.getY(),position.getZ()),"state",block.toString())));
        }
        state.add("fixture_blocks",blocks);
        state.addProperty("replay_fidelity","Initial fixture snapshot; complete world/entity RNG replay is unverified");
        // Operator evidence only: this file is never part of agent observations.
        try { Files.writeString(Path.of(resultsFile.toString()+".initial.jsonl"),state+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND); }
        catch(IOException error) { throw new IllegalStateException(error); }
    }

    private static void finishSuite(MinecraftServer server, String reason) {
        complete = true; index = Math.min(index, trials.size() - 1); instruction(false, true);
        FlyCraftMod.LOGGER.info("FLYCRAFT_PHASE8 suite_end reason={}", reason);
        server.halt(false);
    }
}

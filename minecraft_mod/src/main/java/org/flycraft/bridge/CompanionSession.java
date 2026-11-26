package org.flycraft.bridge;

import com.google.gson.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.message.v1.ServerMessageEvents;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import org.flycraft.bridge.language.*;

/** Opt-in language/task interface. Collection remains policy-selected. */
public final class CompanionSession {
    private static final Gson JSON=new Gson();
    private static HeadlessAgent actor;
    private static Path controlFile,bridgeLog,aliasFile,eventFile;
    private static Properties configuration;
    private static WordMemory words;
    private static String worldName,lastRequest="",goal="one_log";
    private static long started=-1,serial;
    private static int maxTicks;
    private static Process bridge;
    private static CompanionOrder order;
    private static UUID movementOwner;
    private static final Map<UUID,Long> lastChat=new HashMap<>();

    public static void initialize() {
        configuration=new Properties();
        try(var reader=Files.newBufferedReader(Path.of("flycraft-companion.properties"))) { configuration.load(reader); }
        catch(IOException error) { throw new IllegalStateException(error); }
        worldName=configuration.getProperty("worldName");controlFile=Path.of(configuration.getProperty("controlFile"));
        aliasFile=controlFile.resolveSibling("learned_item_names.properties");eventFile=controlFile.resolveSibling("orders.jsonl");
        maxTicks=Integer.parseInt(configuration.getProperty("maxRunTicks","1200"));
        if(worldName==null || worldName.isBlank() || maxTicks<20 || maxTicks>2400)
            throw new IllegalArgumentException("Companion needs an exact world name and a 1-120 second run bound");
        try {
            words=new WordMemory(aliasFile);
        } catch(IOException error) { throw new IllegalStateException(error); }
        if(testHarness()) EnglishOrderHarness.initialize(configuration);
        ServerTickEvents.END_SERVER_TICK.register(CompanionSession::tick);
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            if(order!=null && order.busy()) { order.fail("world_closed");event("interrupted",Map.of("reason","world_closed")); }
            if(actor!=null) { instruction(false,true);actor.close();actor=null; }
            if(bridge!=null) { bridge.destroy();bridge=null; }
            started=-1;order=null;movementOwner=null;lastChat.clear();
        });
        ServerMessageEvents.CHAT_MESSAGE.register((message,sender,type) -> {
            if(!Boolean.parseBoolean(configuration.getProperty("chatCommands","true")))return;
            String text=message.signedContent();MinecraftServer server=sender.level().getServer();
            server.execute(() -> handleText(server,sender,text,!Boolean.parseBoolean(configuration.getProperty("chatRequiresName","true"))));
        });
        CommandRegistrationCallback.EVENT.register((dispatcher,registries,environment) -> dispatcher.register(Commands.literal("flycraft")
            .then(Commands.literal("say").then(Commands.argument("request",StringArgumentType.greedyString()).executes(context -> {
                handleText(context.getSource().getServer(),context.getSource().getPlayerOrException(),StringArgumentType.getString(context,"request"),true);return 1;
            })))
            .then(Commands.literal("start").executes(context -> {
                var owner=context.getSource().getPlayerOrException();var server=context.getSource().getServer();
                if(!available(server,owner) || !authorize(owner))return 0;
                if(!actor.alive()) { tell(owner,"I am dead. Use /flycraft respawn.");return 0; }
                order=null;movementOwner=owner.getUUID();goal="one_log";serial++;started=server.getTickCount();
                actor.stopCompanion(server.getTickCount());instruction(false,true);startBridgeIfNeeded();
                if(!bridgeReady()) { started=-1;tell(owner,"My brain is loading. Try /flycraft start shortly.");return 0; }
                actor.expectResource();instruction(true,false);tell(owner,"Trying one log for at most "+maxTicks/20+" seconds. Say stop to cancel.");return 1;
            }))
            .then(Commands.literal("follow").executes(context -> {handleText(context.getSource().getServer(),context.getSource().getPlayerOrException(),"follow me",true);return 1;}))
            .then(Commands.literal("stop").executes(context -> {handleText(context.getSource().getServer(),context.getSource().getPlayerOrException(),"stop",true);return 1;}))
            .then(Commands.literal("status").executes(context -> {handleText(context.getSource().getServer(),context.getSource().getPlayerOrException(),"status",true);return 1;}))
            .then(Commands.literal("respawn").executes(context -> {
                var owner=context.getSource().getPlayerOrException();var server=context.getSource().getServer();
                if(!available(server,owner) || !authorize(owner))return 0;
                cancel(server,owner);actor.respawnCompanion(server,owner);tell(owner,"Respawn requested. Follow or ask for an item when I am alive.");return 1;
            }))));
    }
    static boolean testHarness() { return configuration!=null && Boolean.parseBoolean(configuration.getProperty("integrationTestDedicated","false")); }
    static HeadlessAgent testActor() { if(!testHarness())throw new IllegalStateException("Test harness disabled");return actor; }
    static CompanionOrder testOrder() { if(!testHarness())throw new IllegalStateException("Test harness disabled");return order; }
    private static boolean matches(MinecraftServer server) {
        return (server.isSingleplayer() || testHarness()) && worldName.equals(server.getWorldData().getLevelName());
    }
    private static void tell(ServerPlayer player,String text) { player.sendSystemMessage(Component.literal("FlyCraft: "+text)); }
    private static boolean available(MinecraftServer server,ServerPlayer owner) {
        if(actor==null || !matches(server) || !actor.ready()) { tell(owner,"Open my configured companion world and wait for me to appear.");return false; }
        return true;
    }
    private static boolean authorize(ServerPlayer owner) {
        UUID current=order!=null && order.busy() ? order.owner : movementOwner;
        if(current!=null && !current.equals(owner.getUUID())) { tell(owner,"I am helping another player. Their stop command controls that task.");return false; }
        return true;
    }
    private static Map<String,String> vocabulary(UUID owner) {
        return words.forPlayer(owner);
    }
    public static void handleText(MinecraftServer server,ServerPlayer owner,String text,boolean directed) {
        if(!matches(server) || actor==null || !actor.ready() || owner.getGameProfile().name().equals("FlyCraftAgent"))return;
        var intent=EnglishOrders.parse(text,vocabulary(owner.getUUID()),directed);
        if(intent.kind()==EnglishOrders.Kind.IGNORE)return;
        long now=server.getTickCount();
        if(intent.kind()!=EnglishOrders.Kind.STOP && now-lastChat.getOrDefault(owner.getUUID(),-100L)<10) { tell(owner,"One request at a time, please.");return; }
        lastChat.put(owner.getUUID(),now);
        switch(intent.kind()) {
            case REJECT -> tell(owner,intent.message());
            case HELP -> tell(owner,"Try: FlyCraft, get me 3 logs; make me a wooden pickaxe; follow me; stop; status. Teach a name with: FlyCraft, teach timber means logs.");
            case STATUS -> {
                String task=order==null ? "No item request." : "Request for "+order.ownerName+": "+EnglishOrders.label(order.item,order.count)+"; "+order.phase().name().toLowerCase(Locale.ROOT)+"; received "+order.received()+"/"+order.count+".";
                var aware=actor.awareness();tell(owner,task+" Health "+aware.get("health")+", food "+aware.get("food")+", holding "+aware.get("inventory")+".");
            }
            case TEACH -> {
                try {
                    words.learn(owner.getUUID(),intent.alias(),intent.item());
                    event("word_learned",Map.of("speaker",owner.getUUID().toString(),"alias",intent.alias(),"item",intent.item()));
                    tell(owner,"For your requests, "+intent.alias()+" means "+intent.item().replace('_',' ')+". I will remember that name.");
                } catch(IOException error) { tell(owner,"I could not save that word; it was not learned."); }
            }
            case STOP -> { if(authorize(owner)) { cancel(server,owner);tell(owner,"Stopped. Already dropped items remain in the world."); } }
            case FOLLOW -> {
                if(!authorize(owner))return;cancel(server,owner);movementOwner=owner.getUUID();actor.follow(server,owner);
                tell(owner,"Following you using companion navigation.");
            }
            case GET -> {
                if(!authorize(owner))return;
                if(order!=null && order.busy()) { tell(owner,"I am still working on your request. Say stop before replacing it.");return; }
                if(!actor.alive()) { tell(owner,"I am dead. Use /flycraft respawn first.");return; }
                actor.stopCompanion(now);movementOwner=null;serial++;
                order=new CompanionOrder(owner.getUUID(),owner.getGameProfile().name(),intent.item(),intent.count(),now);
                goal=EnglishOrders.goal(intent.item());started=now;instruction(false,false);
                event("request_accepted",Map.of("speaker",owner.getUUID().toString(),"text",text,"item",order.item,"count",order.count));
                tell(owner,"I will try to get you "+EnglishOrders.label(order.item,order.count)+", then bring the items back. I will confirm actual pickup.");
                if(actor.heldItems().getOrDefault(order.item,0)<order.count)startBridgeIfNeeded();
            }
            default -> { }
        }
    }
    private static void cancel(MinecraftServer server,ServerPlayer owner) {
        if(order!=null && order.busy()) { order.cancel(owner.getUUID());event("cancelled",Map.of("received",order.received())); }
        instruction(false,true);started=-1;movementOwner=null;actor.stopCompanion(server.getTickCount());
    }
    private static void fail(MinecraftServer server,String reason) {
        order.fail(reason);instruction(false,true);started=-1;movementOwner=null;actor.stopCompanion(server.getTickCount());
        event("failed",Map.of("reason",reason,"received",order.received()));
        ServerPlayer owner=server.getPlayerList().getPlayer(order.owner);
        if(owner!=null)tell(owner,"I could not finish: "+reason.replace('_',' ')+". Confirmed received "+order.received()+"/"+order.count+".");
    }
    private static boolean bridgeReady() {
        if(bridge==null || !bridge.isAlive() || bridgeLog==null)return false;
        try { return Files.readString(bridgeLog).contains("\"status\": \"ready\""); }catch(IOException error){return false;}
    }
    private static void startBridgeIfNeeded() {
        if(bridge!=null && bridge.isAlive())return;
        try {
            Path project=Path.of(configuration.getProperty("projectDirectory")).toAbsolutePath();
            Path python=Path.of(configuration.getProperty("pythonExecutable")).toAbsolutePath();
            Path checkpoint=Path.of(configuration.getProperty("checkpointFile")).toAbsolutePath();
            if(!Files.isRegularFile(python) || !Files.isRegularFile(checkpoint) || !Files.isRegularFile(project.resolve("minecraft_bridge.py")))throw new IOException("Companion runtime files unavailable");
            Path evidence=controlFile.resolveSibling("session_"+serial);Files.createDirectories(evidence);bridgeLog=evidence.resolve("bridge_launcher.log");
            var command=new ArrayList<>(List.of(python.toString(),"-u",project.resolve("minecraft_bridge.py").toString(),
                "--host","127.0.0.1","--port",configuration.getProperty("bridgePort","8875"),"--phase8-checkpoint",checkpoint.toString(),
                "--phase8-results",evidence.resolve("controller.jsonl").toString(),"--phase8-control",controlFile.toString(),"--log",evidence.resolve("bridge.jsonl").toString()));
            if(actor.pitchEnabled())command.add("--phase8-pitch-actions");if(actor.terrainEnabled())command.add("--terrain-actions");
            bridge=new ProcessBuilder(command).directory(project.toFile()).redirectErrorStream(true).redirectOutput(bridgeLog.toFile()).start();
        } catch(IOException error) { FlyCraftMod.LOGGER.warn("Companion brain unavailable",error); }
    }
    private static void instruction(boolean active,boolean complete) {
        var value=new JsonObject();value.addProperty("episode_id","companion_"+serial);value.addProperty("goal",goal);
        value.addProperty("condition","trained");value.addProperty("train",false);value.addProperty("policy_seed",91000+serial%1000000);
        value.addProperty("active",active);value.addProperty("suite_complete",complete);
        if(order!=null) { value.addProperty("companion_request",true);value.addProperty("requested_count",order.count); }
        try { Path temporary=controlFile.resolveSibling(controlFile.getFileName()+".tmp");Files.writeString(temporary,value.toString());AtomicFiles.replace(temporary,controlFile); }
        catch(IOException error){throw new IllegalStateException(error);}
    }
    private static void tick(MinecraftServer server) {
        if(!matches(server))return;
        if(actor==null) {
            if(server.getPlayerList().getPlayers().isEmpty())return;
            serial=System.currentTimeMillis();started=-1;instruction(false,true);actor=new HeadlessAgent();
            server.getPlayerList().broadcastSystemMessage(Component.literal("FlyCraft: address me in chat, e.g. FlyCraft, get me 3 logs. /flycraft say also accepts English requests."),false);
        }
        actor.tick(server);
        if(actor.ready() && server.getTickCount()%5==0) {
            processLocalRequest(server);
            if(order!=null && order.busy())manageOrder(server);
            else if(started>=0 && server.getTickCount()-started>=maxTicks) {
                instruction(false,true);started=-1;actor.stopCompanion(server.getTickCount());movementOwner=null;
            }
        }
    }
    private static void manageOrder(MinecraftServer server) {
        ServerPlayer owner=server.getPlayerList().getPlayer(order.owner);
        if(owner==null || !owner.isAlive() || owner.level()!=server.overworld()) { fail(server,"requester_unavailable");return; }
        if(!actor.alive()) { fail(server,"companion_died");return; }
        if(server.getTickCount()-order.createdTick>=maxTicks) { fail(server,"request_time_limit");return; }
        int held=actor.heldItems().getOrDefault(order.item,0);
        if(order.phase()==CompanionOrder.Phase.LOADING && held<order.count) {
            if(bridgeReady()) { order.collecting();actor.expectResource();instruction(true,false);event("collecting",Map.of()); }
            else if(bridge==null || !bridge.isAlive())fail(server,"brain_unavailable");
            return;
        }
        if(order.phase()==CompanionOrder.Phase.LOADING || order.phase()==CompanionOrder.Phase.COLLECTING) {
            boolean complete=order.phase()==CompanionOrder.Phase.LOADING || Set.of("success","already_complete").contains(actor.resourceStatus());
            if(held>=order.count && complete) {
                order.returning(held);instruction(false,true);actor.returnTo(server,owner);event("returning",Map.of("held",held));
            } else if(order.phase()==CompanionOrder.Phase.COLLECTING && !actor.resourceStatus().equals("running"))fail(server,"collection_"+actor.resourceStatus());
        }
        if(order.phase()==CompanionOrder.Phase.RETURNING && actor.canHandoff(owner)) {
            actor.stopCompanion(server.getTickCount());
            for(var parcel:actor.handoff(owner,order.item,order.count))order.parcel(parcel.entity(),parcel.count());
            if(order.phase()!=CompanionOrder.Phase.DELIVERING) { fail(server,"handoff_unavailable");return; }
            event("items_dropped",Map.of("count",order.count));tell(owner,"I dropped the items for you. Waiting for your actual pickup.");
        }
    }
    public static boolean tracksDelivery(UUID entity,UUID recipient) { return order!=null && order.tracks(entity,recipient); }
    public static void pickupObserved(UUID entity,Player recipient,int units,int before,int after) {
        if(order==null || !order.receipt(entity,recipient.getUUID(),units,before,after))return;
        event("pickup_confirmed",Map.of("entity",entity.toString(),"recipient",recipient.getUUID().toString(),"units",units,"inventory_before",before,"inventory_after",after));
        if(order.phase()==CompanionOrder.Phase.DELIVERED) {
            instruction(false,true);started=-1;movementOwner=null;event("delivered",Map.of("received",order.received()));
            if(recipient instanceof ServerPlayer owner)tell(owner,"Delivered "+EnglishOrders.label(order.item,order.received())+". Your actual pickup is confirmed.");
        }
    }
    private static void event(String type,Map<String,?> values) {
        var row=new LinkedHashMap<String,Object>();row.put("event",type);row.put("wall_time_unix_ms",System.currentTimeMillis());row.put("data",values);
        if(order!=null) { row.put("order_id",order.id.toString());row.put("owner",order.owner.toString());row.put("item",order.item);row.put("requested_count",order.count);row.put("phase",order.phase().name()); }
        try { Files.writeString(eventFile,JSON.toJson(row)+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND); }
        catch(IOException error) { FlyCraftMod.LOGGER.warn("Companion order log unavailable",error); }
    }
    private static void processLocalRequest(MinecraftServer server) {
        String configured=configuration.getProperty("commandFile","");if(configured.isEmpty())return;Path file=Path.of(configured);
        if(!Files.isRegularFile(file))return;
        try {
            var request=JsonParser.parseString(Files.readString(file)).getAsJsonObject();String id=request.get("request_id").getAsString();if(id.equals(lastRequest))return;lastRequest=id;
            var owner=server.getPlayerList().getPlayer(UUID.fromString(request.get("owner_uuid").getAsString()));if(owner==null)return;
            String command=request.get("command").getAsString();
            if(command.equals("say"))handleText(server,owner,request.get("text").getAsString(),true);
            else if(command.equals("follow") || command.equals("stop"))handleText(server,owner,command.equals("follow") ? "follow me" : "stop",true);
            else return;
            var result=JSON.toJsonTree(Map.of("request_id",id,"command",command,"alive",actor.alive(),"following",actor.following(),"server_tick",server.getTickCount()));
            Files.writeString(Path.of(file+".ack"),result.toString());Files.move(file,file.resolveSibling(file.getFileName()+".processed_"+System.currentTimeMillis()));
        } catch(Exception error){FlyCraftMod.LOGGER.warn("Companion operator request failed",error);}
    }
}

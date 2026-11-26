package org.flycraft.bridge;

import com.google.gson.Gson;
import com.mojang.authlib.GameProfile;
import io.netty.channel.embedded.EmbeddedChannel;
import io.netty.util.ReferenceCountUtil;
import java.nio.file.*;
import java.util.*;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.message.v1.ServerMessageEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.*;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.network.protocol.game.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.*;
import net.minecraft.server.network.CommonListenerCookie;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import org.flycraft.bridge.language.*;

/** Explicit disposable teaching fixture. Synthetic chat, real vanilla survival actions/pickup. */
final class EnglishOrderHarness {
    private static Properties config;
    private static FakePlayer owner,other;
    private static long start=-1,requested=-1,finishAt=-1;
    private static boolean placed,lessonSent,attemptedStop,ownershipProtected;
    private static UUID orderId;
    static void initialize(Properties properties) { config=properties;ServerTickEvents.END_SERVER_TICK.register(EnglishOrderHarness::tick); }
    private static final class FakePlayer extends ServerPlayer {
        final MinecraftServer server;final EmbeddedChannel channel;long last=-1;
        FakePlayer(MinecraftServer server,String name) {
            super(server,server.overworld(),new GameProfile(UUID.nameUUIDFromBytes(name.getBytes(java.nio.charset.StandardCharsets.UTF_8)),name),
                net.minecraft.server.level.ClientInformation.createDefault());
            this.server=server;var connection=new net.minecraft.network.Connection(PacketFlow.SERVERBOUND);channel=new EmbeddedChannel(connection);
            server.getPlayerList().placeNewPlayer(connection,this,CommonListenerCookie.createInitial(getGameProfile(),false));
            setGameMode(GameType.SURVIVAL);
            this.connection.handleAcceptPlayerLoad(new ServerboundPlayerLoadedPacket());
        }
        @Override public void tick() {
            if(server==null || last==server.getTickCount())return;last=server.getTickCount();
            super.tick();doTick();channel.runPendingTasks();Object packet;
            while((packet=channel.readOutbound())!=null) {
                if(packet instanceof ClientboundPlayerPositionPacket pos)connection.handleAcceptTeleportPacket(new ServerboundAcceptTeleportationPacket(pos.id()));
                ReferenceCountUtil.release(packet);
            }
        }
    }
    private static void chat(ServerPlayer player,String text) {
        player.level().getServer().getPlayerList().broadcastSystemMessage(Component.literal("[Disposable fixture; synthetic chat] "+player.getGameProfile().name()+": "+text),false);
        ServerMessageEvents.CHAT_MESSAGE.invoker().onChatMessage(PlayerChatMessage.unsigned(player.getUUID(),text),player,ChatType.bind(ChatType.CHAT,player));
    }
    private static void tick(MinecraftServer server) {
        try {
            if(finishAt>=0) { if(server.getTickCount()>=finishAt)server.halt(false);return; }
            if(start<0) { start=server.getTickCount();owner=new FakePlayer(server,"LangRequester");other=new FakePlayer(server,"LangBystander"); }
            owner.tick();other.tick();
            var actor=CompanionSession.testActor();if(actor==null || !actor.ready())return;
            if(!placed) {
                for(int x=-12;x<=12;x++)for(int z=-12;z<=12;z++) {
                    server.overworld().setBlockAndUpdate(new BlockPos(x,99,z),Blocks.STONE.defaultBlockState());
                    if(Math.abs(x)==12 || Math.abs(z)==12)for(int y=100;y<=104;y++)server.overworld().setBlockAndUpdate(new BlockPos(x,y,z),Blocks.STONE.defaultBlockState());
                }
                for(int y=100;y<103;y++)server.overworld().setBlockAndUpdate(new BlockPos(0,y,4),Blocks.OAK_LOG.defaultBlockState());
                owner.teleportTo(server.overworld(),.5,100,-1.5,Set.of(),0,0,true);
                other.teleportTo(server.overworld(),6.5,100,-3.5,Set.of(),0,0,true);
                actor.testPlayer().teleportTo(server.overworld(),.5,100,1.5,Set.of(),0,0,true);
                owner.setDeltaMovement(0,0,0);other.setDeltaMovement(0,0,0);actor.testPlayer().setDeltaMovement(0,0,0);
                if(HeadlessAgent.itemCount(owner,"log")!=0 || actor.heldItems().get("log")!=0)throw new IllegalStateException("Fixture inventories not empty");
                placed=true;start=server.getTickCount();
            }
            for(ServerPlayer observer:server.getPlayerList().getPlayers())if(observer!=owner && observer!=other && observer!=actor.testPlayer()) {
                observer.setGameMode(GameType.SPECTATOR);observer.setCamera(actor.testPlayer());
            }
            String gate=config.getProperty("fixture.startGate","");
            if(requested<0 && (gate.isEmpty() || Files.exists(Path.of(gate))) && server.getTickCount()-start>20) {
                String lesson=config.getProperty("fixture.lesson","");
                if(!lesson.isEmpty() && !lessonSent) { chat(owner,lesson);lessonSent=true;start=server.getTickCount();return; }
                chat(owner,config.getProperty("fixture.request","FlyCraft, get me one log"));requested=server.getTickCount();
            }
            CompanionOrder order=CompanionSession.testOrder();
            if(order!=null && orderId==null)orderId=order.id;
            if(order!=null && !attemptedStop && server.getTickCount()-requested>15) {
                chat(other,"FlyCraft, stop");attemptedStop=true;
            }
            if(attemptedStop && order!=null && order.busy() && order.id.equals(orderId) && order.owner.equals(owner.getUUID()))ownershipProtected=true;
            if(order!=null && !order.busy() || server.getTickCount()-start>3000) {
                boolean success=order!=null && order.phase()==CompanionOrder.Phase.DELIVERED && order.received()==order.count
                    && HeadlessAgent.itemCount(owner,order.item)>=order.count && actor.testBreaks()>0;
                var result=new LinkedHashMap<String,Object>();result.put("success",success);result.put("environment","controlled_companion_language_fixture");
                result.put("synthetic_chat_via_fabric_event",true);result.put("ownership_protected",ownershipProtected);result.put("confirmed_breaks",actor.testBreaks());
                var ownerInventory=new LinkedHashMap<String,Integer>();
                for(String item:List.of("log","planks","sticks","crafting_table","wooden_pickaxe"))ownerInventory.put(item,HeadlessAgent.itemCount(owner,item));
                result.put("owner_inventory",ownerInventory);result.put("actor_inventory",actor.heldItems());
                result.put("received",order==null ? 0 : order.received());result.put("requested_count",order==null ? 0 : order.count);
                result.put("phase",order==null ? "not_started" : order.phase().name());result.put("reason",order==null ? "" : order.reason());
                result.put("ticks",server.getTickCount()-requested);
                Files.writeString(Path.of(config.getProperty("fixture.result")),new Gson().toJson(result));
                server.getPlayerList().broadcastSystemMessage(Component.literal("[Fixture result] "+result.get("phase")+"; confirmed received "+result.get("received")+"/"+result.get("requested_count")+"; requester logs="+HeadlessAgent.itemCount(owner,"log")),false);
                finishAt=server.getTickCount()+60;
            }
        } catch(Exception error) { FlyCraftMod.LOGGER.error("English integration fixture failed",error);server.halt(false); }
    }
}

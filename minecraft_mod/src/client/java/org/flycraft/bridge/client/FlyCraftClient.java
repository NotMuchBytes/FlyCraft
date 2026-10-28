package org.flycraft.bridge.client;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;

import net.minecraft.client.Minecraft;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import org.flycraft.bridge.FlyCraftMod;
import org.flycraft.bridge.control.CameraDriver;

public final class FlyCraftClient implements ClientModInitializer {
    public static FlyCraftClient INSTANCE;
	private static final String BRIDGE_HOST = "127.0.0.1";
	private static final int BRIDGE_PORT = 8765;
	private static final int OBSERVATION_INTERVAL_TICKS = 10;
	private static final double RAY_DISTANCE = 12.0;
	private static final String[] SECTORS = {"far_left", "left", "center", "right", "far_right"};
	private static final double[] YAW_OFFSETS = {-40.0, -20.0, 0.0, 20.0, 40.0};

	private final AtomicBoolean requestPending = new AtomicBoolean(false);
	private final ExecutorService bridgeExecutor = Executors.newSingleThreadExecutor(runnable -> {
		Thread thread = new Thread(runnable, "flycraft-neural-bridge");
		thread.setDaemon(true);
		return thread;
	});
	private long clientTick;
	private long lastAppliedTick = -1;
	private long releaseForwardAt = -1;
	private String stoppedSession = "";
    private CameraDriver camera;
    private String cameraSession="";
    private double turnDegrees=15;

	@Override
	public void onInitializeClient() {
		if(java.nio.file.Files.exists(java.nio.file.Path.of("flycraft-spectator.properties"))) {
			new SpectatorClient().initialize(); return;
		}
		if (java.nio.file.Files.exists(java.nio.file.Path.of("flycraft-phase8-client.properties"))) {
			new Phase8Client().initialize();
			return;
		}
        INSTANCE=this;
        java.util.Properties cameraProperties=new java.util.Properties();
        cameraProperties.putAll(System.getProperties());
        java.nio.file.Path cameraFile=java.nio.file.Path.of("flycraft-camera.properties");
        if(java.nio.file.Files.exists(cameraFile)) try(var reader=java.nio.file.Files.newBufferedReader(cameraFile)) { cameraProperties.load(reader); }
        catch(java.io.IOException error) { throw new IllegalStateException(error); }
        camera=new CameraDriver(cameraProperties);
        turnDegrees=Double.parseDouble(cameraProperties.getProperty("camera.turnDegrees","15"));
        if(!Double.isFinite(turnDegrees) || turnDegrees<=0 || turnDegrees>45) throw new IllegalArgumentException("invalid turn step");
        Runtime.getRuntime().addShutdownHook(new Thread(camera::close,"flycraft-navigation-camera-close"));
		ClientTickEvents.END_CLIENT_TICK.register(this::onEndTick);
		FlyCraftMod.LOGGER.info("FlyCraft client bridge ready at {}:{}", BRIDGE_HOST, BRIDGE_PORT);
	}

	private void onEndTick(Minecraft client) {
		clientTick++;
        if(client.player==null || client.level==null) {
            client.options.keyUp.setDown(false); releaseForwardAt=-1;
            if(camera.busy()) camera.cancel("world_unavailable",true); return;
        }
        String nextCameraSession=client.player.getUUID().toString()+":"+System.identityHashCode(client.level);
        if(!nextCameraSession.equals(cameraSession)) { cameraSession=nextCameraSession; camera.reset(view(client),cameraSession); }
        camera.tick(view(client),clientTick);
		if (releaseForwardAt >= 0 && clientTick >= releaseForwardAt) {
			client.options.keyUp.setDown(false);
			releaseForwardAt = -1;
		}
		if (client.player == null || client.level == null || clientTick % OBSERVATION_INTERVAL_TICKS != 0) {
			return;
		}
        if(camera.busy()) return;
		String currentSession = client.player.getUUID().toString() + ":" + System.identityHashCode(client.level);
		if (currentSession.equals(stoppedSession)) return;
		if (!requestPending.compareAndSet(false, true)) {
			return;
		}
		long observationTick = clientTick;
		Observation observation = observeTargetSector(client);
		String sector = observation.sector();
		JsonObject request = new JsonObject();
		request.addProperty("tick_id", observationTick);
		request.addProperty("sector", sector);
		JsonObject telemetry = new JsonObject();
		telemetry.addProperty("session_id", client.player.getUUID().toString() + ":" + System.identityHashCode(client.level));
		com.google.gson.JsonArray position = new com.google.gson.JsonArray();
		position.add(client.player.getX());
		position.add(client.player.getZ());
		position.add(Math.toRadians(client.player.getYRot()));
		telemetry.add("position", position);
		telemetry.addProperty("target_distance", observation.distance());
		request.add("telemetry", telemetry);
		FlyCraftMod.LOGGER.info("FLYCRAFT observation tick={} sector={}", observationTick, sector);
		bridgeExecutor.execute(() -> exchangeWithBridge(client, observationTick, sector, request));
	}

	private record Observation(String sector, double distance) { }

	private Observation observeTargetSector(Minecraft client) {
		Vec3 start = client.player.getEyePosition();
		for (int i = 0; i < SECTORS.length; i++) {
			double yaw = Math.toRadians(client.player.getYRot() + YAW_OFFSETS[i]);
			double pitch = Math.toRadians(client.player.getXRot());
			Vec3 direction = new Vec3(-Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
			Vec3 end = start.add(direction.scale(RAY_DISTANCE));
			BlockHitResult hit = client.level.clip(new ClipContext(start, end, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, client.player));
			if (hit.getType() == HitResult.Type.BLOCK && client.level.getBlockState(hit.getBlockPos()).is(Blocks.GOLD_BLOCK)) {
				return new Observation(SECTORS[i], start.distanceTo(hit.getLocation()));
			}
		}
		return new Observation("not_visible", -1.0);
	}

	private void exchangeWithBridge(Minecraft client, long observationTick, String sector, JsonObject request) {
        long observationNanos=System.nanoTime();
		try (Socket socket = new Socket()) {
			socket.connect(new InetSocketAddress(BRIDGE_HOST, BRIDGE_PORT), 1500);
			socket.setSoTimeout(15_000);
			try (BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8));
					BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8))) {
				writer.write(request.toString());
				writer.newLine();
				writer.flush();
				JsonObject response = JsonParser.parseString(reader.readLine()).getAsJsonObject();
				if (!"ok".equals(response.get("status").getAsString())) {
					throw new IllegalStateException(response.toString());
				}
				long responseTick = response.get("tick_id").getAsLong();
				String action = response.get("action").getAsString();
				double latency = response.get("latency_ms").getAsDouble();
				String sessionId = request.getAsJsonObject("telemetry").get("session_id").getAsString();
				client.execute(() -> {
					String currentSession = client.player == null || client.level == null ? "" : client.player.getUUID().toString() + ":" + System.identityHashCode(client.level);
					if (sessionId.equals(currentSession)) {
						applyAction(client, observationTick, responseTick, sector, action, latency,observationNanos);
						if (response.has("autonomy_status") && !"running".equals(response.get("autonomy_status").getAsString())) {
							stoppedSession = sessionId;
						}
					}
				});
			}
		} catch (Exception error) {
			FlyCraftMod.LOGGER.error("FLYCRAFT bridge request failed tick={}", observationTick, error);
		} finally {
			requestPending.set(false);
		}
	}

	private void applyAction(Minecraft client, long observationTick, long responseTick, String sector, String action, double latency,long observationNanos) {
		if (client.player == null || responseTick != observationTick || responseTick <= lastAppliedTick || clientTick - observationTick > 40) {
			FlyCraftMod.LOGGER.warn("FLYCRAFT stale action ignored observation_tick={} response_tick={} last_applied={}", observationTick, responseTick, lastAppliedTick);
			return;
		}
		lastAppliedTick = responseTick;
		client.options.keyUp.setDown(false);
		releaseForwardAt = -1;
		switch (action) {
			case "TURN_LEFT", "TURN_RIGHT" -> {
                var accepted=camera.relative(view(client),responseTick,action.equals("TURN_LEFT") ? -turnDegrees : turnDegrees,0,
                    observationTick,clientTick,observationNanos);
                if(!accepted.accepted()) FlyCraftMod.LOGGER.warn("FLYCRAFT camera command rejected tick={} reason={}",responseTick,accepted.reason());
            }
			case "FORWARD" -> {
				client.options.keyUp.setDown(true);
				releaseForwardAt = clientTick + 5;
			}
			case "NO_OP" -> { }
			default -> throw new IllegalArgumentException("Unknown action: " + action);
		}
		FlyCraftMod.LOGGER.info("FLYCRAFT action_applied tick={} sector={} action={} latency_ms={}", responseTick, sector, action, latency);
	}
    private CameraDriver.View view(Minecraft client) {
        return new CameraDriver.View() {
            public double yaw() { return client.player.getYRot(); }
            public double pitch() { return client.player.getXRot(); }
            public void set(double yaw,double pitch) { client.player.setYRot((float)yaw); client.player.setXRot((float)pitch); }
        };
    }
    public void renderedCamera(double yaw,double pitch) { if(camera!=null) camera.rendered(yaw,pitch); }
}

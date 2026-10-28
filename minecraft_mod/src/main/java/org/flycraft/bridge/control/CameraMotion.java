package org.flycraft.bridge.control;

import java.util.Properties;

/** Generic angular actuator. It never receives a block, entity or visual target. */
public final class CameraMotion {
    public enum Mode { RELATIVE, CONTINUOUS }
    public record Limits(double velocity, double acceleration, double deceleration) {
        public Limits {
            if (!positive(velocity) || !positive(acceleration) || !positive(deceleration)
                    || velocity > 720 || acceleration > 100000 || deceleration > 100000)
                throw new IllegalArgumentException("camera limits must be finite and positive");
        }
    }
    public record Config(Limits yaw, Limits pitch, double tolerance, int maxAgeTicks,
                         int relativeTimeoutTicks, int velocityTtlTicks, double maxStepSeconds) {
        public Config {
            if (yaw == null || pitch == null || !positive(tolerance) || tolerance > 1
                    || maxAgeTicks < 1 || maxAgeTicks > 100 || relativeTimeoutTicks < 1 || relativeTimeoutTicks > 400
                    || velocityTtlTicks < 1 || velocityTtlTicks > 100
                    || !positive(maxStepSeconds) || maxStepSeconds > .05)
                throw new IllegalArgumentException("invalid camera configuration");
        }
        public static Config defaults() {
            return new Config(new Limits(120, 720, 1080), new Limits(90, 540, 810), .02, 8, 100, 5, .05);
        }
        public static Config from(Properties properties) {
            Config d = defaults();
            return new Config(new Limits(value(properties,"camera.maxYawVelocity",d.yaw.velocity),
                    value(properties,"camera.yawAcceleration",d.yaw.acceleration), value(properties,"camera.yawDeceleration",d.yaw.deceleration)),
                    new Limits(value(properties,"camera.maxPitchVelocity",d.pitch.velocity),
                    value(properties,"camera.pitchAcceleration",d.pitch.acceleration), value(properties,"camera.pitchDeceleration",d.pitch.deceleration)),
                    value(properties,"camera.toleranceDegrees",d.tolerance),
                    (int)value(properties,"camera.maxCommandAgeTicks",d.maxAgeTicks),
                    (int)value(properties,"camera.relativeTimeoutTicks",d.relativeTimeoutTicks),
                    (int)value(properties,"camera.continuousTtlTicks",d.velocityTtlTicks), .05);
        }
    }
    /** RELATIVE: signed degrees, yaw at most180. CONTINUOUS: degrees/second. */
    public record Request(long id, Mode mode, double yaw, double pitch, long issuedTick, int ttlTicks) { }
    public record Acceptance(boolean accepted, String reason) { }
    public record Frame(long commandId, String mode, double observedYaw, double observedPitch,
                        double outputYaw, double outputPitch, double requestedYaw, double requestedPitch,
                        double actualYawMovement, double actualPitchMovement, double yawVelocity, double pitchVelocity,
                        Double targetYaw, Double targetPitch, Double yawError, Double pitchError, Double yawOvershoot, Double pitchOvershoot,
                        long elapsedTicks, boolean active, boolean settled, String result) { }

    private final Config config;
    private Request request;
    private long lastId, startedTick, expiresTick, overrideUntil;
    private boolean initialized, active, braking, expectedValid;
    private double lastRawYaw, unwrappedYaw, expectedYaw, expectedPitch;
    private double startYaw, startPitch, targetYaw, targetPitch, yawVelocity, pitchVelocity;
    private double yawOvershoot, pitchOvershoot;
    private String result = "idle";

    public CameraMotion(Config config) { this.config = config; }
    public Config config() { return config; }
    public boolean active() { return active; }
    public String result() { return result; }
    public long commandId() { return request == null ? 0 : request.id; }

    public Acceptance submit(Request next, double yaw, double pitch, long tick) {
        checkPose(yaw, pitch);
        synchronizeYaw(yaw);
        if (next == null || next.mode == null || next.id <= 0 || !Double.isFinite(next.yaw) || !Double.isFinite(next.pitch))
            return new Acceptance(false,"invalid_command");
        if (tick < overrideUntil) return new Acceptance(false,"manual_override_cooldown");
        if (tick < next.issuedTick || tick - next.issuedTick > config.maxAgeTicks)
            return new Acceptance(false,"stale_command");
        if (next.id < lastId || next.id == lastId && !(active && !braking && request.mode == Mode.CONTINUOUS && next.mode == Mode.CONTINUOUS))
            return new Acceptance(false,"duplicate_or_old_command");
        if (next.mode == Mode.RELATIVE && Math.abs(next.yaw) > 180)
            return new Acceptance(false,"relative_yaw_out_of_range");
        if (active && expectedValid && (Math.abs(wrap(yaw-expectedYaw)) > .35 || Math.abs(pitch-expectedPitch) > .35)) {
            cancel("external_pose_change",true); overrideUntil = tick + 10;
            return new Acceptance(false,"external_pose_change");
        }
        if (next.mode == Mode.RELATIVE && (unsafeRetarget(next.yaw,yawVelocity,config.yaw)
                || unsafeRetarget(clamp(pitch+next.pitch,-90,90)-pitch,pitchVelocity,config.pitch))) {
            lastId = next.id; cancel("braking_before_retarget",false);
            return new Acceptance(false,"target_inside_braking_distance");
        }
        boolean renewal = next.id == lastId;
        request = next; lastId = next.id;
        if (!renewal) {
            startedTick = tick; startYaw = unwrappedYaw; startPitch = pitch;
            yawOvershoot = pitchOvershoot = 0;
        }
        targetYaw = unwrappedYaw + next.yaw;
        targetPitch = clamp(pitch + next.pitch,-90,90);
        int ttl = next.ttlTicks > 0 ? next.ttlTicks : config.velocityTtlTicks;
        expiresTick = tick + Math.min(ttl,config.velocityTtlTicks);
        active = true; braking = false; result = renewal ? "renewed" : "moving";
        expectedYaw = yaw; expectedPitch = pitch; expectedValid = true;
        return new Acceptance(true,result);
    }

    public void cancel(String reason, boolean immediate) {
        result = reason;
        if (immediate || Math.abs(yawVelocity)+Math.abs(pitchVelocity) < 1e-9) {
            active = false; braking = false; yawVelocity = pitchVelocity = 0; expectedValid = false;
        } else { braking = true; active = true; }
    }

    /** Reset only at an explicit episode/world boundary, never to track a target. */
    public void reset(double yaw, double pitch) {
        checkPose(yaw,pitch); cancel("world_reset",true);
        initialized = true; lastRawYaw = unwrappedYaw = yaw; expectedYaw = yaw; expectedPitch = pitch;
        overrideUntil = 0; lastId = 0; request = null;
        startYaw = targetYaw = yaw; startPitch = targetPitch = pitch; yawOvershoot = pitchOvershoot = 0;
    }

    public Frame tick(double yaw, double pitch, long tick, double elapsedSeconds) {
        checkPose(yaw,pitch);
        if (!Double.isFinite(elapsedSeconds) || elapsedSeconds < 0) throw new IllegalArgumentException("invalid camera dt");
        if (active && expectedValid && (Math.abs(wrap(yaw-expectedYaw)) > .35 || Math.abs(pitch-expectedPitch) > .35)) {
            synchronizeYaw(yaw); cancel("external_pose_change",true); overrideUntil = tick + 10;
            return frame(yaw,pitch,yaw,pitch,tick);
        }
        synchronizeYaw(yaw);
        if (!active) return frame(yaw,pitch,yaw,pitch,tick);
        double dt = Math.min(elapsedSeconds,config.maxStepSeconds);
        if (tick-startedTick > Math.max(200,config.relativeTimeoutTicks+20)) {
            cancel("hard_timeout",true); return frame(yaw,pitch,yaw,pitch,tick);
        }
        if (!braking && (request.mode == Mode.RELATIVE && tick-startedTick >= config.relativeTimeoutTicks
                || request.mode == Mode.CONTINUOUS && tick >= expiresTick)) cancel("command_timeout",false);
        if (!active || dt == 0) return frame(yaw,pitch,yaw,pitch,tick);
        double yawError = targetYaw-unwrappedYaw, pitchError = targetPitch-pitch;
        if (!braking && request.mode == Mode.RELATIVE) {
            yawOvershoot = Math.max(yawOvershoot,Math.max(0,-Math.signum(request.yaw)*yawError));
            pitchOvershoot = Math.max(pitchOvershoot,Math.max(0,-Math.signum(targetPitch-startPitch)*pitchError));
        }
        double desiredYaw = 0, desiredPitch = 0;
        if (!braking) {
            if (request.mode == Mode.RELATIVE) {
                desiredYaw = stoppingVelocity(yawError,config.yaw,dt);
                desiredPitch = stoppingVelocity(pitchError,config.pitch,dt);
            } else {
                desiredYaw = clamp(request.yaw,-config.yaw.velocity,config.yaw.velocity);
                desiredPitch = clamp(request.pitch,-config.pitch.velocity,config.pitch.velocity);
                double boundary = desiredPitch >= 0 ? 90-pitch : -90-pitch;
                desiredPitch = Math.copySign(Math.min(Math.abs(desiredPitch),Math.abs(stoppingVelocity(boundary,config.pitch,dt))),desiredPitch);
            }
        }
        yawVelocity = accelerate(yawVelocity,desiredYaw,config.yaw,dt);
        pitchVelocity = accelerate(pitchVelocity,desiredPitch,config.pitch,dt);
        double yawStep = yawVelocity*dt, pitchStep = pitchVelocity*dt;
        if (!braking && request.mode == Mode.RELATIVE) {
            if (Math.signum(yawStep) == Math.signum(yawError) && Math.abs(yawStep) > Math.abs(yawError)) yawStep = yawError;
            if (Math.signum(pitchStep) == Math.signum(pitchError) && Math.abs(pitchStep) > Math.abs(pitchError)) pitchStep = pitchError;
        }
        double outputYaw = yaw+yawStep, outputPitch = clamp(pitch+pitchStep,-90,90);
        yawVelocity = yawStep/elapsedSeconds; pitchVelocity = (outputPitch-pitch)/elapsedSeconds;
        if (Math.abs(yawVelocity)+Math.abs(pitchVelocity) < 1e-7 && (braking
                || request.mode == Mode.RELATIVE && Math.abs(yawError) <= config.tolerance && Math.abs(pitchError) <= config.tolerance)) {
            active = false;
            if (!braking) result = "settled";
            braking = false; expectedValid = false;
        } else { expectedYaw = outputYaw; expectedPitch = outputPitch; expectedValid = true; }
        return frame(yaw,pitch,outputYaw,outputPitch,tick);
    }

    private Frame frame(double yaw,double pitch,double outputYaw,double outputPitch,long tick) {
        boolean endpoint = request != null && request.mode == Mode.RELATIVE;
        return new Frame(commandId(),request == null ? "none" : request.mode.name(),yaw,pitch,outputYaw,outputPitch,
                request == null ? 0 : request.yaw,request == null ? 0 : request.pitch,
                request == null ? 0 : unwrappedYaw-startYaw,request == null ? 0 : pitch-startPitch,yawVelocity,pitchVelocity,
                endpoint ? targetYaw : null,endpoint ? targetPitch : null,
                endpoint ? targetYaw-unwrappedYaw : null,endpoint ? targetPitch-pitch : null,
                endpoint ? yawOvershoot : null,endpoint ? pitchOvershoot : null,
                request == null ? 0 : tick-startedTick,active,result.equals("settled"),result);
    }
    private void synchronizeYaw(double yaw) {
        if (!initialized) { initialized = true; unwrappedYaw = yaw; }
        else unwrappedYaw += wrap(yaw-lastRawYaw);
        lastRawYaw = yaw;
    }
    private boolean unsafeRetarget(double delta,double velocity,Limits limits) {
        if (!active || braking || Math.abs(velocity) < 1e-7) return false;
        if (Math.abs(delta) <= config.tolerance) return true;
        return Math.signum(delta) == Math.signum(velocity) && Math.abs(delta) <
                velocity*velocity/(2*limits.deceleration)+Math.abs(velocity)*config.maxStepSeconds;
    }
    private static double stoppingVelocity(double error,Limits limits,double dt) {
        double brake = limits.deceleration*dt;
        return Math.copySign(Math.min(limits.velocity,Math.sqrt(brake*brake+2*limits.deceleration*Math.abs(error))-brake),error);
    }
    private static double accelerate(double current,double desired,Limits limits,double dt) {
        if (current*desired < 0) return approach(current,0,limits.deceleration*dt);
        return approach(current,desired,(Math.abs(desired) > Math.abs(current) ? limits.acceleration : limits.deceleration)*dt);
    }
    private static double approach(double current,double target,double amount) {
        return current + clamp(target-current,-amount,amount);
    }
    public static double wrap(double degrees) { return degrees-360*Math.floor((degrees+180)/360); }
    private static double clamp(double value,double low,double high) { return Math.max(low,Math.min(high,value)); }
    private static boolean positive(double value) { return Double.isFinite(value) && value > 0; }
    private static double value(Properties p,String key,double fallback) { return Double.parseDouble(p.getProperty(key,Double.toString(fallback))); }
    private static void checkPose(double yaw,double pitch) {
        if (!Double.isFinite(yaw) || !Double.isFinite(pitch) || pitch < -90 || pitch > 90) throw new IllegalArgumentException("invalid camera pose");
    }
}

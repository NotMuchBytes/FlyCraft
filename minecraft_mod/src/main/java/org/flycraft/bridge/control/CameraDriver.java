package org.flycraft.bridge.control;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Player/spectator independent adapter; only explicit angle commands can move a view. */
public final class CameraDriver implements AutoCloseable {
    public interface View {
        double yaw();
        double pitch();
        void set(double yaw,double pitch);
    }
    public enum Mode { INSTANT_REFERENCE, BOUNDED }
    private final Mode mode;
    private final CameraMotion motion;
    private final Gson json = new GsonBuilder().serializeNulls().create();
    private BufferedWriter trace;
    private long lastNanos, commandNanos;
    private long renderUntilNanos;
    private double previousYaw, previousPitch, previousRateYaw, previousRatePitch;
    private boolean sampled, awaitingCompletion;
    private double peakYaw, peakPitch, peakAccelerationYaw, peakAccelerationPitch;
    private long requests, rejected, completed;
    private String episode = "", completion = "idle";
    private String traceError="";
    private CameraMotion.Frame lastFrame;

    public CameraDriver(Properties properties) {
        String selected = properties.getProperty("camera.mode","bounded");
        mode = switch(selected) {
            case "bounded" -> Mode.BOUNDED;
            case "instant" -> Mode.INSTANT_REFERENCE;
            default -> throw new IllegalArgumentException("camera.mode must be bounded or instant");
        };
        motion = new CameraMotion(CameraMotion.Config.from(properties));
        String path = properties.getProperty("camera.traceFile","");
        if (!path.isEmpty()) {
            try {
                Path target=Path.of(path); Files.createDirectories(target.toAbsolutePath().getParent());
                trace=Files.newBufferedWriter(target,StandardOpenOption.CREATE_NEW);
            } catch(IOException error) { throw new IllegalStateException("camera trace unavailable",error); }
        }
        event("configuration",Map.of("mode",mode.name(),"limits",motion.config(),"units","degrees, degrees/second, degrees/second^2"));
    }
    public CameraMotion motion() { return motion; }
    public CameraMotion.Frame lastFrame() { return lastFrame; }
    public boolean busy() { return motion.active() || awaitingCompletion; }
    public String completion() { return completion; }
    public Mode mode() { return mode; }

    public void reset(View view,String nextEpisode) {
        motion.reset(view.yaw(),view.pitch()); episode=nextEpisode; sampled=false; awaitingCompletion=false;
        lastNanos=System.nanoTime(); completion="world_reset"; lastFrame=null;
        renderUntilNanos=0;
        previousRateYaw=previousRatePitch=0;
        event("fixture_or_world_reset",Map.of("yaw",view.yaw(),"pitch",view.pitch()));
    }
    public CameraMotion.Acceptance relative(View view,long id,double yaw,double pitch,long observationTick,long tick,long observationNanos) {
        return submit(view,new CameraMotion.Request(id,CameraMotion.Mode.RELATIVE,yaw,pitch,observationTick,0),tick,observationNanos);
    }
    public CameraMotion.Acceptance velocity(View view,long id,double yaw,double pitch,long tick,int ttl) {
        return submit(view,new CameraMotion.Request(id,CameraMotion.Mode.CONTINUOUS,yaw,pitch,tick,ttl),tick,System.nanoTime());
    }
    private CameraMotion.Acceptance submit(View view,CameraMotion.Request request,long tick,long observationNanos) {
        requests++;
        long previousId=motion.commandId();
        boolean replacing=awaitingCompletion && previousId!=request.id();
        double ageMs=(System.nanoTime()-observationNanos)/1e6;
        CameraMotion.Acceptance accepted;
        if (ageMs > motion.config().maxAgeTicks()*50.0) accepted=new CameraMotion.Acceptance(false,"stale_wall_time");
        else if (mode==Mode.INSTANT_REFERENCE && request.mode()==CameraMotion.Mode.CONTINUOUS)
            accepted=new CameraMotion.Acceptance(false,"continuous_not_in_original_reference");
        else accepted=motion.submit(request,view.yaw(),view.pitch(),tick);
        event("request",Map.of("request",request,"tick",tick,"observation_age_ms",ageMs,"acceptance",accepted));
        if (!accepted.accepted()) { rejected++; return accepted; }
        if (replacing) event("command_replaced",Map.of("previous_id",previousId,"new_id",request.id(),
                "previous_elapsed_seconds",(System.nanoTime()-commandNanos)/1e9));
        if (previousId==request.id() && awaitingCompletion) return accepted;
        peakYaw=peakPitch=peakAccelerationYaw=peakAccelerationPitch=0;
        if (!sampled) { previousYaw=view.yaw(); previousPitch=view.pitch(); sampled=true; }
        commandNanos=System.nanoTime(); awaitingCompletion=true; completion="moving";
        if (mode==Mode.INSTANT_REFERENCE) {
            view.set(view.yaw()+request.yaw(),Math.max(-90,Math.min(90,view.pitch()+request.pitch())));
            motion.cancel("instant_reference",true);
        }
        return accepted;
    }
    public void cancel(String reason,boolean immediate) {
        motion.cancel(reason,immediate); completion=reason;
        if (immediate) awaitingCompletion=false;
        event("cancel",Map.of("reason",reason,"immediate",immediate));
    }
    public CameraMotion.Frame tick(View view,long tick) {
        long now=System.nanoTime();
        double elapsed=lastNanos==0 ? .05 : Math.max(0,(now-lastNanos)/1e9); lastNanos=now;
        CameraMotion.Frame frame=motion.tick(view.yaw(),view.pitch(),tick,elapsed);
        if (Math.abs(frame.outputYaw()-view.yaw())>1e-10 || Math.abs(frame.outputPitch()-view.pitch())>1e-10)
            view.set(frame.outputYaw(),frame.outputPitch());
        double rateYaw=0,ratePitch=0,accelerationYaw=0,accelerationPitch=0;
        if (sampled && elapsed>1e-6) {
            rateYaw=CameraMotion.wrap(view.yaw()-previousYaw)/elapsed; ratePitch=(view.pitch()-previousPitch)/elapsed;
            accelerationYaw=(rateYaw-previousRateYaw)/elapsed; accelerationPitch=(ratePitch-previousRatePitch)/elapsed;
        }
        sampled=true; previousYaw=view.yaw(); previousPitch=view.pitch(); previousRateYaw=rateYaw; previousRatePitch=ratePitch;
        if (awaitingCompletion) {
            peakYaw=Math.max(peakYaw,Math.abs(rateYaw)); peakPitch=Math.max(peakPitch,Math.abs(ratePitch));
            peakAccelerationYaw=Math.max(peakAccelerationYaw,Math.abs(accelerationYaw)); peakAccelerationPitch=Math.max(peakAccelerationPitch,Math.abs(accelerationPitch));
            Map<String,Object> sample=new LinkedHashMap<>();
            sample.put("tick",tick); sample.put("frame",frame); sample.put("actual_yaw",view.yaw()); sample.put("actual_pitch",view.pitch());
            sample.put("wall_dt_seconds",elapsed); sample.put("effective_dt_seconds",Math.min(elapsed,motion.config().maxStepSeconds()));
            sample.put("observed_yaw_velocity",rateYaw); sample.put("observed_pitch_velocity",ratePitch);
            sample.put("observed_yaw_acceleration",accelerationYaw); sample.put("observed_pitch_acceleration",accelerationPitch);
            event("frame",sample);
            if (!motion.active() && Math.abs(rateYaw)<.4 && Math.abs(ratePitch)<.4) {
                completion=mode==Mode.INSTANT_REFERENCE ? "settled" : motion.result(); awaitingCompletion=false; completed++;
                renderUntilNanos=now+250_000_000L;
                Map<String,Object> summary=new LinkedHashMap<>();
                summary.put("command_id",frame.commandId()); summary.put("result",completion); summary.put("ticks",frame.elapsedTicks());
                summary.put("wall_seconds",(now-commandNanos)/1e9); summary.put("peak_yaw_velocity",peakYaw); summary.put("peak_pitch_velocity",peakPitch);
                summary.put("peak_yaw_acceleration",peakAccelerationYaw); summary.put("peak_pitch_acceleration",peakAccelerationPitch);
                summary.put("final_frame",frame); event("command_complete",summary);
            }
        }
        lastFrame=frame; return frame;
    }
    private void event(String type,Map<String,?> data) {
        if (trace==null) return;
        try {
            trace.write(json.toJson(Map.of("event",type,"episode_id",episode,"nano_time",System.nanoTime(),"wall_time_unix_ms",System.currentTimeMillis(),"mode",mode.name(),"data",data)));
            trace.newLine();
            if (!type.equals("frame")) trace.flush();
        } catch(IOException error) {
            traceError=error.toString();
            try { trace.close(); } catch(IOException ignored) { }
            trace=null;
        }
    }
    public void rendered(double yaw,double pitch) {
        if(awaitingCompletion || System.nanoTime()<renderUntilNanos)
            event("render_frame",Map.of("command_id",motion.commandId(),"actual_camera_yaw",yaw,"actual_camera_pitch",pitch));
    }
    public Map<String,Object> counters() { return Map.of("requests",requests,"rejected",rejected,"completed",completed,"trace_error",traceError); }
    @Override public void close() {
        motion.cancel("driver_closed",true);
        if (trace!=null) try { trace.close(); } catch(IOException error) { throw new IllegalStateException(error); }
    }
}

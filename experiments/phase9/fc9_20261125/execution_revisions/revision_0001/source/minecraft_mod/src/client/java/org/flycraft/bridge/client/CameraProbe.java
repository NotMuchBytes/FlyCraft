package org.flycraft.bridge.client;

import com.google.gson.Gson;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.flycraft.bridge.control.CameraDriver;

/** Scripted actuator tests only; never presented as learned gameplay. */
public final class CameraProbe implements AutoCloseable {
    private record Case(String name,double yaw,double pitch,double deltaYaw,double deltaPitch,int special) { }
    private final List<Case> cases=List.of(
        new Case("small_yaw",0,0,1,0,0),new Case("small_negative_yaw",0,0,-1,0,0),
        new Case("medium_yaw",0,0,15,0,0),new Case("medium_negative_yaw",0,0,-15,0,0),
        new Case("large_yaw",0,0,90,0,0),new Case("wrap_180",179,0,180,0,0),
        new Case("pitch_upper_clamp",0,89,0,20,0),new Case("pitch_lower_clamp",0,-89,0,-20,0),
        new Case("rapid_reversal",0,0,90,0,1),new Case("interruption",0,0,90,0,2),
        new Case("duplicate_and_stale",0,0,15,0,3),new Case("continuous_ttl",0,0,60,20,4));
    private final CameraDriver driver;
    private final BufferedWriter output;
    private final Gson json=new Gson();
    private int index=-1;
    private long began,ready,id;
    private boolean specialDone,finished;
    private int passed,failed,skipped;
    private double expectedYaw,expectedPitch;
    private boolean negativeChecks=true;
    private final Path resultPath;
    public CameraProbe(CameraDriver driver,Path path) {
        this.driver=driver;
        resultPath=Path.of(path.toString()+".complete.json");
        try { output=Files.newBufferedWriter(path,StandardOpenOption.CREATE_NEW); }
        catch(IOException error) { throw new IllegalStateException(error); }
    }
    public boolean finished() { return finished; }
    public void tick(CameraDriver.View view,long tick) {
        if (finished || tick<ready) return;
        if(index<0) { start(view,tick); return; }
        Case test=cases.get(index);
        if(test.special==1 && !specialDone && tick-began>=4) {
            expectedYaw=view.yaw()-30;
            driver.relative(view,++id,-30,0,tick,tick,System.nanoTime()); specialDone=true;
        } else if(test.special==2 && !specialDone && tick-began>=4) {
            driver.cancel("probe_interruption",false); specialDone=true;
        } else if(test.special==4 && !specialDone && tick-began>=3) {
            driver.velocity(view,id,60,20,tick,5); specialDone=true;
        }
        boolean needsSpecial=test.special==1 || test.special==2 || test.special==4;
        if (!driver.busy() && (!needsSpecial || specialDone)) {
            String expectedResult=test.special==2 ? "probe_interruption" : test.special==4 ? "command_timeout" : "settled";
            boolean success=driver.completion().equals(expectedResult) && negativeChecks;
            if(test.special!=2 && test.special!=4) success &= Math.abs(org.flycraft.bridge.control.CameraMotion.wrap(expectedYaw-view.yaw()))<.03
                    && Math.abs(expectedPitch-view.pitch())<.03;
            if(success) passed++; else failed++;
            write("case_complete",Map.of("case",test.name,"mode",driver.mode().name(),"ticks",tick-began,
                "actual_yaw",view.yaw(),"actual_pitch",view.pitch(),"result",driver.completion(),"success",success));
            ready=tick+5; startNext=true;
        } else if(tick-began>140) {
            write("case_failed",Map.of("case",test.name,"reason","probe_timeout"));
            failed++;
            driver.cancel("probe_timeout",true); ready=tick+5; startNext=true;
        }
    }
    private boolean startNext;
    public void beforeTick(CameraDriver.View view,long tick) {
        if(startNext && tick>=ready) { startNext=false; start(view,tick); }
    }
    private void start(CameraDriver.View view,long tick) {
        index++;
        if(index>=cases.size()) {
            finished=true;
            Map<String,Object> summary=Map.of("cases",cases.size(),"passed",passed,"failed",failed,"skipped",skipped,
                "success",failed==0,"counters",driver.counters(),"kind","scripted_motor_test_not_policy");
            write("probe_complete",summary);
            try { Files.writeString(resultPath,json.toJson(summary),StandardOpenOption.CREATE_NEW); }
            catch(IOException error) { throw new IllegalStateException(error); }
            return;
        }
        Case test=cases.get(index); began=tick; specialDone=false;
        net.minecraft.client.Minecraft.getInstance().gui.hud.setOverlayMessage(net.minecraft.network.chat.Component.literal(
            "Scripted motor test: "+test.name+" / "+driver.mode().name()),true);
        expectedYaw=test.yaw+test.deltaYaw; expectedPitch=Math.max(-90,Math.min(90,test.pitch+test.deltaPitch)); negativeChecks=true;
        view.set(test.yaw,test.pitch); driver.reset(view,"camera_probe:"+test.name);
        // Reset interpolation history only for a controlled test's starting pose.
        net.minecraft.client.Minecraft.getInstance().player.yRotO=(float)test.yaw;
        net.minecraft.client.Minecraft.getInstance().player.xRotO=(float)test.pitch;
        write("case_start",Map.of("case",test.name,"tick",tick,"initial_yaw",view.yaw(),"initial_pitch",view.pitch(),"kind","scripted_motor_test_not_policy"));
        if(test.special==4 && driver.mode()==CameraDriver.Mode.INSTANT_REFERENCE) {
            write("case_skipped",Map.of("case",test.name,"reason","original_instant_reference_has_no_continuous_interface"));
            skipped++;
            ready=tick+5; startNext=true; return;
        }
        if(test.special==4) driver.velocity(view,++id,60,20,tick,5);
        else {
            driver.relative(view,++id,test.deltaYaw,test.deltaPitch,tick,tick,System.nanoTime());
            if(test.special==3) {
                boolean duplicate=driver.relative(view,id,15,0,tick,tick,System.nanoTime()).accepted();
                boolean stale=driver.relative(view,id+1000,15,0,tick-100,tick,System.nanoTime()).accepted();
                negativeChecks=!duplicate && !stale;
                write("duplicate_result",Map.of("accepted",duplicate));
                write("stale_result",Map.of("accepted",stale));
            }
        }
    }
    private void write(String event,Map<String,?> data) {
        try { output.write(json.toJson(Map.of("event",event,"wall_time_unix_ms",System.currentTimeMillis(),"data",data))); output.newLine(); output.flush(); }
        catch(IOException error) { throw new IllegalStateException(error); }
    }
    @Override public void close() { try { output.close(); } catch(IOException error) { throw new IllegalStateException(error); } }
}

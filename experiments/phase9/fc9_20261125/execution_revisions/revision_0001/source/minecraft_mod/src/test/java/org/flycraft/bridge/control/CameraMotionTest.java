package org.flycraft.bridge.control;

import java.util.Random;

/** Dependency-free kinematic tests, launched by Python's normal test suite. */
public final class CameraMotionTest {
    private static int cases;
    private static double peakYaw, peakPitch, peakYawAcceleration, peakOvershoot;
    private static final CameraMotion.Config CONFIG = CameraMotion.Config.defaults();
    private static void check(boolean value,String message) { if (!value) throw new AssertionError(message); }
    private static CameraMotion.Request relative(long id,double yaw,double pitch,long tick) {
        return new CameraMotion.Request(id,CameraMotion.Mode.RELATIVE,yaw,pitch,tick,0);
    }
    private static void turn(double initialYaw,double initialPitch,double deltaYaw,double deltaPitch) {
        CameraMotion motor = new CameraMotion(CONFIG);
        check(motor.submit(relative(1,deltaYaw,deltaPitch,0),initialYaw,initialPitch,0).accepted(),"relative accepted");
        double yaw = initialYaw, pitch = initialPitch, previousYawVelocity = 0, previousPitchVelocity = 0, moved = 0;
        for (int tick=0;tick<200;tick++) {
            CameraMotion.Frame frame = motor.tick(yaw,pitch,tick,.05);
            double yawVelocity = CameraMotion.wrap(frame.outputYaw()-yaw)/.05;
            double pitchVelocity = (frame.outputPitch()-pitch)/.05;
            check(Math.abs(yawVelocity) <= CONFIG.yaw().velocity()+1e-6,"yaw velocity limit");
            check(Math.abs(pitchVelocity) <= CONFIG.pitch().velocity()+1e-6,"pitch velocity limit");
            check(Math.abs(yawVelocity-previousYawVelocity)/.05 <= Math.max(CONFIG.yaw().acceleration(),CONFIG.yaw().deceleration())+1e-5,"yaw acceleration limit");
            check(Math.abs(pitchVelocity-previousPitchVelocity)/.05 <= Math.max(CONFIG.pitch().acceleration(),CONFIG.pitch().deceleration())+1e-5,"pitch acceleration limit");
            moved += CameraMotion.wrap(frame.outputYaw()-yaw);
            yaw = frame.outputYaw(); pitch = frame.outputPitch();
            check(pitch >= -90 && pitch <= 90,"pitch clamp");
            peakYaw = Math.max(peakYaw,Math.abs(yawVelocity)); peakPitch = Math.max(peakPitch,Math.abs(pitchVelocity));
            peakYawAcceleration = Math.max(peakYawAcceleration,Math.abs(yawVelocity-previousYawVelocity)/.05);
            peakOvershoot = Math.max(peakOvershoot,Math.max(frame.yawOvershoot(),frame.pitchOvershoot()));
            previousYawVelocity = yawVelocity; previousPitchVelocity = pitchVelocity;
            if (!motor.active()) {
                check(frame.settled(),"turn settled rather than timing out");
                check(Math.abs(moved-deltaYaw) <= CONFIG.tolerance(),"signed relative endpoint, including180 and wrap");
                check(Math.abs(pitch-Math.max(-90,Math.min(90,initialPitch+deltaPitch))) <= CONFIG.tolerance(),"pitch endpoint");
                check(frame.yawOvershoot() <= CONFIG.tolerance() && frame.pitchOvershoot() <= CONFIG.tolerance(),"no overshoot");
                cases++; return;
            }
        }
        throw new AssertionError("unbounded turn");
    }
    private static void reversalsAndCancellation() {
        CameraMotion motor = new CameraMotion(CONFIG);
        double yaw=0,pitch=0,previousVelocity=0;
        motor.submit(relative(1,90,0,0),yaw,pitch,0);
        double replacementTarget=0;
        for (int tick=0;tick<100;tick++) {
            if (tick==4) {
                replacementTarget=yaw-30;
                check(motor.submit(relative(2,-30,0,tick),yaw,pitch,tick).accepted(),"rapid reversal accepted");
                check(!motor.submit(relative(1,90,0,tick),yaw,pitch,tick).accepted(),"old command rejected");
            }
            CameraMotion.Frame frame=motor.tick(yaw,pitch,tick,.05);
            double velocity=(frame.outputYaw()-yaw)/.05;
            check(Math.abs(velocity-previousVelocity)/.05 <= CONFIG.yaw().deceleration()+1e-5,"reversal acceleration bound");
            previousVelocity=velocity; yaw=frame.outputYaw();
            if (!motor.active()) { check(Math.abs(yaw-replacementTarget)<CONFIG.tolerance(),"replacement never queues old endpoint"); break; }
        }
        check(!motor.active(),"reversal bounded"); cases++;
        motor=new CameraMotion(CONFIG); yaw=0; motor.submit(relative(1,90,0,0),0,0,0);
        for (int tick=0;tick<4;tick++) yaw=motor.tick(yaw,0,tick,.05).outputYaw();
        double cancelledAt=yaw; motor.cancel("test_interruption",false);
        for(int tick=4;tick<14 && motor.active();tick++) yaw=motor.tick(yaw,0,tick,.05).outputYaw();
        check(!motor.active() && yaw-cancelledAt<13,"interruption brakes boundedly"); cases++;
    }
    private static void commandSemantics() {
        CameraMotion motor=new CameraMotion(CONFIG);
        motor.submit(relative(1,15,0,0),0,0,0);
        check(!motor.submit(relative(1,15,0,0),0,0,0).accepted(),"duplicate relative is not accumulated");
        double yaw=0;
        for(int tick=0;tick<100 && motor.active();tick++) yaw=motor.tick(yaw,0,tick,.05).outputYaw();
        check(Math.abs(yaw-15)<CONFIG.tolerance(),"duplicate did not turn30"); cases++;
        check(!motor.submit(relative(2,10,0,0),yaw,0,20).accepted(),"stale observation rejected");
        check(!motor.submit(relative(2,Double.NaN,0,20),yaw,0,20).accepted(),"nonfinite command rejected"); cases++;
        motor=new CameraMotion(CONFIG);
        var velocity=new CameraMotion.Request(1,CameraMotion.Mode.CONTINUOUS,999,999,0,5);
        check(motor.submit(velocity,0,89,0).accepted(),"continuous velocity accepted and clipped"); yaw=0; double pitch=89;
        for(int tick=0;tick<30 && motor.active();tick++) {
            CameraMotion.Frame frame=motor.tick(yaw,pitch,tick,.05); yaw=frame.outputYaw(); pitch=frame.outputPitch();
            check(pitch<=90 && Math.abs(frame.yawVelocity())<=CONFIG.yaw().velocity(),"continuous caps");
        }
        check(!motor.active(),"continuous command expires without heartbeat"); cases++;
        motor=new CameraMotion(CONFIG); motor.submit(relative(1,90,0,0),0,0,0);
        CameraMotion.Frame frame=motor.tick(0,0,0,1);
        check(Math.abs(frame.outputYaw())<=CONFIG.yaw().velocity()*.05,"lag cannot make a large jump");
        double previous=frame.outputYaw(); frame=motor.tick(previous+20,0,1,.05);
        check(!frame.active() && frame.outputYaw()==previous+20 && frame.result().equals("external_pose_change"),"manual input is not fought"); cases++;
        motor=new CameraMotion(CONFIG); motor.submit(relative(1,90,0,0),0,0,0); yaw=0;
        for(int tick=0;tick<4;tick++) yaw=motor.tick(yaw,0,tick,.05).outputYaw();
        check(!motor.submit(relative(2,1,0,4),yaw,0,4).accepted(),"unsafe short retarget is rejected before braking");
        for(int tick=4;tick<20 && motor.active();tick++) yaw=motor.tick(yaw,0,tick,.05).outputYaw();
        check(!motor.active(),"rejected retarget leaves no queued turn"); cases++;
        motor=new CameraMotion(CONFIG); yaw=179; double moved=0;
        motor.submit(relative(1,15,0,0),yaw,0,0);
        for(int tick=0;tick<100 && motor.active();tick++) {
            CameraMotion.Frame wrapped=motor.tick(yaw,0,tick,.05);
            double next=CameraMotion.wrap(wrapped.outputYaw()); moved+=CameraMotion.wrap(next-yaw); yaw=next;
        }
        check(!motor.active() && Math.abs(moved-15)<CONFIG.tolerance(),"normalized observations across wrap remain correct"); cases++;
        motor=new CameraMotion(CONFIG); yaw=0;
        motor.submit(new CameraMotion.Request(1,CameraMotion.Mode.CONTINUOUS,60,0,0,5),0,0,0);
        for(int tick=0;tick<20;tick++) {
            if(tick==3) check(motor.submit(new CameraMotion.Request(1,CameraMotion.Mode.CONTINUOUS,60,0,tick,5),yaw,0,tick).accepted(),"velocity heartbeat renews without queue");
            CameraMotion.Frame continuous=motor.tick(yaw,0,tick,.05); yaw=continuous.outputYaw();
            check(continuous.yawError()==null && continuous.yawOvershoot()==null,"velocity mode has no invented endpoint error");
            if(tick==5) check(motor.active(),"renewal extends TTL");
        }
        check(!motor.active(),"renewed velocity still expires"); cases++;
        motor=new CameraMotion(CONFIG); yaw=0; double previousRate=0;
        motor.submit(relative(1,90,0,0),0,0,0);
        for(int tick=0;tick<100 && motor.active();tick++) {
            double dt=tick==5 ? 1.0 : .05;
            CameraMotion.Frame lagged=motor.tick(yaw,0,tick,dt);
            double rate=(lagged.outputYaw()-yaw)/dt;
            check(Math.abs(rate)<=CONFIG.yaw().velocity()+1e-6,"wall-time velocity after stall");
            check(Math.abs(rate-previousRate)/dt<=CONFIG.yaw().deceleration()+1e-5,"wall-time acceleration after stall");
            previousRate=rate; yaw=lagged.outputYaw();
        }
        check(!motor.active() && Math.abs(yaw-90)<CONFIG.tolerance(),"stall recovery settles"); cases++;
    }
    public static void main(String[] args) {
        check(Math.abs(CameraMotion.wrap(0-1000)-80)<1e-9,"resource angle remains valid beyond repeated full rotations");
        check(Math.abs(CameraMotion.wrap(179-(-540))+1)<1e-9,"negative accumulated heading wrap");
        for(double angle:new double[]{-.1,.1,-1,1,-5,5,-15,15,-45,45,-90,90,-179,179,-180,180})
            for(double yaw:new double[]{-179,0,179,359}) turn(yaw,0,angle,0);
        turn(179,89,5,20); turn(-179,-89,-5,-20); turn(0,0,45,35);
        Random random=new Random(20261028);
        for(int i=0;i<250;i++) turn(random.nextDouble()*1440-720,random.nextDouble()*160-80,
                                    random.nextDouble()*360-180,random.nextDouble()*100-50);
        reversalsAndCancellation(); commandSemantics();
        System.out.printf("{\"environment\":\"pure camera kinematic tests, not Minecraft\",\"cases\":%d,\"peak_yaw_deg_s\":%.6f,\"peak_pitch_deg_s\":%.6f,\"peak_yaw_accel_deg_s2\":%.6f,\"max_overshoot_deg\":%.9f}%n",
                cases,peakYaw,peakPitch,peakYawAcceleration,peakOvershoot);
    }
}

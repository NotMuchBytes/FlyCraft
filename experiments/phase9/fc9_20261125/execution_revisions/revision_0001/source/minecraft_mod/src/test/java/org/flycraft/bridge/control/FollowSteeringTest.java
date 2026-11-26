package org.flycraft.bridge.control;

public final class FollowSteeringTest {
    private static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
    private static FollowSteering.Output choose(double distance,boolean arrived,double y,double waypointY,
                                                double yaw,double waypointX,double waypointZ,boolean water,boolean route) {
        return FollowSteering.choose(new FollowSteering.Input(0,y,0,yaw,waypointX,waypointY,waypointZ,
            distance,arrived,true,water,false,route));
    }
    public static void main(String[] args) {
        check(choose(10,false,0,0,0,0,10,false,true).forward(),"walk toward a reachable waypoint");
        check(!choose(2,false,0,0,0,0,10,false,true).forward(),"respect owner spacing");
        check(choose(3.4,true,0,0,0,0,10,false,true).arrived(),"arrival hysteresis prevents start/stop jitter");
        check(!choose(3.6,true,0,0,0,0,10,false,true).arrived(),"resume after owner moves away");
        check(!choose(10,false,5,1,0,0,10,false,true).forward(),"do not walk off a large drop");
        check(choose(10,false,0,1,0,0,1,false,true).jump(),"jump up a path step");
        check(choose(10,false,0,0,0,0,1,true,false).jump(),"surface even while waiting for a water route");
        check(!choose(10,false,0,0,0,0,-10,false,true).forward(),"turn before walking backwards into hazards");
        check(Math.abs(choose(10,false,0,0,0,0,-10,false,true).yawRate())<=100,"bound requested turn speed");
        check(Math.abs(choose(10,false,0,0,179,-.1,-10,false,true).yawRate())<10,"use short yaw wraparound");
        boolean rejected=false;
        try { choose(Double.NaN,false,0,0,0,0,1,false,true); } catch(IllegalArgumentException expected) { rejected=true; }
        check(rejected,"reject invalid target observations");
        // Closed-loop motor check: a moving target reverses direction, then
        // stops. The real bounded camera controls the follower's orientation.
        CameraMotion camera=new CameraMotion(CameraMotion.Config.defaults());
        camera.reset(0,0);
        double x=0,z=0,yaw=0,targetX=12,targetZ=12,minGap=100,maxVelocity=0;
        boolean arrived=false;
        for(int tick=1;tick<=1200;tick++) {
            if(tick<350) targetZ+=.12;
            if(tick==400) { targetX-=8; targetZ-=8; }
            double distance=Math.hypot(targetX-x,targetZ-z);
            var command=FollowSteering.choose(new FollowSteering.Input(x,0,z,yaw,targetX,0,targetZ,distance,
                arrived,true,false,false,true));
            arrived=command.arrived();
            check(camera.submit(new CameraMotion.Request(tick,CameraMotion.Mode.CONTINUOUS,command.yawRate(),0,tick,5),yaw,0,tick).accepted(),"accept fresh motor request");
            var frame=camera.tick(yaw,0,tick,.05); yaw=frame.outputYaw();
            maxVelocity=Math.max(maxVelocity,Math.abs(frame.yawVelocity()));
            if(command.forward()) {
                double speed=command.sprint() ? .28 : .216;
                x-=Math.sin(Math.toRadians(yaw))*speed; z+=Math.cos(Math.toRadians(yaw))*speed;
            }
            minGap=Math.min(minGap,Math.hypot(targetX-x,targetZ-z));
        }
        check(Math.hypot(targetX-x,targetZ-z)<=3.5,"catch moving target and settle after reversal");
        check(minGap>=2,"do not crowd owner during settling");
        check(maxVelocity<=120.00001,"retain bounded camera velocity");
        System.out.println("{\"follow_cases\":12,\"closed_loop_ticks\":1200,\"minimum_gap\":"+minGap+"}");
    }
}

package org.flycraft.bridge.control;

/** Engineered companion locomotion only. Never used by the learned policy. */
public final class FollowSteering {
    public record Input(double x,double y,double z,double yaw,double waypointX,double waypointY,
                        double waypointZ,double ownerDistance,boolean arrived,boolean onGround,
                        boolean inWater,boolean horizontalCollision,boolean routeAvailable) { }
    public record Output(double yawRate,boolean forward,boolean jump,boolean sprint,boolean arrived) { }
    public static Output choose(Input input) {
        if(!Double.isFinite(input.x+input.y+input.z+input.yaw+input.waypointX+input.waypointY
                +input.waypointZ+input.ownerDistance) || input.ownerDistance<0)
            throw new IllegalArgumentException("Follow pose must be finite");
        boolean arrived=input.ownerDistance<=(input.arrived ? 3.5 : 2.5);
        if(arrived || !input.routeAvailable) return new Output(0,false,input.inWater,false,arrived);
        double dx=input.waypointX-input.x,dz=input.waypointZ-input.z;
        double error=CameraMotion.wrap(Math.toDegrees(Math.atan2(-dx,dz))-input.yaw);
        boolean safeDrop=input.waypointY>=input.y-1.25;
        boolean forward=safeDrop && Math.abs(error)<55;
        boolean jump=input.inWater || forward && input.onGround
                && (input.waypointY-input.y>.35 || input.horizontalCollision);
        return new Output(Math.clamp(error*5,-100,100),forward,jump,
                forward && input.ownerDistance>7 && !input.inWater,false);
    }
}

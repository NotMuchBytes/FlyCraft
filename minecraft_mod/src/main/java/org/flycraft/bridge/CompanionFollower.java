package org.flycraft.bridge;

import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.level.pathfinder.Path;
import net.minecraft.world.phys.Vec3;
import org.flycraft.bridge.control.FollowSteering;

/** Vanilla server pathfinding assistance, explicitly outside neural evaluation. */
final class CompanionFollower {
    record Step(FollowSteering.Output movement,String status,double distance,int pathNodes) { }
    private final UUID owner;
    private final PathfinderMob probe;
    private Path path;
    private long replanAt,progressTick;
    private Vec3 lastPosition,ownerAnchor;
    private int failedPlans;
    private boolean arrived,blocked;
    private final double stopDistance,resumeDistance;

    CompanionFollower(ServerPlayer actor,ServerPlayer target) {
        this(actor,target,2.5);
    }
    CompanionFollower(ServerPlayer actor,ServerPlayer target,double stopDistance) {
        if(stopDistance<1 || stopDistance>2.5) throw new IllegalArgumentException("Invalid follow spacing");
        this.stopDistance=stopDistance;resumeDistance=stopDistance==2.5 ? 3.5 : stopDistance+.4;
        owner=target.getUUID();
        // A player-sized navigation probe. It is never added to the world,
        // never ticks mob AI, and never attacks, drops items or changes blocks.
        probe=new PathfinderMob(EntityTypes.ZOMBIE,actor.level()) {
            @Override public boolean isInWater() { return actor.isInWater(); }
        };
        probe.getNavigation().setCanFloat(true);
        probe.getNavigation().setMaxVisitedNodesMultiplier(.5F);
        lastPosition=actor.position(); ownerAnchor=target.position();
        progressTick=actor.level().getServer().getTickCount();
    }

    Step tick(MinecraftServer server,ServerPlayer actor) {
        ServerPlayer target=server.getPlayerList().getPlayer(owner);
        if(target==null || !target.isAlive() || target.level()!=actor.level())
            return idle(actor,"owner_unavailable",0);
        double distance=actor.position().distanceTo(target.position());
        long tick=server.getTickCount();
        if(target.position().distanceToSqr(ownerAnchor)>4) {
            failedPlans=0; blocked=false; ownerAnchor=target.position(); replanAt=0;
        }
        if(distance>40) return idle(actor,"owner_too_far",distance);
        if(distance<=(arrived ? resumeDistance : stopDistance)) {
            arrived=true; path=null; failedPlans=0; blocked=false;
            lastPosition=actor.position(); progressTick=tick;
            return idle(actor,"near_owner",distance);
        }
        arrived=false;
        if(actor.position().distanceToSqr(lastPosition)>.16) {
            lastPosition=actor.position(); progressTick=tick;
        } else if(tick-progressTick>60) {
            path=null; replanAt=0; progressTick=tick;
            if(++failedPlans>=5) blocked=true;
        }
        if(blocked) return idle(actor,"blocked_waiting_for_owner",distance);
        if(tick>=replanAt) {
            replanAt=tick+20;
            probe.setPos(actor.getX(),actor.getY(),actor.getZ());
            probe.setOnGround(actor.onGround());
            probe.setDeltaMovement(actor.getDeltaMovement());
            path=probe.getNavigation().createPath(target.blockPosition(),0);
            if(path==null || path.getNodeCount()==0 || path.getNodeCount()>128) {
                path=null;
                if(++failedPlans>=5) blocked=true;
                return idle(actor,"no_route",distance);
            }
        }
        if(path==null) return idle(actor,"waiting_to_replan",distance);
        // Finite advancement, including the path's initial node under our feet.
        for(int advanced=0;advanced<path.getNodeCount() && !path.isDone();advanced++) {
            Vec3 point=path.getNextEntityPos(actor);
            if(Math.hypot(point.x-actor.getX(),point.z-actor.getZ())>.55 || Math.abs(point.y-actor.getY())>1) break;
            path.advance();
        }
        if(path.isDone()) return idle(actor,"path_end",distance);
        Vec3 point=path.getNextEntityPos(actor);
        var movement=FollowSteering.choose(new FollowSteering.Input(actor.getX(),actor.getY(),actor.getZ(),actor.getYRot(),
                point.x,point.y,point.z,distance,arrived,actor.onGround(),actor.isInWater(),actor.horizontalCollision,true),stopDistance,resumeDistance);
        return new Step(movement,movement.forward() ? "walking" : "turning_or_unsafe_drop",distance,path.getNodeCount());
    }

    private Step idle(ServerPlayer actor,String status,double distance) {
        return new Step(new FollowSteering.Output(0,false,actor.isInWater(),false,arrived),status,distance,0);
    }
}

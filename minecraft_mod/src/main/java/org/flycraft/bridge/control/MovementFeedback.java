package org.flycraft.bridge.control;

/** Own-pose feedback only: no target selection, steering or world-map access. */
public final class MovementFeedback {
    public static final double MINIMUM_DISTANCE = 0.02;
    private MovementFeedback() { }
    public record Result(double distance, boolean moved) { }
    public static Result measure(double startX, double startZ, double endX, double endZ) {
        if(!Double.isFinite(startX) || !Double.isFinite(startZ) || !Double.isFinite(endX) || !Double.isFinite(endZ))
            throw new IllegalArgumentException("Movement coordinates must be finite");
        double distance=Math.hypot(endX-startX,endZ-startZ);
        if(!Double.isFinite(distance)) throw new IllegalArgumentException("Movement distance must be finite");
        return new Result(distance,distance>=MINIMUM_DISTANCE);
    }
}

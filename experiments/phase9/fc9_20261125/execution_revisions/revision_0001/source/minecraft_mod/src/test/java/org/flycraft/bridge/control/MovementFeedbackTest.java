package org.flycraft.bridge.control;

public final class MovementFeedbackTest {
    private static void require(boolean value) { if(!value) throw new AssertionError(); }
    public static void main(String[] args) {
        require(!MovementFeedback.measure(4,7,4,7).moved());
        require(!MovementFeedback.measure(0,0,.019,0).moved());
        require(MovementFeedback.measure(0,0,.02,0).moved());
        require(MovementFeedback.measure(-4,7,-4.3,7.4).moved());
        require(Math.abs(MovementFeedback.measure(-4,7,-4.3,7.4).distance()-.5)<1e-12);
        for(double bad:new double[]{Double.NaN,Double.POSITIVE_INFINITY,Double.NEGATIVE_INFINITY}) {
            try { MovementFeedback.measure(bad,0,0,0); throw new AssertionError(); }
            catch(IllegalArgumentException expected) { }
        }
        System.out.println("{\"movement_cases\":8}");
    }
}

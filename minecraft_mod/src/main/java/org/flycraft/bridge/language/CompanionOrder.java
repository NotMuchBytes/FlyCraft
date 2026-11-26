package org.flycraft.bridge.language;

import java.util.*;

/** Request ownership and native-pickup receipts, independent from action selection. */
public final class CompanionOrder {
    public enum Phase { LOADING, COLLECTING, RETURNING, DELIVERING, DELIVERED, FAILED, CANCELLED }
    public final UUID id=UUID.randomUUID(),owner;
    public final String ownerName,item;
    public final int count;
    public final long createdTick;
    private Phase phase=Phase.LOADING;
    private final Map<UUID,Integer> parcels=new HashMap<>();
    private int received;
    private String reason="";
    public CompanionOrder(UUID owner,String ownerName,String item,int count,long tick) {
        EnglishOrders.goal(item);
        if(count<1 || count>16) throw new IllegalArgumentException("Invalid order count");
        this.owner=Objects.requireNonNull(owner);this.ownerName=ownerName;this.item=item;this.count=count;createdTick=tick;
    }
    public Phase phase() { return phase; }
    public String reason() { return reason; }
    public int received() { return received; }
    public boolean busy() { return phase!=Phase.DELIVERED && phase!=Phase.FAILED && phase!=Phase.CANCELLED; }
    public boolean authorized(UUID speaker) { return owner.equals(speaker); }
    public void collecting() { if(phase==Phase.LOADING) phase=Phase.COLLECTING; }
    public void returning(int held) { if((phase==Phase.LOADING || phase==Phase.COLLECTING) && held>=count) phase=Phase.RETURNING; }
    public void parcel(UUID entity,int units) {
        if(phase!=Phase.RETURNING && phase!=Phase.DELIVERING) throw new IllegalStateException("Not handing off");
        if(units<1 || parcels.containsKey(entity) || received+parcels.values().stream().mapToInt(Integer::intValue).sum()+units>count)
            throw new IllegalArgumentException("Invalid parcel");
        parcels.put(entity,units);phase=Phase.DELIVERING;
    }
    public boolean tracks(UUID entity,UUID recipient) { return phase==Phase.DELIVERING && owner.equals(recipient) && parcels.containsKey(entity); }
    public boolean receipt(UUID entity,UUID recipient,int units,int inventoryBefore,int inventoryAfter) {
        if(!tracks(entity,recipient) || units<1 || units>parcels.get(entity) || inventoryAfter-inventoryBefore<units) return false;
        int rest=parcels.get(entity)-units;if(rest==0)parcels.remove(entity);else parcels.put(entity,rest);
        received+=units;if(received==count) phase=Phase.DELIVERED;
        return true;
    }
    public void fail(String reason) { if(busy()) { phase=Phase.FAILED;this.reason=reason; } }
    public boolean cancel(UUID speaker) { if(!authorized(speaker))return false;if(busy()){phase=Phase.CANCELLED;reason="requested_stop";}return true; }
}

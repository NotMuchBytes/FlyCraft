package org.flycraft.bridge.language;
import java.util.*;
public final class EnglishOrdersTest {
    static void check(boolean value) { if(!value)throw new AssertionError(); }
    public static void main(String[] args) {
        var empty=Map.<String,String>of();int cases=0;
        for(String phrase:List.of("FlyCraft, get me 3 logs!","could you please bring me three logs?","get me 3 logs please")) {
            var i=EnglishOrders.parse(phrase,empty,true);check(i.kind()==EnglishOrders.Kind.GET && i.count()==3 && i.item().equals("log"));cases++;
        }
        for(String phrase:List.of("get me 0 logs","get me 17 logs","get me -1 logs","get me diamonds","get me oak logs","don't get me logs","get me logs and sticks","get me 999999999999999999 logs")) {
            check(EnglishOrders.parse(phrase,empty,true).kind()==EnglishOrders.Kind.REJECT);cases++;
        }
        check(EnglishOrders.parse("get me logs",empty,false).kind()==EnglishOrders.Kind.IGNORE);
        check(EnglishOrders.parse("ordinary chat ".repeat(20),empty,false).kind()==EnglishOrders.Kind.IGNORE);
        check(EnglishOrders.parse("FlyCraft, "+"long ".repeat(40),empty,false).kind()==EnglishOrders.Kind.REJECT);
        var learned=EnglishOrders.parse("teach timber means logs",empty,true);check(learned.kind()==EnglishOrders.Kind.TEACH);
        check(EnglishOrders.parse("get me two timber",Map.of(learned.alias(),learned.item()),true).count()==2);
        check(EnglishOrders.parse("teach stop means logs",empty,true).kind()==EnglishOrders.Kind.REJECT);
        UUID owner=UUID.randomUUID(),other=UUID.randomUUID(),parcel=UUID.randomUUID();
        var order=new CompanionOrder(owner,"Requester","log",3,10);
        order.returning(2);check(order.phase()==CompanionOrder.Phase.LOADING);
        order.collecting();order.returning(3);order.parcel(parcel,3);
        check(!order.receipt(parcel,other,3,0,3));check(!order.receipt(parcel,owner,3,0,0));
        check(order.receipt(parcel,owner,1,0,1));check(order.received()==1);
        check(order.receipt(parcel,owner,2,1,3));check(order.phase()==CompanionOrder.Phase.DELIVERED);
        check(!order.receipt(parcel,owner,3,3,6));check(!order.cancel(other));
        try {
            var folder=java.nio.file.Files.createTempDirectory("flycraft_words_");var path=folder.resolve("words.properties");
            var words=new WordMemory(path);words.learn(owner,"timber","log");words.learn(other,"timber","planks");
            words.learn(owner,"Lumber","log");
            var restored=new WordMemory(path);check(restored.forPlayer(owner).get("timber").equals("log"));
            check(restored.forPlayer(owner).get("lumber").equals("log"));
            check(restored.forPlayer(other).get("timber").equals("planks"));
            java.nio.file.Files.delete(path);java.nio.file.Files.delete(folder);
        } catch(java.io.IOException error) { throw new AssertionError(error); }
        System.out.println("{\"language_cases\":"+(cases+4)+",\"delivery_verified\":true}");
    }
}

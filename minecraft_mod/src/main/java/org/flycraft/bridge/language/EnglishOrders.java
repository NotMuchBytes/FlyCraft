package org.flycraft.bridge.language;

import java.util.*;
import java.util.regex.*;

/** Small teachable command language, not a general language model. */
public final class EnglishOrders {
    public enum Kind { IGNORE, GET, FOLLOW, STOP, STATUS, HELP, TEACH, REJECT }
    public record Intent(Kind kind,String item,int count,String alias,String message) { }
    private static final Map<String,String> ITEMS=Map.ofEntries(
        Map.entry("wood","log"),Map.entry("log","log"),Map.entry("logs","log"),
        Map.entry("plank","planks"),Map.entry("planks","planks"),Map.entry("wooden planks","planks"),
        Map.entry("stick","sticks"),Map.entry("sticks","sticks"),
        Map.entry("crafting table","crafting_table"),Map.entry("crafting tables","crafting_table"),
        Map.entry("workbench","crafting_table"),Map.entry("workbenches","crafting_table"),
        Map.entry("wooden pickaxe","wooden_pickaxe"),Map.entry("wooden pickaxes","wooden_pickaxe"),
        Map.entry("wood pickaxe","wooden_pickaxe"));
    private static final List<String> NUMBERS=List.of("one","two","three","four","five","six","seven","eight",
        "nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen");
    private static final Pattern GET=Pattern.compile("^(?:please )?(?:(?:can|could|would) you (?:please )?)?(?:get|fetch|bring|collect|gather|make|craft|mine)(?: me| us)? (.+?)(?: please)?$");
    private static final Pattern TEACH=Pattern.compile("^(?:teach )?([a-z ]{1,32}) (?:means|=) ([a-z ]{1,32})$");
    private static Intent result(Kind kind,String message) { return new Intent(kind,"",0,"",message); }
    public static String normalize(String text) {
        return text.toLowerCase(Locale.ROOT).replace('’','\'').replaceAll("[!?.,:;]"," ").replaceAll("\\s+"," ").trim();
    }
    public static Intent parse(String raw,Map<String,String> learned,boolean directed) {
        if(raw==null) return result(Kind.IGNORE,"");
        if(!directed && !normalize(raw).matches("^@?flycraft(?: .*|$)")) return result(Kind.IGNORE,"");
        if(raw.length()>180 || raw.indexOf('\n')>=0 || raw.indexOf('\r')>=0)
            return result(Kind.REJECT,"Use one short request, up to 180 characters.");
        String text=normalize(raw);
        if(text.matches("^@?flycraft(?: .*|$)")) { text=text.replaceFirst("^@?flycraft ?",""); directed=true; }
        if(!directed) return result(Kind.IGNORE,"");
        if(text.matches(".*\\b(?:don't|dont|not|never)\\b.*")) return result(Kind.REJECT,"No action started. Please give a positive request or say stop.");
        if(text.matches("(?:please )?(?:stop|cancel|stay|wait)(?: please)?")) return result(Kind.STOP,"");
        if(text.matches("(?:please )?(?:follow me|come here|come to me)(?: please)?")) return result(Kind.FOLLOW,"");
        if(Set.of("status","what are you doing","what do you have","how are you","who are you helping").contains(text)) return result(Kind.STATUS,"");
        if(Set.of("help","what can you do","what do you understand").contains(text)) return result(Kind.HELP,"");
        Matcher teach=TEACH.matcher(text);
        if(teach.matches()) {
            String alias=teach.group(1).trim(),item=ITEMS.get(teach.group(2).trim());
            if(item==null || ITEMS.containsKey(alias) || alias.matches(".*\\b(?:get|fetch|bring|stop|cancel|follow|status|help|teach|and|then)\\b.*"))
                return result(Kind.REJECT,"Teach a new item name, for example: teach timber means logs.");
            return new Intent(Kind.TEACH,item,0,alias,"");
        }
        Matcher get=GET.matcher(text);
        if(!get.matches()) return result(Kind.REJECT,"Try: get me 3 logs, follow me, stop, or status.");
        String phrase=get.group(1).trim();int count=1;
        String[] first=phrase.split(" ",2);String number=first[0];
        if(number.matches("[0-9]+") || NUMBERS.contains(number) || Set.of("a","an").contains(number)) {
            try { count=number.matches("[0-9]+") ? Integer.parseInt(number) : Set.of("a","an").contains(number) ? 1 : NUMBERS.indexOf(number)+1; }
            catch(NumberFormatException error) { return result(Kind.REJECT,"Request between 1 and 16 items."); }
            phrase=first.length==2 ? first[1] : "";
        }
        if(count<1 || count>16) return result(Kind.REJECT,"Request between 1 and 16 items.");
        String item=ITEMS.getOrDefault(phrase,learned.get(phrase));
        if(item==null || !ITEMS.containsValue(item)) return result(Kind.REJECT,"I can currently try logs, planks, sticks, crafting tables and wooden pickaxes. I cannot fetch that item yet.");
        return new Intent(Kind.GET,item,count,"","");
    }
    public static String goal(String item) {
        return switch(item) { case "log" -> "one_log"; case "planks","sticks","crafting_table","wooden_pickaxe" -> item; default -> throw new IllegalArgumentException("Unknown skill"); };
    }
    public static String label(String item,int count) {
        String noun=switch(item) { case "log" -> count==1 ? "log" : "logs"; case "planks" -> count==1 ? "plank" : "planks";
            case "sticks" -> count==1 ? "stick" : "sticks"; case "crafting_table" -> count==1 ? "crafting table" : "crafting tables";
            case "wooden_pickaxe" -> count==1 ? "wooden pickaxe" : "wooden pickaxes"; default -> item; };
        return count+" "+noun;
    }
}

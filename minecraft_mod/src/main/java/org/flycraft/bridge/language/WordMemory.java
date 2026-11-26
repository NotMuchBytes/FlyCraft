package org.flycraft.bridge.language;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.flycraft.bridge.AtomicFiles;

/** Explicit per-requester vocabulary teaching; persists without changing neural weights. */
public final class WordMemory {
    private final Path path;
    private Properties words=new Properties();
    public WordMemory(Path path) throws IOException {
        this.path=path;
        if(Files.exists(path)) {
            if(Files.size(path)>131072)throw new IOException("Word memory exceeds its bound");
            try(var reader=Files.newBufferedReader(path)) { words.load(reader); }
        }
    }
    public synchronized Map<String,String> forPlayer(UUID player) {
        var result=new HashMap<String,String>();String prefix=player+".";
        for(String key:words.stringPropertyNames())if(key.startsWith(prefix))result.put(key.substring(prefix.length()),words.getProperty(key));
        return Map.copyOf(result);
    }
    public synchronized void learn(UUID player,String alias,String item) throws IOException {
        String noun=EnglishOrders.label(item,1).substring(2);
        var check=EnglishOrders.parse("teach "+alias+" means "+noun,Map.of(),true);
        if(check.kind()!=EnglishOrders.Kind.TEACH || !check.item().equals(item))throw new IllegalArgumentException("Invalid word definition");
        alias=check.alias();
        if(!forPlayer(player).containsKey(alias) && (forPlayer(player).size()>=128 || words.size()>=1024))throw new IOException("Word memory is full");
        Properties next=new Properties();next.putAll(words);next.setProperty(player+"."+alias,item);
        Path temporary=path.resolveSibling(path.getFileName()+".tmp");
        try(var writer=Files.newBufferedWriter(temporary)) { next.store(writer,"User-taught item names; not neural language training"); }
        AtomicFiles.replace(temporary,path);words=next;
    }
}

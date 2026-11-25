package org.flycraft.bridge;

import java.io.IOException;
import java.nio.file.AccessDeniedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

/** Bounded retry of Windows reader sharing races; never expose partial JSON. */
public final class AtomicFiles {
    private AtomicFiles() { }

    public static void replace(Path temporary, Path destination) throws IOException {
        long deadline = System.nanoTime() + 1_000_000_000L;
        while (true) {
            try {
                Files.move(temporary, destination, StandardCopyOption.REPLACE_EXISTING,
                        StandardCopyOption.ATOMIC_MOVE);
                return;
            } catch (AccessDeniedException sharingRace) {
                if (System.nanoTime() >= deadline) throw sharingRace;
                try {
                    Thread.sleep(10);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new IOException("Interrupted while publishing control file", interrupted);
                }
            }
        }
    }
}

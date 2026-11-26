"""Exercise the actual Java publisher against native Windows sharing locks."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / ".runtime/jdk-25/bin/java.exe"


@unittest.skipUnless(os.name == "nt" and JAVA.is_file(), "Windows and prepared JDK required")
class AtomicControlTests(unittest.TestCase):
    def test_sharing_race_retries_and_permanent_lock_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Publish.java"
            source.write_text("import java.nio.file.Path; import org.flycraft.bridge.AtomicFiles; public class Publish { public static void main(String[] a) throws Exception { AtomicFiles.replace(Path.of(a[0]), Path.of(a[1])); } }")
            subprocess.run([str(JAVA.with_name("javac.exe")), "-d", str(root), str(source),
                str(ROOT / "minecraft_mod/src/main/java/org/flycraft/bridge/AtomicFiles.java")],
                check=True, capture_output=True, timeout=30)
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                          wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            target, temporary = root / "control.json", root / "control.json.tmp"
            for permanent in (False, True):
                with self.subTest(permanent=permanent):
                    target.write_text('{"active":false}')
                    temporary.write_text('{"active":true}')
                    # Share reads/writes, deliberately deny FILE_SHARE_DELETE.
                    handle = kernel.CreateFileW(str(target), 0x80000000, 3, None, 3, 0x80, None)
                    self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
                    started = time.monotonic()
                    process = subprocess.Popen([str(JAVA), "-cp", str(root), "Publish", str(temporary), str(target)],
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        if permanent:
                            process.communicate(timeout=6)
                            self.assertNotEqual(process.returncode, 0)
                            self.assertEqual(target.read_text(), '{"active":false}')
                            self.assertEqual(temporary.read_text(), '{"active":true}')
                            self.assertLess(time.monotonic() - started, 6)
                        else:
                            time.sleep(.35)
                            self.assertEqual(target.read_text(), '{"active":false}')
                            kernel.CloseHandle(handle)
                            handle = None
                            process.communicate(timeout=6)
                            self.assertEqual(process.returncode, 0)
                            self.assertEqual(target.read_text(), '{"active":true}')
                            self.assertFalse(temporary.exists())
                    finally:
                        if handle:
                            kernel.CloseHandle(handle)
                        if process.poll() is None:
                            process.kill()
                            process.wait()

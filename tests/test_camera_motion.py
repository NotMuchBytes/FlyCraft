import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
JAVA_DIR = ROOT / ".runtime/jdk-25/bin"
JAVAC = JAVA_DIR / "javac.exe"
JAVA = JAVA_DIR / "java.exe"


@unittest.skipUnless(JAVAC.is_file() and JAVA.is_file(), "Local JDK25 unavailable")
class CameraMotionTests(unittest.TestCase):
    def test_real_java_controller_kinematics_and_command_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            sources = [ROOT / "minecraft_mod/src/main/java/org/flycraft/bridge/control/CameraMotion.java",
                       ROOT / "minecraft_mod/src/test/java/org/flycraft/bridge/control/CameraMotionTest.java"]
            compiled = subprocess.run([str(JAVAC), "-d", directory, *map(str,sources)], capture_output=True, text=True, timeout=30)
            self.assertEqual(compiled.returncode,0,compiled.stderr)
            result = subprocess.run([str(JAVA), "-cp", directory, "org.flycraft.bridge.control.CameraMotionTest"],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            metrics = json.loads(result.stdout)
            self.assertGreater(metrics["cases"],300)
            self.assertLessEqual(metrics["max_overshoot_deg"],.02)

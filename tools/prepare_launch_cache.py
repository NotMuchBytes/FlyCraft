"""Build and export one immutable server/client launcher cache, without playing."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.launch_cache import freeze_cache, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--server-heap-mib", type=int, default=384)
    parser.add_argument("--client-heap-mib", type=int, default=512)
    parser.add_argument("--capture-width", type=int, default=854)
    parser.add_argument("--capture-height", type=int, default=480)
    parser.add_argument("--graphics-backend", default="opengl", choices=("opengl",))
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    java = ROOT / ".runtime/jdk-25/bin/java.exe"
    command = [str(java), "-Xmx64m", "-classpath", "gradle/wrapper/gradle-wrapper.jar",
        "org.gradle.wrapper.GradleWrapperMain", "--offline", "--no-daemon", "--max-workers=2", "--console=plain",
        "-Dorg.gradle.jvmargs=-Xmx512m", "-PflycraftBuildDir=" + args.build_dir.resolve().as_posix(),
        "-PflycraftRunDir=" + (args.output / "prepare").as_posix(), "-PflycraftAutotest",
        "-PflycraftServer=127.0.0.1:25567", "-PflycraftGraphicsBackend=opengl",
        "-PflycraftServerHeapMiB=" + str(args.server_heap_mib), "-PflycraftClientHeapMiB=" + str(args.client_heap_mib),
        "-PflycraftCaptureWidth=" + str(args.capture_width), "-PflycraftCaptureHeight=" + str(args.capture_height),
        "-PflycraftExportLaunchDir=" + args.output.as_posix(), "runServer", "runClient"]
    with (args.output / "prepare.log").open("x", encoding="utf-8") as log:
        subprocess.run(command, cwd=ROOT / "minecraft_mod", stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    print(freeze_cache(args.output, ROOT, profile(args)))


if __name__ == "__main__":
    main()

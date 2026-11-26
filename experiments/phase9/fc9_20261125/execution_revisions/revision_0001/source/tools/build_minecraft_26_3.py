"""Build an isolated 26.3 client/companion preview, preserving the 26.2 baseline."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def replace(path, before, after):
    text = path.read_text(encoding="utf-8-sig")
    if text.count(before) != 1:
        raise ValueError(f"Expected exactly one compatibility anchor in {path.name}: {before}")
    path.write_text(text.replace(before, after), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True, help="New, empty build directory")
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists():
        raise SystemExit("Destination already exists; preserve previous builds and choose a new directory")
    shutil.copytree(ROOT / "minecraft_mod", target,
                    ignore=shutil.ignore_patterns("build", ".gradle", "dist", "run", ".github"))
    replace(target / "gradle.properties", "minecraft_version=26.2", "minecraft_version=26.3")
    replace(target / "gradle.properties", "loader_version=0.19.5", "loader_version=0.20.1")
    replace(target / "gradle.properties", "fabric_api_version=0.161.0+26.2", "fabric_api_version=0.165.0+26.3")
    replace(target / "src/main/resources/fabric.mod.json", '"minecraft": "~26.2"', '"minecraft": "~26.3"')
    headless = target / "src/main/java/org/flycraft/bridge/HeadlessAgent.java"
    replace(headless, "new ServerboundAcceptTeleportationPacket(position.id())",
            "new ServerboundAcceptTeleportationPacket(position.id(), player.getX(), player.getY(), player.getZ(), player.getYRot(), player.getXRot())")
    replace(headless, "player.swing(net.minecraft.world.InteractionHand.MAIN_HAND);",
            "player.swing(net.minecraft.world.InteractionHand.MAIN_HAND, net.minecraft.world.item.component.SwingAnimation.DEFAULT, true);")
    replace(target / "src/client/java/org/flycraft/bridge/client/Phase8Client.java",
            "client.player.swing(InteractionHand.MAIN_HAND);",
            "client.player.swing(InteractionHand.MAIN_HAND, net.minecraft.world.item.component.SwingAnimation.DEFAULT, true);")
    # 26.3 replaced GLFW with SDL. The old background-test window redirect must
    # not be injected into an SDL client. Other packet/render/skin mixins stay.
    replace(target / "src/client/resources/flycraft.phase8.mixins.json", '"Phase8WindowMixin", ', "")
    replace(target / "src/client/java/org/flycraft/bridge/client/mixin/CameraRenderMixin.java",
            "flycraftCameraRendered(DeltaTracker tracker,boolean renderWorld,CallbackInfo callback)",
            "flycraftCameraRendered(CallbackInfo callback)")
    with (target / "build.gradle").open("a", encoding="utf-8") as handle:
        handle.write("\n// 26.3 SDL preview: no obsolete GLFW window redirect.\nsourceSets.client.java.exclude('**/Phase8WindowMixin.java')\n")
    env = os.environ.copy()
    env["JAVA_HOME"] = str(ROOT / ".runtime/jdk-25")
    # Java test mains run through the Python suite. Gradle's assemble task
    # builds both source sets without treating these mains as missing JUnit tests.
    result = subprocess.run([str(target / "gradlew.bat"), "--no-daemon", "--max-workers=2", "assemble"],
                            cwd=target, env=env)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

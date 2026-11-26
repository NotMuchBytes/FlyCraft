"""Own a dedicated background OBS recorder without touching the desktop UI."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

import psutil

from tools.obs_control import ObsRecorder


def obs_running():
    return any((process.info["name"] or "").lower() == "obs64.exe"
               for process in psutil.process_iter(["name"]))


def archive_stale_markers(config_root, archive):
    """Reversibly preserve empty session markers only while OBS is absent."""
    if obs_running():
        return []
    config_root, archive = Path(config_root).resolve(), Path(archive).resolve()
    source = (config_root / ".sentinel").resolve()
    if source.parent != config_root:
        raise ValueError("Unexpected OBS marker directory")
    archive.mkdir(parents=True, exist_ok=True)
    moved = []
    for path in source.glob("run_*"):
        if not re.fullmatch(r"run_[0-9a-fA-F-]{36}", path.name) or not path.is_file() or path.stat().st_size:
            raise ValueError("Unrecognized OBS session marker; inspection required")
        destination = archive / path.name
        if destination.exists() or path.resolve().parent != source:
            raise ValueError("Refusing to overwrite or move an unexpected OBS marker")
        shutil.move(str(path), str(destination))
        moved.append({"source": str(path), "archive": str(destination), "bytes": 0})
    return moved


def check_profile(config_root):
    path = Path(config_root) / "basic/scenes/FlyCraft_Background.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    sources = data["sources"]
    if any("AudioDevice" in key for key in data):
        raise ValueError("Dedicated OBS collection must have no global audio devices")
    captures = [source for source in sources if source["id"] == "window_capture"]
    if len(captures) != 1 or any(source["id"] not in ("window_capture", "scene") for source in sources):
        raise ValueError("Dedicated OBS collection must contain only one Minecraft window capture")
    settings = captures[0]["settings"]
    if settings.get("priority") != 0 or settings.get("capture_audio") or settings.get("cursor"):
        raise ValueError("OBS must match the exact Minecraft title, without audio or cursor capture")
    return {"collection": "FlyCraft Background", "window_capture": captures[0]["name"],
            "desktop_capture": False, "audio_capture": False}


class BackgroundRecorder:
    def __init__(self, control_dir, archive, *, executable=None, config_root=None):
        self.control_dir, self.archive = Path(control_dir), Path(archive)
        self.executable = Path(executable or "C:/Program Files/obs-studio/bin/64bit/obs64.exe")
        self.config_root = Path(config_root or Path.home() / "AppData/Roaming/obs-studio")
        self.process = None
        self.recovery = []

    def ensure_ready(self, stop_requested=lambda: False):
        profile = check_profile(self.config_root)
        self.archive.mkdir(parents=True, exist_ok=True)
        if self.process is not None and self.process.poll() is None:
            ObsRecorder(self.control_dir, "readiness")
            return profile
        if obs_running():
            raise RuntimeError("An unowned OBS process is running; it was left untouched")
        self.recovery += archive_stale_markers(self.config_root, self.archive / "session_markers")
        startup = None
        if os.name == "nt":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        self.log = (self.archive / "obs_launcher.log").open("ab")
        self.process = subprocess.Popen([str(self.executable), "--minimize-to-tray",
            "--collection", "FlyCraft Background", "--profile", "FlyCraft Background"],
            cwd=self.executable.parent, stdout=self.log, stderr=subprocess.STDOUT,
            startupinfo=startup, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and not stop_requested():
            if self.process.poll() is not None:
                break
            try:
                ObsRecorder(self.control_dir, "readiness")
                return profile
            except RuntimeError:
                time.sleep(.5)
        raise RuntimeError("Owned OBS did not produce a fresh stopped heartbeat")

    def close(self):
        if self.process is None:
            if hasattr(self, "log"):
                self.log.close()
            return
        if self.process.poll() is None:
            state = ObsRecorder.__new__(ObsRecorder)
            state.state_file = self.control_dir / "obs-state.txt"
            current = state.state()
            if current is None or current[1] != "stopped":
                raise RuntimeError("Owned OBS has not confirmed recording stopped; recorder left running")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.log.close()
        self.recovery += archive_stale_markers(self.config_root, self.archive / "session_markers")
        (self.archive / "recorder_lifecycle.json").write_text(json.dumps({
            "owned_pid": self.process.pid, "exited": True, "archived_markers": self.recovery}, indent=2),
            encoding="utf-8", newline="\n")

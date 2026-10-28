"""File-based control of the companion OBS Lua script; never generates desktop input."""
import os
import time
from pathlib import Path


class ObsRecorder:
    def __init__(self, directory: Path, token: str):
        self.directory, self.token = directory, token
        self.command_file, self.state_file = directory / "obs-command.txt", directory / "obs-state.txt"
        self.started = False
        self.last_path = None
        state = self.state()
        if state is None or state[1] != "stopped":
            raise RuntimeError("OBS background recorder is unavailable or already busy")

    def state(self):
        try:
            values = self.state_file.read_text(encoding="utf-8").splitlines()
            if len(values) < 6 or abs(time.time() - int(values[5])) > 5:
                return None
            return values
        except (OSError, ValueError):
            return None

    def command(self, name):
        temporary = self.command_file.with_suffix(".tmp")
        temporary.write_text(f"{self.token}\n{name}\n{int(time.time())}\n", encoding="utf-8")
        os.replace(temporary, self.command_file)

    def pulse(self):
        self.command("start")
        state = self.state()
        # OBS replaces its local status file. Retry a transient rename gap or
        # UI-thread stall, while still requiring positive active confirmation.
        deadline = time.monotonic() + 2
        while state is None and time.monotonic() < deadline:
            time.sleep(0.05)
            state = self.state()
        active = state is not None and state[0] == self.token and state[1] == "recording"
        if self.started and not active:
            raise RuntimeError("OBS recording confirmation was lost")
        self.started = self.started or active
        return active

    def stop(self):
        self.command("stop")
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            state = self.state()
            if state is not None and state[0] == self.token and state[1] == "stopped":
                candidate = Path(state[2]) if state[2] else None
                if self.started and candidate and candidate.is_file():
                    self.last_path = candidate
                return self.last_path
            time.sleep(0.25)
        return None

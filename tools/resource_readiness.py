"""Keep the existing 30-second healthy window across episode boundaries."""
import threading
import time

import psutil


class ResourceReadiness:
    def __init__(self, root, temperature, *, memory=psutil.virtual_memory, disk=psutil.disk_usage, clock=time.monotonic):
        self.root, self.temperature = root, temperature
        self.memory, self.disk, self.clock = memory, disk, clock
        self.lock, self.stop = threading.Lock(), threading.Event()
        self.healthy_since = {1800: None, 3000: None}
        self.latest = None
        self.error = None

    def sample(self):
        now = self.clock()
        value = dict(available_ram_mib=self.memory().available / 1024**2,
                     free_disk_mib=self.disk(str(self.root)).free / 1024**2,
                     gpu_temperature_c=self.temperature(), sampled_monotonic=now)
        with self.lock:
            for threshold in self.healthy_since:
                healthy = value["available_ram_mib"] >= threshold and value["free_disk_mib"] >= 2048 \
                    and (value["gpu_temperature_c"] is None or value["gpu_temperature_c"] < 75)
                if not healthy:
                    self.healthy_since[threshold] = None
                elif self.healthy_since[threshold] is None:
                    self.healthy_since[threshold] = now
            self.latest = value

    def readiness(self, threshold):
        with self.lock:
            if self.error:
                raise RuntimeError(self.error)
            if threshold not in self.healthy_since:
                raise ValueError("unsupported launch reserve")
            since = self.healthy_since[threshold]
            fresh = self.latest is not None and self.clock() - self.latest["sampled_monotonic"] <= 5
            ready = fresh and since is not None and self.clock() - since >= 30
            return ready, dict(self.latest or {})

    def __enter__(self):
        self.sample()

        def monitor():
            while not self.stop.wait(1):
                try:
                    self.sample()
                except Exception as error:
                    with self.lock:
                        self.error = str(error)
                    return

        self.thread = threading.Thread(target=monitor, name="FlyCraft resource readiness", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *unused):
        self.stop.set()
        self.thread.join(timeout=5)

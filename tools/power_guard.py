"""Temporary Windows sleep/shutdown guard, released on critical battery.

This blocks ordinary session shutdown only. Windows' forced shutdown and a
physical power-off can override it. No power-plan or critical-battery setting
is changed, and the display is allowed to sleep.
"""

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import time

import psutil


def critical_battery(battery, threshold=5):
    return battery is not None and not battery.power_plugged and battery.percent <= threshold


def request_stop(paths, *, reason=None):
    for path in paths:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        path.touch(exist_ok=True)
        if reason and not existed:
            sidecar = path.with_name(path.name + ".reason.json")
            sidecar.write_text(json.dumps(dict(reason=reason, stop_mtime_ns=path.stat().st_mtime_ns,
                created_unix=time.time())), encoding="utf-8")


def publish_status(path, payload, *, replace=os.replace, sleep=time.sleep, clock=time.monotonic):
    """A dashboard reader must never take down the native shutdown guard."""
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        deadline = clock() + 1
        while True:
            try:
                replace(temporary, path)
                return True
            except PermissionError:
                if clock() >= deadline:
                    return False
                sleep(.01)
    except OSError:
        return False


class WindowsGuard:
    """Own an invisible top-level window; never manipulate another app's UI."""

    def __init__(self, on_shutdown):
        if os.name != "nt":
            raise OSError("The shutdown guard requires Windows")
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.hwnd = None
        self.registered = False
        self.execution_state = False
        self.reason_created = False
        self.on_shutdown = on_shutdown
        self.name = f"FlyCraftPowerGuard_{os.getpid()}"
        result_type = ctypes.c_ssize_t
        callback_type = ctypes.WINFUNCTYPE(result_type, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        class WindowClass(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", callback_type),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        self.kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel.GetModuleHandleW.restype = wintypes.HMODULE
        self.kernel.SetThreadExecutionState.argtypes = [wintypes.DWORD]
        self.kernel.SetThreadExecutionState.restype = wintypes.DWORD
        self.user.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user.DefWindowProcW.restype = result_type
        self.user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
        self.user.RegisterClassW.restype = wintypes.ATOM
        self.user.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
            wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        self.user.CreateWindowExW.restype = wintypes.HWND
        self.user.DestroyWindow.argtypes = [wintypes.HWND]
        self.user.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        self.user.ShutdownBlockReasonCreate.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user.ShutdownBlockReasonDestroy.argtypes = [wintypes.HWND]
        self.user.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
        self.user.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        self.user.DispatchMessageW.restype = result_type
        self.user.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]

        def procedure(hwnd, message, wparam, lparam):
            if message == 0x0011:  # WM_QUERYENDSESSION: ordinary shutdown/logoff
                return 0
            if message == 0x0016 and wparam:  # WM_ENDSESSION: forced override
                self.on_shutdown()
                return 0
            return self.user.DefWindowProcW(hwnd, message, wparam, lparam)

        self.callback = callback_type(procedure)
        self.instance = self.kernel.GetModuleHandleW(None)
        self.window_class = WindowClass(0, self.callback, 0, 0, self.instance,
                                       None, None, None, None, self.name)

    def __enter__(self):
        try:
            if not self.user.RegisterClassW(ctypes.byref(self.window_class)):
                raise ctypes.WinError(ctypes.get_last_error())
            self.registered = True
            self.hwnd = self.user.CreateWindowExW(0, self.name, "FlyCraft training power guard",
                0, 0, 0, 0, 0, None, None, self.instance, None)
            if not self.hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            if not self.user.ShutdownBlockReasonCreate(self.hwnd,
                    "FlyCraft training is active. Use its STOP file before shutting down. Critical battery releases this guard."):
                raise ctypes.WinError(ctypes.get_last_error())
            self.reason_created = True
            if not self.kernel.SetThreadExecutionState(0x80000001):  # continuous | system required
                raise ctypes.WinError(ctypes.get_last_error())
            self.execution_state = True
            return self
        except BaseException:
            self.__exit__()
            raise

    def pump(self):
        message = wintypes.MSG()
        while self.user.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
            self.user.TranslateMessage(ctypes.byref(message))
            self.user.DispatchMessageW(ctypes.byref(message))

    def __exit__(self, *unused):
        if self.execution_state:
            self.kernel.SetThreadExecutionState(0x80000000)
            self.execution_state = False
        if self.hwnd:
            if self.reason_created:
                self.user.ShutdownBlockReasonDestroy(self.hwnd)
            self.user.DestroyWindow(self.hwnd)
            self.hwnd = None
        if self.registered:
            self.user.UnregisterClassW(self.name, self.instance)
            self.registered = False


def run(folder, stop_files, *, battery=psutil.sensors_battery, guard=WindowsGuard, sleep=time.sleep):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    status_path = folder / "status.json"

    def status(state, sample=None, error=None):
        payload = {"status": state, "pid": os.getpid(), "updated_unix": time.time(),
                   "critical_percent": 5, "battery_percent": sample.percent if sample else None,
                   "power_plugged": sample.power_plugged if sample else None,
                   "blocks_idle_sleep": state == "active", "blocks_normal_shutdown": state == "active",
                   "forced_shutdown_can_override": True, "stop_files": [str(p) for p in stop_files],
                   "release_file": str(folder / "RELEASE"), "error": error}
        return publish_status(status_path, payload)

    try:
        with guard(lambda: request_stop(stop_files)) as native:
            while True:
                native.pump()
                sample = battery()
                if critical_battery(sample):
                    request_stop(stop_files, reason="critical_battery")
                    break
                if (folder / "RELEASE").exists():
                    break
                status("active", sample)
                sleep(1)
        status("released_critical_battery" if critical_battery(sample) else "released", sample)
    except BaseException as error:
        status("failed", error=str(error))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--stop-file", type=Path, action="append", required=True)
    args = parser.parse_args()
    run(args.state_dir.resolve(), [p.resolve() for p in args.stop_file])


if __name__ == "__main__":
    main()

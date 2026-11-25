"""Freeze and validate Loom launch exports instead of rerunning Gradle per world."""
import hashlib
import json
import os
from pathlib import Path

from autonomy.experiment import atomic_json, digest, source_manifest
from tools.java_launch import command_from_export


def profile(args):
    return {key: getattr(args, key) for key in ("server_heap_mib", "client_heap_mib", "capture_width", "capture_height", "graphics_backend")}


def freeze_cache(folder, root, settings):
    folder, root = Path(folder).resolve(), Path(root).resolve()
    paths = set()

    def add(value):
        path = Path(value).resolve(strict=True)
        if path.is_dir():
            paths.update(p for p in path.rglob("*") if p.is_file())
        else:
            paths.add(path)

    for task in ("runServer", "runClient"):
        path = folder / (task + ".json")
        add(path)
        exported = json.loads(path.read_text(encoding="utf-8"))
        add(exported["executable"])
        arguments = exported["arguments"]
        for i, argument in enumerate(arguments):
            if argument in ("-cp", "-classpath"):
                for value in arguments[i + 1].split(os.pathsep):
                    add(value)
            if argument.startswith("-Dfabric.dli.config="):
                config = Path(argument.partition("=")[2])
                add(config)
                for line in config.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        values = line.strip().partition("=")[2]
                        for value in values.split(os.pathsep):
                            if value and Path(value).exists():
                                add(value)
    hashes = {str(p): digest(p) for p in sorted(paths)}
    value = {"schema": 1, "implementation_sha256": source_manifest(root)["implementation_sha256"],
             "profile": settings, "files": hashes, "tasks": ["runServer", "runClient"]}
    atomic_json(folder / "manifest.json", value)
    return {"path": str(folder / "manifest.json"), "sha256": digest(folder / "manifest.json")}


def cached_commands(manifest_path, expected_sha256, root, args, export_dir, java):
    manifest_path = Path(manifest_path).resolve()
    if digest(manifest_path) != expected_sha256:
        raise ValueError("launch cache manifest changed")
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or value["implementation_sha256"] != source_manifest(root)["implementation_sha256"]:
        raise ValueError("launch cache source mismatch")
    if value["profile"] != profile(args):
        raise ValueError("launch cache runtime profile mismatch")
    for name, expected in value["files"].items():
        if digest(name) != expected:
            raise ValueError("launch cache artifact changed: " + name)
    export_dir.mkdir(parents=True, exist_ok=False)
    names = ("server", "client") if not args.headless or args.spectator else ("server",)
    return {name: command_from_export(manifest_path.parent / ("run" + name.title() + ".json"),
            export_dir / (name + ".args"), expected_java=java) for name in names}

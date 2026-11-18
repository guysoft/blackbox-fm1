#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The same source fingerprint in Git checkouts and complete release archives."""
import hashlib
import json
from pathlib import Path
import subprocess

LOCK = ".source-fingerprint.json"


def tracked_paths(root):
    return sorted(set(p for p in subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root).decode().split("\0") if p))


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root):
    root = Path(root)
    result = {"files": {}, "modules": {}}
    for name in tracked_paths(root):
        path = root / name
        if path.is_file():
            result["files"][name] = file_sha(path)
        elif path.is_dir() and (path / ".git").exists():
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=path).decode().strip()
            result["modules"][name] = {
                "commit": revision,
                "files": {p: file_sha(path / p) for p in tracked_paths(path)
                          if (path / p).is_file()},
            }
    return result


def fingerprint(record):
    h = hashlib.sha256()
    for name in sorted(set(record["files"]) | set(record["modules"])):
        value = (bytes.fromhex(record["files"][name]) if name in record["files"] else
                 (record["modules"][name]["commit"] + "\n").encode())
        h.update(name.encode() + b"\0" + value)
    return h.hexdigest()


def verify_files(root, files):
    for name, expected in files.items():
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or file_sha(root / rel) != expected:
            raise ValueError(f"release source file changed: {name}")


def source_sha(root):
    root = Path(root)
    if (root / ".git").exists():
        return fingerprint(snapshot(root))
    record = json.loads((root / LOCK).read_text())
    verify_files(root, record["files"])
    for name, module in record["modules"].items():
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("invalid source module path")
        verify_files(root / rel, module["files"])
    return fingerprint(record)

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Explicit project-local tool/firmware download. Never installs system packages.

Without --fetch, verifies existing files only. A checksum mismatch is a hard
stop, not an excuse to replace a pin or upgrade a tool.
"""
import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(path, sha):
    if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
        raise ValueError(f"checksum mismatch: {path}; existing file preserved")


def obtain(item, downloads, fetch=False):
    path = downloads / item["file"]
    if path.exists():
        verify(path, item["sha256"])
        return path
    if not fetch:
        raise FileNotFoundError(f"{path}: run bootstrap.py --fetch explicitly")
    downloads.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=downloads, prefix="download-", delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            with urllib.request.urlopen(item["url"], timeout=120) as r:
                shutil.copyfileobj(r, tmp)
            tmp.close()
            verify(temporary, item["sha256"])
            temporary.replace(path)
        except BaseException:
            # Retain the failed download for diagnosis, never overwrite a user's input.
            print(f"failed download retained at {temporary}")
            raise
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fetch", action="store_true", help="download pinned tools, SDK assets and stock files locally")
    a = ap.parse_args()
    if a.fetch:
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "docs/reference-lock.json").read_text())
    for item in lock["downloads"]:
        path = obtain(item, ROOT / "artifacts/downloads", a.fetch)
        print(f"verified {item['file']}")
        if a.fetch and item.get("extract"):
            dest = ROOT / "artifacts/toolchain"
            dest.mkdir(parents=True, exist_ok=True)
            # Check the pin before reading an archive. Refuse archives that
            # would overwrite existing tool files; existing local tools are
            # never silently upgraded/reinstalled.
            with tarfile.open(path) as archive:
                top = archive.getmembers()[0].name.split("/")[0]
                if not (dest / top).exists():
                    archive.extractall(dest, filter="data")
        if a.fetch and "sdk_path" in item:
            dest = ROOT / "artifacts/sdk/cpu/wl82/tools" / item["sdk_path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                verify(dest, item["sha256"])
            else:
                shutil.copyfile(path, dest)
    print("No system software installed or upgraded. Use the project-local uv with sync --frozen.")


if __name__ == "__main__":
    main()

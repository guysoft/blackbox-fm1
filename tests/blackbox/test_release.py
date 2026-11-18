# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

import pytest

from release_blackbox import notes, source_archive
from source_fingerprint import LOCK, file_sha, fingerprint, snapshot, source_sha


def test_archive_fingerprint_detects_modified_sources(tmp_path):
    (tmp_path / "app.c").write_text("int main(void) { return 0; }\n")
    module = tmp_path / "firmware/bsp"
    module.mkdir(parents=True)
    (module / "gpio.h").write_text("/* original */\n")
    record = {
        "files": {"app.c": file_sha(tmp_path / "app.c")},
        "modules": {"firmware/bsp": {"commit": "a" * 40,
                                    "files": {"gpio.h": file_sha(module / "gpio.h")}}},
    }
    (tmp_path / LOCK).write_text(json.dumps(record))
    assert source_sha(tmp_path) == fingerprint(record)
    (module / "gpio.h").write_text("/* changed */\n")
    with pytest.raises(ValueError, match="gpio.h"):
        source_sha(tmp_path)


def test_archive_rejects_external_paths(tmp_path):
    record = {"files": {"../outside": "0" * 64}, "modules": {}}
    (tmp_path / LOCK).write_text(json.dumps(record))
    with pytest.raises(ValueError):
        source_sha(tmp_path)


def test_complete_source_archive(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "app.c").write_text("/* distributable source */\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "Test"], cwd=root, check=True)
    record = snapshot(root)
    outputs = [tmp_path / "one.tar.gz", tmp_path / "two.tar.gz"]
    for output in outputs:
        source_archive(output, root, "source", record, 1234567890)
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    dest = tmp_path / "extracted"
    with tarfile.open(outputs[0]) as archive:
        assert all("/.git/" not in p.name and "/artifacts/" not in p.name for p in archive)
        archive.extractall(dest, filter="data")
    assert source_sha(dest / "source") == source_sha(root)
    assert (dest / "source/app.c").read_bytes() == (root / "app.c").read_bytes()


def test_release_notes_distinguish_evidence_and_limits():
    text = notes("v0.1.0-alpha.1", {"product": "BlackBox_950", "source_sha256": "a" * 64})
    for required in ("have **not** been flashed", "persistence is disabled",
                     "Screen capture currently fails", "Automatic repeat flashing is disarmed",
                     "0xE0000,0xE5000", "GPL does not relicense", "full backup"):
        assert required in text

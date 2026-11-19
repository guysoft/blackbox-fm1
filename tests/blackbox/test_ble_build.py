# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_pinned_ble_sources():
    folder = ROOT / "firmware/third_party/optimist_ble"
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name != "NOTICE.md":
            digest.update(path.relative_to(folder).as_posix().encode() + b"\0"
                          + hashlib.sha256(path.read_bytes()).digest())
    lock = json.loads((ROOT / "docs/reference-lock.json").read_text())
    assert digest.hexdigest() == lock["optimist_ble"]["import_tree_sha256"]
    for name, expected in lock["fm1_rf_cal"]["files"].items():
        assert hashlib.sha256((ROOT / "firmware/third_party/fm1_rf_cal" / name).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("board", ["fm1", "blackbox-v20", "blackbox-v23"])
def test_ble_refuses_uninspected_layout(board):
    result = subprocess.run([sys.executable, "tools/build.py", "--board", board, "--ble"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert "surveyed blackbox-v17" in result.stderr


def test_ble_diagnostic_requires_ble():
    result = subprocess.run([sys.executable, "tools/build.py", "--board", "blackbox-v17", "--ble-diagnostic"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert "--ble-diagnostic requires --ble" in result.stderr


def test_ble_selfcal_requires_ble():
    result = subprocess.run([sys.executable, "tools/build.py", "--board", "blackbox-v17", "--ble-selfcal"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert "--ble-selfcal requires --ble" in result.stderr

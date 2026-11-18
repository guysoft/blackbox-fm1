# SPDX-License-Identifier: GPL-3.0-only
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("source", ["input_test.c", "remote_test.c"])
def test_portable_inputs_and_capture(tmp_path, source):
    exe = tmp_path / "input-test"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Wno-unused-function",
                    "-Wno-unused-variable", "-fsanitize=address,undefined",
                    "-o", str(exe), str(ROOT / "tests/blackbox" / source)], check=True)
    subprocess.run([str(exe)], check=True)


@pytest.mark.parametrize("profile,stock", [
    ("blackbox-v20", "BlackBox_FACTORY_V20.fwsc"),
    ("blackbox-v23", "BlackBox-current.fwsc"),
])
def test_real_loader_packages(tmp_path, profile, stock):
    from blackbox_pkg import PROFILES
    p = PROFILES[profile]
    donor = ROOT / "artifacts/downloads" / stock
    image = ROOT / "build" / profile / "blackbox-fm1-950.fwsc"
    if not donor.exists() or not image.exists():
        pytest.skip("real stock and built target package required; no hardware involved")
    exe = tmp_path / "loader-test"
    subprocess.run(["cc", "-std=c99", "-O1", "-Wno-unused-function",
                    f"-DBB_APP_LO={p['app_lo']}", f"-DBB_APP_HI={p['app_hi']}",
                    "-Ifirmware/bsp/chip", "-o", str(exe),
                    str(ROOT / "tests/blackbox/loader_test.c")], cwd=ROOT, check=True)
    subprocess.run([str(exe), str(donor), str(image)], check=True, timeout=60)

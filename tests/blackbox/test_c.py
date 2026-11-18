# SPDX-License-Identifier: GPL-3.0-only
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("source", ["input_test.c", "remote_test.c", "flash_policy_test.c"])
def test_portable_inputs_and_capture(tmp_path, source):
    exe = tmp_path / "input-test"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Wno-unused-function",
                    "-Wno-unused-variable", "-fsanitize=address,undefined",
                    "-o", str(exe), str(ROOT / "tests/blackbox" / source)], check=True)
    subprocess.run([str(exe)], check=True)


@pytest.mark.parametrize("profile,stock", [
    ("blackbox-v17", "BlackBox-wayback-20250705.fwsc"),
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
    args = [str(exe), str(donor), str(image)]
    saved_dump = ROOT / "artifacts/backups/full-flash-v17-20261118-attempt1/flash-pass-1.bin"
    if profile == "blackbox-v17" and saved_dump.exists():
        args.append(str(saved_dump))
    subprocess.run(args, check=True, timeout=60)


def test_blackbox_boot_only_probes_flash(tmp_path):
    """Compile the actual persist_boot body; forbidden FM-1 helpers are absent."""
    source = (ROOT / "firmware/src/project.c").read_text()
    body = source[source.index("static void persist_boot(void)"):
                  source.index("static int project_used(")]
    (tmp_path / "persist_boot.inc").write_text(body)
    harness = tmp_path / "flash_boot.c"
    harness.write_text("""
#include <assert.h>
#include <stdint.h>
#include "firmware/boards/blackbox/flash_policy.h"
#define BLACKBOX 1
#define FELUCCA_FLASH 1
#define FL_FAR(fn) fn
static uint32_t test_id, restored;
static int flash_ok;
static uint32_t irq_save(void) { return 42; }
static void irq_restore(uint32_t f) { assert(f == 42); restored++; }
static uint32_t fl_jedec_ram(void) { return test_id; }
#include "persist_boot.inc"
int main(void) {
    test_id = 0xEB6014u;
    persist_boot();
    assert(flash_ok && restored == 1);
    test_id = 0xEB6015u;
    persist_boot();
    assert(!flash_ok && restored == 2);
    return 0;
}
""")
    exe = tmp_path / "flash-boot"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{ROOT}",
                    str(harness), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)

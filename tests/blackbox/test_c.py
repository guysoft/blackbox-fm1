# SPDX-License-Identifier: GPL-3.0-only
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("source", ["input_test.c", "remote_test.c", "flash_policy_test.c", "ble_test.c", "rf_cal_test.c"])
def test_portable_inputs_and_capture(tmp_path, source):
    exe = tmp_path / "input-test"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Wno-unused-function",
                    "-Wno-unused-variable", "-fsanitize=address,undefined",
                    "-o", str(exe), str(ROOT / "tests/blackbox" / source)], check=True)
    subprocess.run([str(exe)], check=True)


def test_ble_calibration_from_private_backup(tmp_path):
    dump = ROOT / "artifacts/backups/full-flash-v17-20261118-attempt1/flash-pass-1.bin"
    if not dump.exists():
        pytest.skip("private original V17 backup not available")
    exe = tmp_path / "ble-calibration"
    subprocess.run(["cc", "-std=c99", "-Wno-unused-function",
                    "-o", str(exe), str(ROOT / "tests/blackbox/ble_test.c")], check=True)
    subprocess.run([str(exe), str(dump)], check=True)


@pytest.mark.parametrize("diagnostic", [0, 1])
@pytest.mark.parametrize("selfcal", [0, 1])
def test_ble_boot_diagnostics(tmp_path, diagnostic, selfcal):
    exe = tmp_path / "ble-storage"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Wno-unused-function",
                    "-fsanitize=address,undefined", f"-DBLACKBOX_BLE_DIAGNOSTIC={diagnostic}",
                    f"-DBLACKBOX_BLE_SELFCAL={selfcal}",
                    "-o", str(exe), str(ROOT / "tests/blackbox/ble_storage_test.c")], check=True)
    subprocess.run([str(exe)], check=True)
    dump = ROOT / "artifacts/backups/full-flash-v17-20261118-attempt1/flash-pass-1.bin"
    if dump.exists():
        subprocess.run([str(exe), str(dump)], check=True)


def test_ble_remote_transport_ownership(tmp_path):
    exe = tmp_path / "ble-remote"
    subprocess.run(["cc", "-std=c99", "-DBLACKBOX_BLE=1", "-Wno-unused-function",
                    "-fsanitize=address,undefined", "-o", str(exe),
                    str(ROOT / "tests/blackbox/remote_test.c")], check=True)
    subprocess.run([str(exe)], check=True)


def test_remote_arrival_between_main_and_editor_poll(tmp_path):
    source = (ROOT / "firmware/src/editor.c").read_text()
    (tmp_path / "editor_dispatch.inc").write_text(source[source.index("static int ed_service(void)"):])
    exe = tmp_path / "editor-dispatch"
    subprocess.run(["cc", "-std=c99", "-DBLACKBOX=1", "-DBB_TEST_EDITOR_DISPATCH=1",
                    f"-I{tmp_path}", "-Wno-unused-function", "-fsanitize=address,undefined",
                    "-o", str(exe), str(ROOT / "tests/blackbox/remote_test.c")], check=True)
    subprocess.run([str(exe)], check=True)


def test_ble_synth_ownership(tmp_path):
    generated = ROOT / "build/gen"
    if not (generated / "felucca_tables.h").exists():
        pytest.skip("baseline generated headers required")
    exe = tmp_path / "ble-ownership"
    subprocess.run(["cc", "-O1", "-w", f"-I{generated}", "-Ifirmware/src", "-Ifirmware/bsp/chip",
                    "-o", str(exe), "tests/blackbox/ble_ownership_test.c", "-lm"],
                   cwd=ROOT, check=True)
    subprocess.run([str(exe)], check=True, timeout=30)


def test_ble_boot_does_not_lock_audio_vector(tmp_path):
    source = (ROOT / "firmware/boards/blackbox/ble_radio.h").read_text()
    body = source[source.index("static void bb_ble_attach_boot_irqs(void)"):
                  source.index("static void bb_ble_start(")]
    main = (ROOT / "firmware/src/main.c").read_text()
    assert main.index("bb_ble_boot();") < main.index("audio_init();") < main.index("fm1_guard_lock_top();")
    (tmp_path / "attach.inc").write_text(body)
    harness = tmp_path / "boot.c"
    harness.write_text("""
#include <assert.h>
#include <stdint.h>
static int locked, irqs_off, attached;
static uint32_t fm1__lock(void) { assert(!irqs_off); irqs_off = 1; return 42; }
static void fm1__unlock(uint32_t f) { assert(f == 42); irqs_off = 0; }
static void fm1_guard_lock_top(void) { locked = 1; }
static void ble_hw_wl82_attach(void) { assert(irqs_off && !locked); attached = 1; }
#include "attach.inc"
int main(void) {
    bb_ble_attach_boot_irqs();
    assert(attached && !irqs_off && !locked);
    assert(!locked); /* audio_init may now write its interrupt vector */
    fm1_guard_lock_top();
    assert(locked);
    return 0;
}
""")
    exe = tmp_path / "boot"
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                    str(harness), "-o", str(exe)], check=True)
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

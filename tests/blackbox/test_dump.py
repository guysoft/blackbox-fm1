# SPDX-License-Identifier: GPL-3.0-only
import importlib.util
import struct

import pytest

import blackbox_dump as d


def simulator():
    path = d.REFERENCE.parent / "tests/uboot_sim.py"
    if not path.exists():
        pytest.skip("pinned OpenPocket reference required")
    r = d.load_reference()
    spec = importlib.util.spec_from_file_location("dump_sim", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return r, module


@pytest.mark.parametrize("op", [0xFB01, 0xFB02, 0xFB04, 0xFC12, 0x1234])
def test_flash_mutations_blocked(op):
    class NoCalls:
        def execute(self, *args):
            pytest.fail("forbidden command reached transport")
    guard = d.ReadOnlyTransport(NoCalls())
    with pytest.raises(ValueError, match="REFUSED"):
        guard.execute(op.to_bytes(2, "big").ljust(16, b"\xff"), None, 16)


def test_ram_write_bounds():
    guard = d.ReadOnlyTransport(None)
    for addr in (0, d.LOADER_AT - 1, d.LOADER_AT + d.LOADER_SIZE):
        cdb = b"\xfb\x06" + struct.pack(">IH", addr, 512) + b"\x00" * 8
        with pytest.raises(ValueError):
            guard.execute(cdb, bytes(512), 0)


def test_two_reads_and_return(tmp_path):
    r, sim = simulator()
    path = d.ROOT / "artifacts/downloads/wl82loader-c32b28e.bin"
    if not path.exists():
        pytest.skip("verified RAM loader required")
    loader = path.read_bytes()
    flash = bytes(range(256)) * 4096
    pedal = sim.SimPedal(flash, loader)
    report = d.dump_twice(r, pedal, loader, tmp_path, lambda _: None)
    assert report["matching_reads"] and report["flash_size"] == len(flash)
    assert (tmp_path / "flash-pass-1.bin").read_bytes() == flash
    assert (tmp_path / "flash-pass-2.bin").read_bytes() == flash
    assert pedal.flash == flash and not pedal.writes() and not pedal.erases()
    assert pedal.seen[-1][0] == r.RUN_APP


def test_disconnect_retains_partial_without_run_app(tmp_path):
    r, sim = simulator()
    loader_path = d.ROOT / "artifacts/downloads/wl82loader-c32b28e.bin"
    if not loader_path.exists():
        pytest.skip("verified RAM loader required")
    loader = loader_path.read_bytes()
    pedal = sim.SimPedal(bytes(d.FLASH_SIZE), loader)
    pedal.drop_at = 65
    with pytest.raises(r.DeviceGone):
        d.dump_twice(r, pedal, loader, tmp_path, lambda _: None)
    assert not (tmp_path / "manifest.json").exists()
    assert not pedal.writes() and not pedal.erases()
    assert not any(op == r.RUN_APP for op, _ in pedal.seen)


def test_mismatching_reads_retained_without_run_app(tmp_path):
    r, sim = simulator()
    loader_path = d.ROOT / "artifacts/downloads/wl82loader-c32b28e.bin"
    if not loader_path.exists():
        pytest.skip("verified RAM loader required")
    loader = loader_path.read_bytes()

    class ChangingPedal(sim.SimPedal):
        def execute(self, cdb, out, in_len, timeout=2000):
            result = super().execute(cdb, out, in_len, timeout)
            if int.from_bytes(cdb[:2], "big") == r.READ_FLASH:
                address, size = struct.unpack(">IH", cdb[2:8])
                if address + size == len(self.flash):
                    self.flash[0] ^= 1
            return result

    pedal = ChangingPedal(bytes(d.FLASH_SIZE), loader)
    with pytest.raises(ValueError, match="reads differ"):
        d.dump_twice(r, pedal, loader, tmp_path, lambda _: None)
    assert (tmp_path / "flash-pass-1.bin").exists()
    assert (tmp_path / "flash-pass-2.bin").exists()
    assert not (tmp_path / "manifest.json").exists()
    assert not pedal.writes() and not pedal.erases()
    assert not any(op == r.RUN_APP for op, _ in pedal.seen)

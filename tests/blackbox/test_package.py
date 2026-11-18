# SPDX-License-Identifier: GPL-3.0-only
import struct

import pytest

import blackbox_pkg as bb
import fm1pkg_make as fmt


def fixture(base):
    """Synthetic package, no vendor bytes; exercise both boot-head sizes."""
    flash = bytearray(b"\xff" * 0xA0000)
    blob = fmt.key_blob(0x980F)
    flash[0x200:0x200 + len(blob)] = blob
    top = bytearray(struct.pack("<H", fmt.crc16(fmt.FLASH_HDR)) + fmt.FLASH_HDR)
    top += fmt.entry(0, 0xA0, 0x100, 0, 0, 0, "uboot.boot")
    top += fmt.entry(fmt.crc16(blob), 0x200, len(blob), 2, 0x80, 0, "isd_config.ini")
    top += fmt.entry(0xFFFF, base, 0xFFFFFFFF, 0x81, 0xFF, 0, "app_dir_head")
    top += fmt.entry(0xFFFF, 0xFF000, 4096, 0x12, 1, 0xFFFF, "key_mac")
    for off in range(0, len(top), 32):
        fmt.enc(top, off, 32)
    flash[:len(top)] = top
    block = 0x1120
    area = bytearray(b"\xff" * (block + 68))
    app = bytes.fromhex("04818000") + bytes(4092)
    area[0x120:block] = app
    area[32:64] = fmt.entry(fmt.crc16(app), 0x120, len(app), 0x82, 0xFF, 0, "app.bin")
    area[64:96] = fmt.entry(0xFFFF, 0, len(flash), 0x92, 0x82, 0, "PRCT")
    area[:32] = fmt.entry(fmt.crc16(area[32:block]), 0x02000120, block, 0x83, 0xFF, 0, "app_area_head")
    eq = b"test"
    body = fmt.entry(fmt.crc16(eq), 64, 4, 0x82, 0xFF, 1, "eq_cfg_hw.bin") + eq
    area[block:] = fmt.entry(fmt.crc16(body), 32, 32 + len(body), 0x83, 0xFF, 1, "cfg") + body
    fmt.sfc(area, 0, len(area), 0, 0x980F)
    flash[base:base + len(area)] = area
    return fmt.ufw(bytes(flash), b"FELUCCA-LOADER-1" + bytes(600), "BlackBox_950")


@pytest.mark.parametrize("base", [0x4000, 0x6000])
def test_dynamic_app_base(base):
    p = bb.inspect(fixture(base))
    assert p.app_lo == base
    assert p.app_size == 4096
    assert p.product == "BlackBox_950"


@pytest.mark.parametrize("offset", [0, 90, 1100, 20000])
def test_corruption_rejected(offset):
    raw = bytearray(fixture(0x6000))
    raw[offset] ^= 1
    with pytest.raises(ValueError):
        bb.inspect(raw)


def test_truncation():
    for n in [0, 959, 1024]:
        with pytest.raises(ValueError):
            bb.inspect(bytes(n))


def test_wrong_board():
    p = bb.inspect(fixture(0x6000))
    with pytest.raises(ValueError, match="layout"):
        bb.validate_profile(p, "blackbox-v20")


def test_build_round_trip(monkeypatch):
    raw = fixture(0x6000)
    monkeypatch.setitem(bb.PROFILES, "synthetic", {
        "app_lo": 0x6000, "app_hi": 0xA0000, "stock_product": "BlackBox_950",
        "stock_sha256": bb.hashlib.sha256(raw).hexdigest(),
    })
    app = bytes.fromhex("04818000") + b"new" * 100
    out = bb.build(raw, app, b"FELUCCA-LOADER-1" + bytes(600), "synthetic", "BlackBox_951")
    p, old = bb.inspect(out), bb.inspect(raw)
    assert p.product == "BlackBox_951"
    assert p.flash[:0x6000] == old.flash[:0x6000]
    assert p.area[0x120:0x120 + len(app)] == app
    with pytest.raises(ValueError, match="stock checksum"):
        bb.build(out, app, b"FELUCCA-LOADER-1" + bytes(600), "synthetic", "BlackBox_952")

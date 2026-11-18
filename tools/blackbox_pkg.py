#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Strict offline Blackbox package inspection and stock-derived packaging.

The stock head is retained, not flashed by our loader. V20 and V23 have
different app-area bases. Never infer those from a filename.
"""
import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import fm1pkg_make as fmt

PROFILES = {
    "blackbox-v20": {
        "stock_sha256": "c0fef191b860d3b20f77fc492a24986eef2d12df44bb5e38355684820e26cb08",
        "stock_product": "BlackBox_020", "app_lo": 0x4000, "app_hi": 0xA5000,
    },
    "blackbox-v23": {
        "stock_sha256": "67b087c9bd2aae98f09d63d70a6ab7fbe54826c4389b0dc874a4f183ab84415c",
        "stock_product": "BlackBox_023", "app_lo": 0x6000, "app_hi": 0x9F000,
    },
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def name_of(entry):
    return entry[16:32].split(b"\0")[0].split(b"\xff")[0].decode("ascii")


def entry_at(data, off):
    require(0 <= off <= len(data) - 32, "truncated JLFS entry")
    e = bytes(data[off:off + 32])
    require(fmt.crc16(e[2:]) == int.from_bytes(e[:2], "little"), "JLFS header CRC mismatch")
    return e


def replace_crc(entry, data):
    e = bytearray(entry)
    struct.pack_into("<H", e, 2, fmt.crc16(data))
    struct.pack_into("<H", e, 0, fmt.crc16(e[2:]))
    return e


@dataclass
class Package:
    raw: bytes
    product: str
    logical: bytes
    files: dict
    flash: bytes
    area: bytes
    app_lo: int
    app_hi: int
    app_size: int
    cfg_offset: int

    def report(self):
        return {
            "product": self.product, "sha256": hashlib.sha256(self.raw).hexdigest(),
            "size": len(self.raw), "app_lo": self.app_lo, "app_hi": self.app_hi,
            "app_slot": self.app_size, "chip_key": "0x980f",
            "files": {n: len(d) for n, (_, d) in self.files.items()},
        }


def inspect(raw):
    require(len(raw) >= 0x400 + 20, "package too short")
    product = "".join(chr((raw[i * 48 + 47] - i - 1) & 255)
                      for i in range(20) if raw[i * 48 + 47] != 0x7D)
    require(product.startswith("BlackBox_") and product[9:].isdigit(), "not a BlackBox package")
    logical = b"".join(raw[i * 48:i * 48 + 47] for i in range(20)) + raw[960:]
    hdr = bytearray(logical[:64])
    fmt.enc(hdr, 0, 64)
    hcrc, lcrc, total, count = struct.unpack_from("<HHIH", hdr)
    require(hdr[16:22] == b"AC791N" and fmt.crc16(hdr[2:]) == hcrc, "invalid UFW header")
    require(total == len(logical) and 1 <= count <= 11, "invalid UFW length/count")
    end = 64 + count * 80
    require(end <= 0x400 and fmt.crc16(logical[64:end]) == lcrc, "invalid UFW list CRC")
    files, ranges = {}, []
    for i in range(count):
        e = bytearray(logical[64 + i * 80:144 + i * 80])
        fmt.enc(e, 0, 80)
        typ, _, crc, _, off, size, alloc = struct.unpack_from("<HHHHIII", e)
        name = e[64:].split(b"\0")[0].decode("ascii")
        require(name not in files and off >= 0x400 and size <= total - off and alloc >= size,
                "invalid/duplicate UFW file")
        require(not any(off < b and a < off + size for a, b in ranges), "overlapping UFW files")
        data = logical[off:off + size]
        # Vendor metadata uses another encoding: its recorded CRC is not over
        # these on-wire bytes. Accept it only within an exact pinned stock file.
        if typ in (0, 2, 100, 255):
            require(fmt.crc16(data) == crc, f"{name}: data CRC mismatch")
        else:
            require(hashlib.sha256(raw).hexdigest() in
                    {p["stock_sha256"] for p in PROFILES.values()},
                    f"{name}: opaque metadata requires pinned stock checksum")
        files[name] = (typ, data)
        if size:
            ranges.append((off, off + size))
    require("flash.bin" in files and files["flash.bin"][0] == 0, "missing flash.bin")
    require("ota.bin" in files and files["ota.bin"][0] == 100, "missing ota.bin")
    flash = files["flash.bin"][1]
    require(0x6000 <= len(flash) <= 0xFF000 and len(flash) % 4096 == 0, "invalid flash length")
    top = bytearray(flash[:160])
    for off in range(0, 160, 32):
        fmt.enc(top, off, 32)
    require(fmt.crc16(top[2:32]) == int.from_bytes(top[:2], "little"), "flash header CRC mismatch")
    entries = {name_of(e): e for e in (entry_at(top, off) for off in range(32, 160, 32))}
    require("app_dir_head" in entries and "isd_config.ini" in entries, "missing boot entries")
    base = int.from_bytes(entries["app_dir_head"][4:8], "little")
    require(base in (0x4000, 0x6000), "unknown app base")
    keyent = entries["isd_config.ini"]
    ko = int.from_bytes(keyent[4:8], "little")
    require(ko + 34 <= base, "chip-key blob outside preserved head")
    blob = flash[ko:ko + 34]
    require(fmt.crc16(blob[:32]) == int.from_bytes(blob[32:34], "little"), "chip-key CRC mismatch")
    require(fmt.chipkey_decode(blob) == 0x980F, "unknown chip key")
    area = bytearray(flash[base:])
    fmt.sfc(area, 0, len(area), 0, 0x980F)
    head = entry_at(area, 0)
    block = int.from_bytes(head[8:12], "little")
    require(name_of(head) == "app_area_head" and 0x120 <= block <= len(area) - 64, "invalid app area")
    require(fmt.crc16(area[32:block]) == int.from_bytes(head[2:4], "little"), "app-area CRC mismatch")
    app_size = None
    for off in range(32, 0x120, 32):
        if area[off:off + 32] == b"\xff" * 32:
            break
        e = entry_at(area, off)
        pos, size = struct.unpack_from("<II", e, 4)
        if e[12] == 0x82:
            require(0x120 <= pos and size <= block - pos, "file exceeds app area")
            require(fmt.crc16(area[pos:pos + size]) == int.from_bytes(e[2:4], "little"),
                    f"{name_of(e)}: inner data CRC mismatch")
        if name_of(e) == "app.bin":
            require(pos == 0x120 and e[12] == 0x82, "unsupported app entry")
            app_size = size
        if name_of(e) == "PRCT":
            require(pos == 0 and size == len(flash), "PRCT disagrees with flash length")
    require(app_size is not None, "missing app")
    cfg = entry_at(area, block)
    cfglen = int.from_bytes(cfg[8:12], "little")
    require(name_of(cfg) in ("cfg", "EXT_RESERVED") and 64 <= cfglen <= len(area) - block,
            "invalid trailing directory")
    require(fmt.crc16(area[block + 32:block + cfglen]) == int.from_bytes(cfg[2:4], "little"),
            "trailing directory CRC mismatch")
    return Package(raw, product, logical, files, flash, bytes(area), base, len(flash), app_size, block)


def validate_profile(pkg, profile, stock=False):
    p = PROFILES[profile]
    require((pkg.app_lo, pkg.app_hi) == (p["app_lo"], p["app_hi"]), "profile layout mismatch")
    if stock:
        require(pkg.product == p["stock_product"] and
                hashlib.sha256(pkg.raw).hexdigest() == p["stock_sha256"], "stock checksum mismatch")


def build(stock, app, loader, profile, product):
    pkg = inspect(stock)
    validate_profile(pkg, profile, stock=True)
    require(app[:4] == bytes.fromhex("04818000") and len(app) <= pkg.app_size, "invalid/oversized app")
    require(product.startswith("BlackBox_") and product[9:].isdigit(), "invalid product")
    require(len(loader) >= 512 and b"FELUCCA-LOADER-1" in loader, "unrecognized loader")
    area = bytearray(pkg.area)
    image = app + b"\xff" * (pkg.app_size - len(app))
    area[0x120:0x120 + len(image)] = image
    for off in range(32, 0x120, 32):
        if area[off:off + 32] == b"\xff" * 32:
            break
        e = entry_at(area, off)
        if name_of(e) == "app.bin":
            area[off:off + 32] = replace_crc(e, image)
    area[:32] = replace_crc(area[:32], area[32:pkg.cfg_offset])
    # Alter unused entry-name padding, not configuration or a region address.
    # V20 calls this directory cfg; V23 uses EXT_RESERVED. Hardware acceptance
    # of V23 remains a separate qualification gate.
    inner = bytearray(entry_at(area, pkg.cfg_offset + 32))
    inner[31] ^= 1
    struct.pack_into("<H", inner, 0, fmt.crc16(inner[2:]))
    area[pkg.cfg_offset + 32:pkg.cfg_offset + 64] = inner
    outer = entry_at(area, pkg.cfg_offset)
    n = int.from_bytes(outer[8:12], "little")
    area[pkg.cfg_offset:pkg.cfg_offset + 32] = replace_crc(outer, area[pkg.cfg_offset + 32:pkg.cfg_offset + n])
    # Only the occupied region is SFC-encrypted; trailing stock padding stays unchanged.
    used = pkg.cfg_offset + n
    fmt.sfc(area, 0, used, 0, 0x980F)
    flash = pkg.flash[:pkg.app_lo] + bytes(area[:used]) + pkg.flash[pkg.app_lo + used:]
    raw = fmt.ufw(flash, loader, product)
    validate_profile(inspect(raw), profile)
    require(flash[:pkg.app_lo] == pkg.flash[:pkg.app_lo], "boot head changed")
    return raw


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("package", type=Path)
    a = ap.parse_args()
    try:
        print(json.dumps(inspect(a.package.read_bytes()).report(), indent=2))
    except (ValueError, OSError, UnicodeError, struct.error) as e:
        ap.exit(2, f"REFUSED: {e}\n")


if __name__ == "__main__":
    main()

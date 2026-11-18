#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Full-flash backup through USB ROM + a pinned RAM loader. NO flash writes.

Uses the inspected OpenPocket libusb transport. No restore mode, write option,
automatic reconnect/retry, or automatic MIDI boot-mode entry.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "artifacts/reference/openpocket/tools"
PINS = {
    "uboot_rescue.py": "cb5d3830d2f6dbe390d9bb7a64c5f6b3a06f0e07474a0ab54dec20aa356d4aec",
    "pocketx_fw.py": "33bcc5df22301d780c9f7e0ae5baaf96e55b237ec89ec0a043974f4de0fd87c6",
}
LOADER_SHA = "d41da6126760c9d66660bcc0cac8d27d221806c5e369a8036921efe68dca5376"
FLASH_SIZE = 0x100000
LOADER_AT = 0x1C02000
LOADER_SIZE = 24064


def load_reference():
    for name, sha in PINS.items():
        if hashlib.sha256((REFERENCE / name).read_bytes()).hexdigest() != sha:
            raise ValueError(f"reference changed: {name}")
    sys.path.insert(0, str(REFERENCE))
    return importlib.import_module("uboot_rescue")


class ReadOnlyTransport:
    """Independent last-mile command guard, even if the caller requests writes."""
    def __init__(self, transport):
        self.transport = transport
        self.commands = {}

    def execute(self, cdb, out, in_len, timeout=2000):
        op = int.from_bytes(cdb[:2], "big")
        if cdb == b"\x12\x00\x00\x00\x24\x00":
            allowed = out is None and in_len == 36
        elif op == 0xFB06:  # RAM write, restricted to the verified loader's area
            addr, n = struct.unpack(">IH", cdb[2:8])
            allowed = (out is not None and len(out) == n and in_len == 0 and
                       LOADER_AT <= addr and addr + n <= LOADER_AT + LOADER_SIZE)
        elif op == 0xFB08:  # jump only to the RAM loader
            allowed = (out is None and in_len == 16 and
                       cdb[2:8] == struct.pack(">IH", LOADER_AT, 1))
        elif op == 0xFD05:  # raw flash read
            addr, n = struct.unpack(">IH", cdb[2:8])
            allowed = out is None and 0 < n <= 0x8000 and in_len == n and addr + n <= FLASH_SIZE
        elif op in (0xFC09, 0xFC0A, 0xFC14, 0xFC0C):
            args = {0xFC09: struct.pack(">I", 0xAC6900),
                    0xFC0A: b"", 0xFC14: b"", 0xFC0C: struct.pack(">I", 1)}[op]
            allowed = out is None and in_len == 16 and cdb == (cdb[:2] + args).ljust(16, b"\xff")
        else:
            allowed = False
        if not allowed:
            raise ValueError(f"dump transport REFUSED opcode {op:04X}")
        self.commands[f"{op:04X}"] = self.commands.get(f"{op:04X}", 0) + 1
        return self.transport.execute(cdb, out, in_len, timeout)


def dump_twice(reference, transport, loader, directory, log=print):
    if len(loader) != LOADER_SIZE or hashlib.sha256(loader).hexdigest() != LOADER_SHA:
        raise ValueError("wrong RAM loader")
    directory.mkdir(parents=True, exist_ok=True)
    guard = ReadOnlyTransport(transport)
    dev = reference.Uboot(guard)  # no write window
    chip = reference.attach(dev, loader, log)
    hashes = []
    for attempt in range(1, 3):
        path = directory / f"flash-pass-{attempt}.bin"
        h = hashlib.sha256()
        with path.open("xb") as output:
            for address in range(0, chip.size, chip.io):
                data = dev.flash_read(address, min(chip.io, chip.size - address))
                output.write(data)
                h.update(data)
                if address % 0x10000 == 0:
                    log(f"pass {attempt}: {address:#08x}/{chip.size:#08x}")
            output.flush()
            os.fsync(output.fileno())
        if path.stat().st_size != chip.size:
            raise ValueError("incomplete flash dump")
        hashes.append(h.hexdigest())
        log(f"saved pass {attempt}: {hashes[-1]}")
        dev.keepalive()
    if hashes[0] != hashes[1]:
        raise ValueError("flash reads differ; retained both, no automatic retry")
    report = {
        "scope": "entire physical flash, two matching reads; restore untested",
        "flash_size": chip.size, "flash_jedec": f"0x{chip.flash_id:06x}",
        "chip_key": f"0x{chip.key:04x}", "loader_sha256": LOADER_SHA,
        "dump_sha256": hashes[0], "matching_reads": True,
        "flash_writes_permitted": False, "commands_before_run_app": guard.commands.copy(),
    }
    with (directory / "manifest.json").open("x") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    log("Two complete matching backups saved. Sending RUN_APP to return to stock.")
    dev.run_app()
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="offline prerequisites only; no USB access")
    ap.add_argument("--execute", action="store_true", help="enable ROM/RAM operations, never flash writes")
    ap.add_argument("--loader", type=Path, default=ROOT / "artifacts/downloads/wl82loader-c32b28e.bin")
    ap.add_argument("--output", type=Path)
    ap.add_argument("--wait-seconds", type=float, default=90)
    a = ap.parse_args()
    if not a.check and (not a.execute or a.output is None):
        ap.error("requires --check, or --execute --output NEW_PRIVATE_DIRECTORY")
    if not 1 <= a.wait_seconds <= 300:
        ap.error("wait-seconds must be 1..300")
    r = load_reference()
    loader = r.get_loader(a.loader)
    usb = r.Libusb()
    if a.check:
        print("Reference and RAM loader hashes verified; libusb loaded. No USB device opened.")
        return
    # Create a new run directory exclusively; never overwrite a prior backup.
    a.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    with (a.output / "events.log").open("x", buffering=1) as events:
        def log(text):
            line = f"{time.monotonic():.3f} {text}"
            print(line, flush=True)
            events.write(line + "\n")
        log("DUMP ONLY: no erase/program opcodes permitted. Waiting for USB 4c4a:8057.")
        deadline = time.monotonic() + a.wait_seconds
        transport = None
        try:
            while time.monotonic() < deadline:
                transport = usb.open_pedal()
                if transport:
                    break
                time.sleep(0.05)
            if transport is None:
                raise TimeoutError("USB ROM device not seen; no mode-change commands sent by this tool")
            dump_twice(r, transport, loader, a.output, log)
        except BaseException as e:
            log(f"STOP: {e}; no automatic recovery/retry. Partial files retained.")
            raise
        finally:
            if transport:
                transport.close()


if __name__ == "__main__":
    main()

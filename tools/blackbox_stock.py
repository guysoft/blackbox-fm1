#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only stock preset queries; no writes, preset changes, OTA or reboot.

Protocol reference: Bulrok/mvave-blackbox-linux PROTOCOL.md (GPL-3.0-or-later).
Frame implementation uses the existing project's bitstream codec.
These addresses are protocol objects, NOT raw flash addresses.
"""
import time

from fm1_install import pack7, unpack7

RECORD_SIZE = 92
STATUS = 0x20000000
WORKING = 0x10000000


def read_request(address, length):
    allowed = ((address == STATUS and length == 4) or
               (address == WORKING and length == RECORD_SIZE) or
               (0 <= address < 64 * RECORD_SIZE and address % RECORD_SIZE == 0
                and length == RECORD_SIZE))
    if not allowed:
        raise ValueError("not an allowlisted stock preset/status read")
    frame = (b"\x00\x59\x23\x08\x00\x00\x04" +
             address.to_bytes(4, "little") + length.to_bytes(2, "little") + b"\x00")
    return b"\xf0" + pack7(frame + bytes([~sum(frame[6:]) & 255])) + b"\xf7"


def read_reply(packet, address, length):
    if not packet.startswith(b"\xf0") or not packet.endswith(b"\xf7"):
        return None
    frame = unpack7(packet[1:-1])
    if len(frame) < 7 or frame[:3] != b"\x00\x59\x23" or frame[6] != 4:
        return None
    if len(frame) < 15:
        raise ValueError("truncated stock reply")
    if int.from_bytes(frame[7:11], "little") != address:
        return None
    if (len(frame) != length + 15 or
            int.from_bytes(frame[3:5], "little") != length + 8 or
            int.from_bytes(frame[11:13], "little") != length or
            frame[5] != 0 or frame[13] != 0 or
            (sum(frame[6:]) & 255) != 255):
        raise ValueError("stock reply length/flags/checksum mismatch")
    return frame[14:-1]


def read(link, address, length, timeout=2):
    request = read_request(address, length)
    link.drain()
    if not link.send(request):
        raise ConnectionError("stock read send failed")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        packet = link.read(max(0, deadline - time.monotonic()))
        if packet is None:
            break
        payload = read_reply(packet, address, length)
        if payload is not None:
            return payload
    raise TimeoutError(f"stock read timed out at object {address:#x}")

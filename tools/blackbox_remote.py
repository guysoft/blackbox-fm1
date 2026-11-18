#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Remote panel wire codec/client. Uses serialized requests, never OTA commands."""
import secrets
import time

HEADER = b"\xf0\x7d\x42\x42"
FIELDS = ("uptime_ms", "boots", "audio_halves", "late", "ui_frames",
          "lcd_timeouts", "cpu_q8", "reset_source", "flash_ok")


def encode(cmd, *data):
    if not 1 <= cmd <= 9 or any(not 0 <= b < 128 for b in data):
        raise ValueError("invalid remote frame")
    return HEADER + bytes([cmd, *data, 0xF7])


def decode(pkt, cmd):
    if not pkt.startswith(HEADER + bytes([cmd])) or not pkt.endswith(b"\xf7"):
        return None
    data = pkt[5:-1]
    if not data or any(b >= 128 for b in data):
        raise ValueError("malformed remote reply")
    if data[0]:
        raise ValueError(f"device rejected remote command {cmd}: rc={data[0]}")
    return data[1:]


def u32(data):
    if len(data) != 5 or any(b >= 128 for b in data) or data[4] > 15:
        raise ValueError("invalid u32")
    return sum(b << (7 * i) for i, b in enumerate(data))


def unpack_bytes(data, count):
    out = bytearray()
    while data:
        mask, data = data[0], data[1:]
        n = min(7, count - len(out))
        if not n or len(data) < n or mask >> n:
            raise ValueError("invalid packed screen data")
        out.extend(data[j] | ((mask >> j) & 1) << 7 for j in range(n))
        data = data[n:]
    if len(out) != count:
        raise ValueError("truncated screen data")
    return bytes(out)


class Panel:
    def __init__(self, link, timeout=2.0):
        self.link, self.timeout = link, timeout
        self.token = secrets.randbelow(127) + 1

    def request(self, cmd, *args, hello=False):
        if not self.link.send(encode(cmd, *(() if hello else (self.token,)), *args)):
            raise ConnectionError("remote send failed")
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            pkt = self.link.read(max(0, deadline - time.monotonic()))
            if pkt is None:
                break
            result = decode(pkt, cmd)
            if result is not None:
                return result
        raise TimeoutError(f"remote command {cmd} timed out")

    def hello(self):
        d = self.request(1, self.token, hello=True)
        if len(d) < 18 or d[:2] != bytes([1, self.token]) or d[4:7] != bytes([7, 14, 27]):
            raise ValueError("incompatible remote panel")
        strings = d[17:].split(b"\0")
        if len(strings) != 3 or strings[-1] or len(strings[1]) != 64:
            raise ValueError("missing firmware source fingerprint")
        return {"version": d[0], "width": d[2], "height": d[3],
                "app_lo": u32(d[7:12]), "app_hi": u32(d[12:17]),
                "product": strings[0].decode("ascii"), "source_sha256": strings[1].decode("ascii")}

    def state(self):
        d = self.request(4)
        if len(d) != len(FIELDS) * 5:
            raise ValueError("invalid health reply")
        return dict(zip(FIELDS, (u32(d[i:i + 5]) for i in range(0, len(d), 5))))

    def key(self, key, down):
        if not 0 <= key < 41:
            raise ValueError("invalid key")
        self.request(2, key, int(bool(down)))

    def encoder(self, enc, delta):
        if not 0 <= enc < 7 or not -63 <= delta <= 63:
            raise ValueError("invalid encoder movement")
        self.request(3, enc, delta + 64)

    def screenshot(self):
        self.request(7, 0)
        image = bytearray()
        try:
            for offset in range(0, 120 * 120 * 2, 256):
                d = self.request(7, 1, offset & 127, (offset >> 7) & 127, (offset >> 14) & 127)
                if len(d) < 2:
                    raise ValueError("missing screen chunk length")
                count = d[0] | d[1] << 7
                if count != min(256, 28800 - offset):
                    raise ValueError("wrong screen chunk length")
                image.extend(unpack_bytes(d[2:], count))
        finally:
            self.request(7, 2)
        return bytes(image)


def check_health(before, after):
    """Strict initial health policy; returns evidence, not proof of analog output."""
    for field in ("uptime_ms", "audio_halves", "ui_frames"):
        if after[field] <= before[field]:
            raise ValueError(f"device stalled/reset: {field} did not advance")
    if before["boots"] != after["boots"]:
        raise ValueError("unexpected reboot")
    if after["late"] != before["late"]:
        raise ValueError("audio deadline missed")
    if after["lcd_timeouts"] != before["lcd_timeouts"] or after["lcd_timeouts"]:
        raise ValueError("LCD transport timed out")
    if not after["flash_ok"] or after["cpu_q8"] >= 85 * 256 // 100:
        raise ValueError("flash unsupported or sustained CPU overload")
    return {"runtime": "passed", "physical_display": "not measured", "analog_audio": "not measured"}

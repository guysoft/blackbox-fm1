#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Remote panel wire codec/client. Uses serialized requests, never OTA commands."""
import secrets
import time

HEADER = b"\xf0\x7d\x42\x42"
FIELDS = ("uptime_ms", "boots", "audio_halves", "late", "ui_frames",
          "lcd_timeouts", "cpu_q8", "reset_source", "flash_ok")
BLE_FIELDS = ("state", "calibration_mask", "connected", "midi_ready", "rx_packets",
              "tx_packets", "drops", "event_irqs", "rx_irqs", "bbp_timeouts",
              "spi_timeouts", "vco_found", "max_irq_us", "fault", "rf_sections", "vm_area")
BLE_CAL_FIELDS = ("version", "radio_held", "stage", "read_rc", "read_offset", "read_bytes",
                  "header", "fnv1a", "parse_error", "record_offset", "record_id", "record_length",
                  "expected_crc", "returned_crc", "found_mask", "sfc_con")
BLE_CAL_CONTROL_FIELDS = ("boot_read_rc", "boot_fnv1a", "boot_word0", "boot_word1", "boot_word2",
                          "boot_word3", "app_read_rc", "app_fnv1a", "app_word0", "app_word1",
                          "app_word2", "app_word3", "jedec", "uid_valid", "uid_fnv1a", "selfcal")
BLE_RF_FIELDS = ("version", "selfcal", "scan_rc", "trim_rc", "mid", "bank121", "filter6",
                 "filter10", "filter20", "txlo_i", "txlo_q", "scan_us", "trim_us",
                 "filter_timeouts", "estimator_timeouts", "bbp_timeouts", "breadcrumb",
                 "previous_breadcrumb", "previous_address", "address")


def encode(cmd, *data):
    if not 1 <= cmd <= 12 or any(not 0 <= b < 128 for b in data):
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

    def request(self, cmd, *args, hello=False, read_only=False):
        if read_only and (hello or cmd not in (4, 10, 11, 12)):
            raise ValueError("stateless diagnostics allow STATE/BLE_STATE/BLE_CAL/BLE_RF only")
        auth = () if hello else (0 if read_only else self.token,)
        if not self.link.send(encode(cmd, *auth, *args)):
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

    def state(self, read_only=False):
        d = self.request(4, read_only=read_only)
        if len(d) != len(FIELDS) * 5:
            raise ValueError("invalid health reply")
        return dict(zip(FIELDS, (u32(d[i:i + 5]) for i in range(0, len(d), 5))))

    def key(self, key, down):
        if not 0 <= key < 41:
            raise ValueError("invalid key")
        self.request(2, key, int(bool(down)))

    def ble_state(self, read_only=False):
        """Diagnostics only; state=2 does not establish RF or MIDI reception."""
        d = self.request(10, read_only=read_only)
        if len(d) != len(BLE_FIELDS) * 5:
            raise ValueError("invalid BLE status reply")
        return dict(zip(BLE_FIELDS, (u32(d[i:i + 5]) for i in range(0, len(d), 5))))

    def ble_calibration(self, read_only=False):
        """Boot-time read/parse evidence, without triggering flash or radio operations."""
        d = self.request(11, read_only=read_only)
        if len(d) not in (len(BLE_CAL_FIELDS) * 5, (len(BLE_CAL_FIELDS) + len(BLE_CAL_CONTROL_FIELDS)) * 5):
            raise ValueError("invalid BLE calibration reply")
        fields = BLE_CAL_FIELDS + (BLE_CAL_CONTROL_FIELDS if len(d) == 160 else ())
        result = dict(zip(fields, (u32(d[i:i + 5]) for i in range(0, len(d), 5))))
        if (result["version"], len(d)) not in ((1, 80), (2, 160)):
            raise ValueError("unsupported BLE calibration diagnostics")
        for name in ("read_rc", "boot_read_rc", "app_read_rc"):
            if result.get(name, 0) >= 1 << 31:
                result[name] -= 1 << 32
        return result

    def ble_rf(self, read_only=False):
        d = self.request(12, read_only=read_only)
        if len(d) != len(BLE_RF_FIELDS) * 5:
            raise ValueError("invalid BLE RF reply")
        result = dict(zip(BLE_RF_FIELDS, (u32(d[i:i + 5]) for i in range(0, len(d), 5))))
        if result["version"] != 1:
            raise ValueError("unsupported BLE RF diagnostics")
        for name in ("scan_rc", "trim_rc"):
            if result[name] >= 1 << 31:
                result[name] -= 1 << 32
        return result

    def encoder(self, enc, delta):
        if not 0 <= enc < 7 or not -63 <= delta <= 63:
            raise ValueError("invalid encoder movement")
        self.request(3, enc, delta + 64)

    def screenshot(self):
        self.request(7, 0)
        image = bytearray()
        failure = None
        try:
            for offset in range(0, 120 * 120 * 2, 256):
                d = self.request(7, 1, offset & 127, (offset >> 7) & 127, (offset >> 14) & 127)
                if len(d) < 2:
                    raise ValueError("missing screen chunk length")
                count = d[0] | d[1] << 7
                if count != min(256, 28800 - offset):
                    raise ValueError("wrong screen chunk length")
                image.extend(unpack_bytes(d[2:], count))
        except BaseException as error:
            failure = error
            raise
        finally:
            try:
                self.request(7, 2)
            except Exception as cleanup:
                if failure is None:
                    raise
                failure.add_note(f"screen release also failed: {cleanup}")
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

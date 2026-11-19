# SPDX-License-Identifier: GPL-3.0-only
import pytest

from blackbox_remote import (HEADER, FIELDS, BLE_FIELDS, BLE_CAL_FIELDS, BLE_CAL_CONTROL_FIELDS,
                             BLE_RF_FIELDS, Panel, check_health, decode, encode, u32, unpack_bytes)


def test_codec():
    assert encode(2, 1, 40, 1) == HEADER + bytes([2, 1, 40, 1, 247])
    assert decode(HEADER + bytes([4, 0, 1, 247]), 4) == b"\x01"
    assert decode(b"\xf0\x7d\x46\x4c\x01\xf7", 4) is None
    for bad in [-1, 128]:
        with pytest.raises(ValueError):
            encode(2, bad)
    with pytest.raises(ValueError):
        decode(HEADER + bytes([4, 2, 247]), 4)
    with pytest.raises(ValueError):
        u32(bytes([0, 0, 0, 0, 16]))


def test_screen_unpack():
    assert unpack_bytes(bytes([1, 0, 127]), 2) == bytes([128, 127])
    with pytest.raises(ValueError):
        unpack_bytes(bytes([4, 0, 127]), 2)
    with pytest.raises(ValueError):
        unpack_bytes(bytes([0]), 1)


def test_health():
    a = dict.fromkeys(FIELDS, 0)
    a.update(uptime_ms=1000, boots=1, audio_halves=100, ui_frames=20, flash_ok=1)
    b = dict(a, uptime_ms=2000, audio_halves=200, ui_frames=40)
    assert check_health(a, b)["analog_audio"] == "not measured"
    for k, v in [("uptime_ms", 1), ("boots", 2), ("audio_halves", 100),
                 ("ui_frames", 20), ("late", 1), ("lcd_timeouts", 1),
                 ("flash_ok", 0), ("cpu_q8", 85 * 256 // 100)]:
        with pytest.raises(ValueError):
            check_health(a, dict(b, **{k: v}))


def test_timeout():
    class Silent:
        def send(self, p): return True
        def read(self, timeout): return None
    with pytest.raises(TimeoutError):
        Panel(Silent()).hello()


def test_stateless_ble_diagnostics():
    class Link:
        def send(self, message):
            self.message = message
            assert message[5] == 0
            return True

        def read(self, timeout):
            count = len(FIELDS) if self.message[4] == 4 else len(BLE_FIELDS)
            return HEADER + bytes([self.message[4], 0]) + bytes(count * 5) + b"\xf7"

    panel = Panel(Link())
    assert panel.state(read_only=True) == dict.fromkeys(FIELDS, 0)
    assert panel.ble_state(read_only=True) == dict.fromkeys(BLE_FIELDS, 0)
    with pytest.raises(ValueError, match="diagnostics"):
        panel.request(2, 14, 1, read_only=True)
    with pytest.raises(ValueError, match="diagnostics"):
        panel.request(1, 42, hello=True, read_only=True)


def test_screen_cleanup_preserves_original_failure():
    panel = Panel(None)

    def request(command, *args):
        if args == (0,):
            return b""
        if args == (2,):
            raise ValueError("expired session")
        raise TimeoutError("missing screen chunk")

    panel.request = request
    with pytest.raises(TimeoutError, match="missing screen chunk") as caught:
        panel.screenshot()
    assert caught.value.__notes__ == ["screen release also failed: expired session"]


def test_ble_calibration_diagnostics():
    class Link:
        version = 1
        truncated = False

        def send(self, message):
            assert message == HEADER + bytes([11, 0, 247])
            return True

        def read(self, timeout):
            values = [self.version, 1, 2, 0xFFFFFFFE] + [0] * (len(BLE_CAL_FIELDS) - 4)
            data = bytes((v >> (7 * i)) & 127 for v in values for i in range(5))
            return HEADER + bytes([11, 0]) + (data[:-5] if self.truncated else data) + b"\xf7"

    panel = Panel(Link())
    assert panel.ble_calibration(read_only=True)["read_rc"] == -2
    panel.link.version = 2
    with pytest.raises(ValueError, match="unsupported"):
        panel.ble_calibration(read_only=True)
    panel.link.truncated = True
    with pytest.raises(ValueError, match="invalid"):
        panel.ble_calibration(read_only=True)


@pytest.mark.parametrize("command,fields,method", [
    (11, BLE_CAL_FIELDS + BLE_CAL_CONTROL_FIELDS, "ble_calibration"),
    (12, BLE_RF_FIELDS, "ble_rf"),
])
def test_extended_radio_diagnostics(command, fields, method):
    class Link:
        def send(self, message):
            assert message == HEADER + bytes([command, 0, 247])
            return True

        def read(self, timeout):
            values = dict.fromkeys(fields, 0)
            values["version"] = 2 if command == 11 else 1
            if command == 11:
                values.update(boot_read_rc=0xFFFFFFFE, app_read_rc=0xFFFFFFFF, uid_valid=1)
            else:
                values.update(scan_rc=0xFFFFFFFF, trim_rc=0xFFFFFFFE)
            data = bytes((v >> (7 * i)) & 127 for v in values.values() for i in range(5))
            return HEADER + bytes([command, 0]) + data + b"\xf7"

    result = getattr(Panel(Link()), method)(read_only=True)
    if command == 11:
        assert result["boot_read_rc"] == -2 and result["app_read_rc"] == -1 and result["uid_valid"] == 1
    else:
        assert result["scan_rc"] == -1 and result["trim_rc"] == -2

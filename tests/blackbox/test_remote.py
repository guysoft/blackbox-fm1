# SPDX-License-Identifier: GPL-3.0-only
import pytest

from blackbox_remote import HEADER, FIELDS, Panel, check_health, decode, encode, u32, unpack_bytes


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

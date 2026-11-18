# SPDX-License-Identifier: GPL-3.0-only
import pytest

import blackbox_stock as stock
from fm1_install import pack7, unpack7


def response(address, payload):
    frame = (b"\x00\x59\x23" + (len(payload) + 8).to_bytes(2, "little") +
             b"\x00\x04" + address.to_bytes(4, "little") +
             len(payload).to_bytes(2, "little") + b"\x00" + payload)
    return b"\xf0" + pack7(frame + bytes([~sum(frame[6:]) & 255])) + b"\xf7"


def test_stock_read_frame():
    frame = unpack7(stock.read_request(stock.STATUS, 4)[1:-1])
    assert frame[:7] == b"\x00\x59\x23\x08\x00\x00\x04"
    assert (sum(frame[6:]) & 255) == 255
    for slot in range(64):
        assert unpack7(stock.read_request(slot * 92, 92)[1:-1])[2] == 0x23


@pytest.mark.parametrize("address,length", [
    (0xF0000000, 0), (0xE0000000, 1), (1, 92), (64 * 92, 92),
    (0, 4096), (stock.STATUS, 92), (-92, 92),
])
def test_refuse_other_objects(address, length):
    with pytest.raises(ValueError):
        stock.read_request(address, length)


def test_strict_reply():
    data = bytes(range(92))
    packet = response(92, data)
    assert stock.read_reply(packet, 92, 92) == data
    assert stock.read_reply(packet, 0, 92) is None
    frame = bytearray(unpack7(packet[1:-1]))
    frame[14] ^= 1
    with pytest.raises(ValueError, match="checksum"):
        stock.read_reply(b"\xf0" + pack7(frame) + b"\xf7", 92, 92)
    with pytest.raises(ValueError):
        stock.read_reply(packet, 92, 4)


def test_timeout_sends_only_read():
    class Link:
        sent = []
        def drain(self): pass
        def send(self, packet):
            self.sent.append(packet)
            return True
        def read(self, timeout): return None
    link = Link()
    with pytest.raises(TimeoutError):
        stock.read(link, stock.STATUS, 4)
    assert link.sent == [stock.read_request(stock.STATUS, 4)]

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Scripted USB-MIDI peer for the real host updater. No USB or synth emulation.

Real firmware/loader C is tested separately. These counters/pixels are synthetic.
"""
import queue

import blackbox_remote as remote
import fm1_install as ota


def word(v):
    return bytes((v >> (7 * i)) & 127 for i in range(5))


class Link:
    def __init__(self, device):
        self.device, self.generation = device, device.generation
        self.q, self.closed = queue.Queue(), False

    @property
    def lost(self):
        return not self.device.connected or self.generation != self.device.generation

    def send(self, data):
        if self.lost or self.closed:
            return False
        self.device.receive(data, self)
        return True

    def read(self, timeout):
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self):
        while not self.q.empty():
            self.q.get_nowait()

    def close(self):
        self.closed = True


class SimulatedBlackbox:
    def __init__(self, package, manifest, fault=None):
        self.package, self.manifest, self.fault = package, manifest, fault
        self.generation, self.connected = 0, True
        self.upgrades = self.served = 0
        self.token, self.uptime = 0, 1000
        self.boot("BlackBox_950", "SIM Blackbox")

    def boot(self, identity, name):
        self.identity, self.name = identity, name
        self.generation += 1
        self.reads, self.pending = [], None

    def input_names(self):
        return [self.name] if self.connected else []

    output_names = input_names

    def open(self, inp, out):
        if inp != self.name or out != self.name or not self.connected:
            raise OSError("simulated port absent")
        return Link(self)

    def next_read(self, link):
        if not self.reads:
            return
        addr, count = self.pending = self.reads.pop(0)
        data = bytes([0, 0x59, 0x30, 0, 0, 0, 0]) + addr.to_bytes(4, "little") + count.to_bytes(3, "little")
        data += bytes([~sum(data[6:]) & 255])
        link.q.put(b"\xf0" + ota.pack7(data) + b"\xf7")

    def receive(self, data, link):
        if data == ota.HS_QUERY:
            text = self.identity.encode().ljust(27, b"\0")
            # Match the device's 27-byte identity reply and checksum.
            body = bytes([0, 0x59, 0x11, 27, 0, 0]) + text
            link.q.put(b"\xf0" + ota.pack7(body + bytes([~sum(text) & 255])) + b"\xf7")
        elif data.startswith(remote.HEADER):
            self.remote(data, link)
        elif data == ota.UPGRADE:
            self.upgrades += 1
            finish = ota.FINISH_WRITE if self.identity.startswith("ota-") else ota.FINISH_CHECK
            # Transfer every byte of the validated logical image in both phases.
            self.reads = [(i, min(512, len(self.package.logical) - i))
                          for i in range(0, len(self.package.logical), 512)] + [(finish, 8)]
            self.next_read(link)
        elif self.pending is not None:
            u = ota.unpack7(data[1:-1])
            addr, count = self.pending
            expected = b"success\0" if addr in (ota.FINISH_CHECK, ota.FINISH_WRITE) else self.package.logical[addr:addr + count]
            if u[14:14 + count] != expected:
                raise ValueError("host served wrong package bytes")
            self.served += 1
            if self.fault == "disconnect" and self.served == 3:
                self.connected = False
                return
            if addr == ota.FINISH_CHECK:
                self.boot("ota-BlackBox_950", "SIM Update")
            elif addr == ota.FINISH_WRITE:
                self.boot(self.package.product, "SIM Blackbox")
            else:
                self.next_read(link)

    def remote(self, data, link):
        cmd, args = data[4], data[5:-1]
        payload, rc = b"", 0
        if cmd == 1:
            self.token = args[0]
            h = self.manifest
            source = h["source_sha256"] if self.upgrades else "f" * 64
            if self.fault == "wrong-build" and self.upgrades:
                source = "e" * 64
            payload = bytes([1, self.token, 120, 120, 7, 14, 27])
            payload += word(h["app_lo"]) + word(h["app_hi"])
            payload += self.identity.encode() + b"\0" + source.encode() + b"\0"
        elif not args or args[0] != self.token:
            rc = 2
        elif cmd == 4:
            if self.fault != "stalled":
                self.uptime += 500
            payload = b"".join(word(v) for v in (self.uptime, 1, self.uptime // 3, 0,
                                                self.uptime // 16, 0, 20, 0, 1))
        elif cmd == 7 and args[1] == 1:
            offset = args[2] | args[3] << 7 | args[4] << 14
            count = min(256, 28800 - offset)
            payload = bytes([count & 127, count >> 7])
            for k in range(0, count, 7):
                payload += bytes([0]) + bytes(min(7, count - k))
        link.q.put(remote.HEADER + bytes([cmd, rc]) + payload + b"\xf7")

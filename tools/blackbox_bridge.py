#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional Q mini/USB keyboard routing through the computer host."""
import queue
import time

import mido


def panel_event(message, first_note):
    """Command mode uses panel key edges, not synth MIDI notes."""
    if message.type not in ("note_on", "note_off") or not first_note <= message.note < first_note + 27:
        return None
    down = message.type == "note_on" and message.velocity > 0
    return message.note - first_note + 14, down


def bridge(updater, input_name, first_note=None, seconds=0):
    from blackbox import open_panel, port_key
    matches = [n for n in mido.get_input_names() if port_key(n) == port_key(input_name)]
    if len(matches) != 1:
        raise ValueError("keyboard input must match one exact normalized port")
    keyboard_name = matches[0]
    dev, panel, hello = open_panel(updater)
    incoming, held, channels = queue.Queue(maxsize=1024), set(), set()
    overflow = False
    def receive(message):
        nonlocal overflow
        try:
            incoming.put_nowait(message)
        except queue.Full:
            overflow = True
    start = last_ping = last_ports = time.monotonic()
    try:
        with mido.open_input(keyboard_name, callback=receive):
            print(f"keyboard {keyboard_name} -> {hello['product']}; "
                  f"{'panel keys' if first_note is not None else 'MIDI performance'}; Ctrl-C stops", flush=True)
            while not seconds or time.monotonic() - start < seconds:
                if overflow:
                    raise RuntimeError("keyboard queue overflow; stop and release held inputs")
                now = time.monotonic()
                if now - last_ports >= 0.5:
                    if dev.link.lost or keyboard_name not in mido.get_input_names():
                        raise ConnectionError("keyboard/Blackbox disconnected")
                    last_ports = now
                if now - last_ping >= 0.8:
                    panel.request(5)
                    last_ping = now
                try:
                    message = incoming.get(timeout=0.01)
                except queue.Empty:
                    continue
                if message.type == "sysex":
                    continue  # A keyboard may never inject OTA/editor/flash commands through this bridge.
                if first_note is not None:
                    event = panel_event(message, first_note)
                    if event is not None:
                        panel.key(*event)
                else:
                    if message.type in ("note_on", "note_off"):
                        key = (message.channel, message.note)
                        channels.add(message.channel)
                        if message.type == "note_on" and message.velocity:
                            held.add(key)
                        else:
                            held.discard(key)
                    elif message.type == "control_change":
                        channels.add(message.channel)
                    dev.link.send_midi(bytes(message.bytes()))
    finally:
        try:
            for channel, note in held:
                dev.link.send_midi(bytes([0x80 | channel, note, 0]))
            for channel in channels:
                dev.link.send_midi(bytes([0xB0 | channel, 64, 0]))
            panel.request(6)
        finally:
            dev.link.close()

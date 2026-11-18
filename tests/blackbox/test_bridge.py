# SPDX-License-Identifier: GPL-3.0-only
import mido

from blackbox_bridge import panel_event


def test_panel_note_edges():
    assert panel_event(mido.Message("note_on", note=53, velocity=80), 53) == (14, True)
    assert panel_event(mido.Message("note_on", note=79, velocity=80), 53) == (40, True)
    assert panel_event(mido.Message("note_off", note=53), 53) == (14, False)
    assert panel_event(mido.Message("note_on", note=53, velocity=0), 53) == (14, False)


def test_outside_keys_do_not_wrap():
    for note in (0, 52, 80, 127):
        assert panel_event(mido.Message("note_on", note=note), 53) is None


def test_non_note_is_not_panel_input():
    assert panel_event(mido.Message("control_change", control=1, value=127), 53) is None
    assert panel_event(mido.Message("sysex", data=[0x22, 0x24, 0x35, 0x7F]), 53) is None

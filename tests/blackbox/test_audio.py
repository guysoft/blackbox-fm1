# SPDX-License-Identifier: GPL-3.0-only
import array
import math
import sys
import wave

import pytest

from blackbox_audio import analyze
import blackbox_audio


def wavfile(path, values):
    a = array.array("h", values)
    if sys.byteorder != "little":
        a.byteswap()
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(a.tobytes())


def test_audio_activity(tmp_path):
    p = tmp_path / "sine.wav"
    wavfile(p, [int(3000 * math.sin(i * 2 * math.pi * 440 / 44100)) for i in range(44100)])
    assert -25 < analyze(p)["rms_dbfs"] < -20


@pytest.mark.parametrize("values", [[0] * 44100, [32767] * 44100, [100] * 20])
def test_bad_capture(tmp_path, values):
    p = tmp_path / "bad.wav"
    wavfile(p, values)
    with pytest.raises(ValueError):
        analyze(p)


def test_probe_failure_releases_note_and_process(tmp_path, monkeypatch):
    class Process:
        killed = False
        def poll(self): return 1 if self.killed else None
        def kill(self): self.killed = True
        def wait(self): return 1
    class Link:
        sent = []
        def send_midi(self, data): self.sent.append(data)
    class Panel:
        link = Link()
        def request(self, *args): raise TimeoutError("USB disappeared")
    process, panel = Process(), Panel()
    monkeypatch.setattr(blackbox_audio.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(blackbox_audio.time, "sleep", lambda _: None)
    with pytest.raises(TimeoutError):
        blackbox_audio.record_probe(panel, "synthetic", tmp_path)
    assert panel.link.sent == [bytes([0x90, 69, 32]), bytes([0x80, 69, 0])]
    assert process.killed

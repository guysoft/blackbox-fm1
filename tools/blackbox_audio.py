#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Optional ALSA capture probe and offline PCM checks; no volume/preset writes."""
import array
import math
import subprocess
import sys
import time
import wave


def analyze(path):
    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() not in (1, 2) or wav.getcomptype() != "NONE":
            raise ValueError("audio probe requires mono/stereo PCM16 WAV")
        rate, channels, frames = wav.getframerate(), wav.getnchannels(), wav.getnframes()
        samples = array.array("h", wav.readframes(frames))
    if sys.byteorder != "little":
        samples.byteswap()
    if frames < rate // 2 or len(samples) != frames * channels:
        raise ValueError("audio capture is short/truncated")
    rms = math.sqrt(sum(v * v for v in samples) / len(samples)) / 32768
    clipped = sum(abs(v) >= 32760 for v in samples) / len(samples)
    db = 20 * math.log10(max(rms, 1e-12))
    if db < -70:
        raise ValueError("audio probe silent/below -70 dBFS; do not automatically turn up volume")
    if clipped > 0.001:
        raise ValueError("audio capture clipped")
    return {"rms_dbfs": round(db, 2), "clipped_fraction": clipped, "rate": rate,
            "channels": channels, "frames": frames, "quality": "activity/clipping only; pitch/timbre not verified"}


def record_probe(panel, device, directory):
    """Explicitly enabled low-velocity A4. Always release it; physical master stays authoritative."""
    path = directory / "audio.wav"
    with (directory / "audio-capture.log").open("w") as log:
        process = subprocess.Popen(
            ["arecord", f"--device={device}", "--format=S16_LE", "--channels=2",
             "--rate=44100", "--duration=3", "--file-type=wav", str(path)],
            stdout=log, stderr=subprocess.STDOUT)
        note_on = False
        try:
            time.sleep(0.2)
            if process.poll() is not None:
                raise RuntimeError("audio capture stopped before probe; see audio-capture.log")
            note_on = True
            panel.link.send_midi(bytes([0x90, 69, 32]))
            for _ in range(3):
                time.sleep(0.25)
                panel.request(5)
            panel.link.send_midi(bytes([0x80, 69, 0]))
            note_on = False
            deadline = time.monotonic() + 5
            while process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.25)
                panel.request(5)
            if process.poll() is None:
                raise TimeoutError("audio capture did not finish")
            if process.returncode:
                raise RuntimeError("audio capture failed; see audio-capture.log")
        finally:
            try:
                if note_on:
                    panel.link.send_midi(bytes([0x80, 69, 0]))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    return analyze(path)

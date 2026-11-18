# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import json
from types import SimpleNamespace

import pytest

from blackbox import BoundUpdater, port_key, validate_artifacts, validate_session
import blackbox
from test_package import fixture
import blackbox_pkg as pkg


def test_exact_ports():
    class Backend:
        def input_names(self):
            return ["Felucca:Felucca MIDI 1 28:0", "Q mini 30:0", "Other Felucca 32:0"]
        def output_names(self): return []
    u = BoundUpdater(Backend(), ["Felucca:Felucca MIDI 1"])
    assert u.candidates() == ["Felucca:Felucca MIDI 1 28:0"]
    assert port_key("Felucca:Felucca MIDI 1 29:0") == "Felucca:Felucca MIDI 1"
    with pytest.raises(ValueError, match="output"):
        u.find()


def test_session_fail_closed(tmp_path):
    s = {"board": "blackbox-v23", "armed": True, "expires_at": 200,
         "remaining_flashes": 3, "ports": ["Felucca"], "evidence": {}}
    with pytest.raises(ValueError, match="survey"):
        validate_session(s, "blackbox-v23", now=100)
    for key in ("survey", "backup", "first_flash", "repeat_flash", "recovery"):
        p = tmp_path / key
        p.write_text(f"synthetic {key}")
        s["evidence"][key] = {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    assert validate_session(s, "blackbox-v23", now=100) is s
    with pytest.raises(ValueError, match="expired"):
        validate_session(s, "blackbox-v23", now=201)
    s["remaining_flashes"] = 0
    with pytest.raises(ValueError, match="budget"):
        validate_session(s, "blackbox-v23", now=100)


def test_wrong_manifest(tmp_path, monkeypatch):
    raw = fixture(0x6000)
    monkeypatch.setitem(pkg.PROFILES, "synthetic", {
        "app_lo": 0x6000, "app_hi": 0xA0000,
    })
    p = tmp_path / "p.fwsc"
    p.write_bytes(raw)
    manifest = {"product": "BlackBox_950", "sha256": "0" * 64, "board": "synthetic", "persistence": False}
    with pytest.raises(ValueError, match="manifest"):
        validate_artifacts(p, manifest, "synthetic")


def test_build_failure_disarms_before_midi(tmp_path, monkeypatch):
    s = {"board": "blackbox-v23", "armed": True, "expires_at": blackbox.time.time() + 3600,
         "remaining_flashes": 3, "ports": ["Felucca"], "current_source_sha256": "a" * 64,
         "stock_package": "unused", "evidence": {}}
    for key in ("survey", "backup", "first_flash", "repeat_flash", "recovery"):
        p = tmp_path / key
        p.write_text(f"synthetic test evidence {key}")
        s["evidence"][key] = {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    session = tmp_path / "session.json"
    session.write_text(json.dumps(s))
    monkeypatch.setattr(blackbox, "ROOT", tmp_path)
    def fail(*args): raise RuntimeError("simulated build failure")
    def forbidden(): pytest.fail("MIDI must not open after a build failure")
    monkeypatch.setattr(blackbox, "run_command", fail)
    monkeypatch.setattr(blackbox, "MidiBackend", forbidden)
    with pytest.raises(RuntimeError, match="build failure"):
        blackbox.run_iteration(SimpleNamespace(session=session, build_id=950))
    after = json.loads(session.read_text())
    assert after["armed"] is False and after["remaining_flashes"] == 2
    logs = list((tmp_path / "artifacts/runs").glob("*/events.jsonl"))
    assert len(logs) == 1 and '"session_disarmed": true' in logs[0].read_text()


def test_default_and_write_opt_in_do_not_open_midi(monkeypatch):
    def forbidden(): pytest.fail("unexpected MIDI access")
    monkeypatch.setattr(blackbox, "MidiBackend", forbidden)
    monkeypatch.setattr(blackbox.sys, "argv", ["blackbox.py"])
    assert blackbox.main() == 0
    monkeypatch.setattr(blackbox.sys, "argv", ["blackbox.py", "iterate", "--session", "missing.json"])
    with pytest.raises(SystemExit) as e:
        blackbox.main()
    assert e.value.code == 2

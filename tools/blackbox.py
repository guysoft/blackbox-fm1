#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Blackbox development CLI. No arguments / inspect never opens MIDI.

Real iteration is gated by a hardware-qualified session; no automatic restore.
"""
import argparse
import hashlib
import fcntl
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import blackbox_pkg as pkg
import blackbox_remote as remote
import fm1_install as ota

ROOT = Path(__file__).resolve().parents[1]


class MidiLink(ota.MidoLink):
    def send_midi(self, data):
        self.out.send(self.mido.Message.from_bytes(list(data)))


class MidiBackend(ota.MidoBackend):
    def open(self, in_name, out_name):
        return MidiLink(self, in_name, out_name)


def port_key(name):
    """ALSA client numbers may change on enumeration; never strip device names."""
    return re.sub(r" \d+:\d+$", "", name)


class BoundUpdater(ota.Updater):
    """Use only the exact normalized names observed during qualification."""
    def __init__(self, backend, names):
        super().__init__(backend)
        self.names = set(names)

    def candidates(self, only_port=True):
        return [n for n in self.backend.input_names() if port_key(n) in self.names]

    def check(self, dev, image, step):
        try:
            return super().check(dev, image, step)
        except ota.InstallError as e:
            raise ota.InstallError(e.code, str(e).replace(
                "nothing was written", "application write unconfirmed; OTA staging may already have changed flash")) from e

    def find(self, want=None, only_port=True):
        candidates = self.candidates()
        if len(candidates) > 1:
            raise ValueError("ambiguous target: multiple permitted MIDI inputs")
        for name in candidates:
            outputs = [n for n in self.backend.output_names() if port_key(n) == port_key(name)]
            if len(outputs) != 1:
                raise ValueError("missing/ambiguous exact MIDI output")
            link = self.backend.open(name, outputs[0])
            try:
                identity = ota.handshake(link, 2)
                if identity and identity.model.removeprefix("ota-") == "BlackBox":
                    if want is None or want(identity):
                        return ota.Device(link, identity, name)
            except BaseException:
                link.close()
                raise
            link.close()
        return None


def validate_session(session, board, now=None):
    now = time.time() if now is None else now
    pkg.require(session.get("board") == board and board in pkg.PROFILES, "session/profile mismatch")
    pkg.require(session.get("armed") is True and session.get("expires_at", 0) > now,
                "session is not armed or has expired")
    pkg.require(session["expires_at"] <= now + 86400, "session must expire within 24 hours")
    pkg.require(1 <= session.get("remaining_flashes", 0) <= 20, "flash budget exhausted/invalid")
    pkg.require(isinstance(session.get("ports"), list) and
                1 <= len(session["ports"]) <= 3 and
                all(isinstance(n, str) and n for n in session["ports"]), "missing exact MIDI port names")
    for key in ("survey", "backup", "first_flash", "repeat_flash", "recovery"):
        e = session.get("evidence", {}).get(key, {})
        path = Path(e.get("path", ""))
        pkg.require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == e.get("sha256"),
                    f"missing/changed hardware qualification evidence: {key}")
    return session


def validate_artifacts(package, manifest, board):
    raw = Path(package).read_bytes()
    p = pkg.inspect(raw)
    pkg.validate_profile(p, board)
    pkg.require(p.product == manifest.get("product") and
                hashlib.sha256(raw).hexdigest() == manifest.get("sha256"), "package/manifest mismatch")
    pkg.require(manifest.get("board") == board and manifest.get("persistence") is False,
                "wrong board or unexpected storage migration")
    pkg.require(re.fullmatch(r"BlackBox_9[5-7]\d", p.product) is not None,
                "not a blackbox-fm1 development image")
    pkg.require(b"FELUCCA-LOADER-1" in p.files["ota.bin"][1], "missing project loader")
    pkg.require(re.fullmatch(r"[0-9a-f]{64}", manifest.get("source_sha256", "")) is not None,
                "missing source fingerprint")
    return p


def open_panel(updater):
    dev = updater.find(lambda i: not i.loader)
    if dev is None:
        raise ConnectionError("qualified Blackbox application not found")
    panel = remote.Panel(dev.link)
    try:
        hello = panel.hello()
        pkg.require(hello["product"] == dev.id.text, "identity/remote mismatch")
        return dev, panel, hello
    except BaseException:
        dev.link.close()
        raise


def observe(panel, hello, profile, expected_source, emit, seconds=5, capture=None):
    p = pkg.PROFILES[profile]
    pkg.require((hello["app_lo"], hello["app_hi"]) == (p["app_lo"], p["app_hi"]),
                "device runtime flash map mismatch")
    if expected_source is not None:
        pkg.require(hello["source_sha256"] == expected_source, "device is running another source build")
    before = panel.state()
    emit("health", state=before)
    deadline = time.monotonic() + seconds
    last = before
    while time.monotonic() < deadline:
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))
        state = panel.state()  # heartbeat too
        remote.check_health(last, state)
        emit("health", state=state)
        last = state
    verdict = remote.check_health(before, last)
    if capture:
        pixels = panel.screenshot()
        Path(capture).write_bytes(pixels)
        emit("render_capture", file=str(capture), sha256=hashlib.sha256(pixels).hexdigest(),
             width=120, height=120, format="RGB565 little-endian", physical_display="not measured")
    emit("health_pass", **verdict)
    return verdict


def iteration(updater, p, manifest, emit, run_dir, seconds=5, expected_before=None, audio=None):
    """Real OTA state machine; injectable MIDI backend for offline tests."""
    dev, panel, hello = open_panel(updater)
    try:
        observe(panel, hello, manifest["board"], expected_before, emit, seconds=seconds)
        panel.request(6)
    finally:
        dev.link.close()
    dev = updater.find(lambda i: not i.loader)
    if dev is None:
        raise ConnectionError("device disappeared before flashing")
    pkg.require(dev.id.text == hello["product"], "identity changed before flashing")
    emit("flash_begin", product=p.product, sha256=manifest["sha256"])
    try:
        updater.install(dev, p.logical, p.product,
                        lambda stage, detail=None: emit("ota", stage=stage, detail=detail))
    finally:
        dev.link.close()
    dev, panel, hello = open_panel(updater)
    try:
        pkg.require(hello["product"] == p.product, "wrong firmware after flashing")
        observe(panel, hello, manifest["board"], manifest["source_sha256"], emit,
                seconds=seconds, capture=run_dir / "screen.rgb565")
        if audio:
            from blackbox_audio import record_probe
            pkg.require(audio.get("kind") in ("usb", "analog") and bool(audio.get("device")),
                        "audio capture needs an explicit kind and ALSA device")
            before = panel.state()
            result = record_probe(panel, audio["device"], run_dir)
            remote.check_health(before, panel.state())
            emit("audio_capture", kind=audio["kind"], device=audio["device"], **result)
        else:
            emit("audio_unavailable", reason="no capture device configured; counters are not an audio test")
        panel.request(6)
    finally:
        dev.link.close()


def run_command(command, log):
    with log.open("w") as out:
        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}); see {log}")


def run_iteration(a):
    # One hardware owner per session, even across separate agent processes.
    lock_path = a.session.resolve().with_suffix(".lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_iteration_locked(a)


def run_iteration_locked(a):
    session_path = a.session.resolve()
    session = json.loads(session_path.read_text())
    validate_session(session, session["board"])
    pkg.require(re.fullmatch(r"[0-9a-f]{64}", session.get("current_source_sha256", "")) is not None,
                "session needs the source fingerprint measured on the qualified device")
    # Atomically consume/disarm before any device operation. A crash or interrupt
    # cannot leave a failed session armed. Success re-arms with one fewer flash.
    def save_session():
        temp = session_path.with_suffix(".pending")
        temp.write_text(json.dumps(session, indent=2) + "\n")
        temp.replace(session_path)
    session["armed"] = False
    session["remaining_flashes"] -= 1
    save_session()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    run_dir = ROOT / "artifacts/runs" / stamp
    run_dir.mkdir(parents=True)
    with (run_dir / "events.jsonl").open("a") as events:
        def emit(event, **data):
            row = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **data}
            text = json.dumps(row)
            print(text, flush=True)
            events.write(text + "\n")
            events.flush()
        try:
            board = session["board"]
            stock = session["stock_package"]
            emit("build_begin", board=board)
            run_command([sys.executable, "tools/build.py", "--board", board, "--stock", stock,
                         "--build-id", str(a.build_id)], run_dir / "build.log")
            emit("tests_begin")
            run_command([sys.executable, "-m", "pytest", "-q"], run_dir / "tests.log")
            folder = ROOT / "build" / board
            manifest = json.loads((folder / "manifest.json").read_text())
            package_path = folder / f"blackbox-fm1-{a.build_id}.fwsc"
            p = validate_artifacts(package_path, manifest, board)
            from build import source_sha
            pkg.require(source_sha() == manifest["source_sha256"], "source changed since build")
            (run_dir / "package.fwsc").write_bytes(p.raw)
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            emit("tests_pass", package_sha256=manifest["sha256"])
            updater = BoundUpdater(MidiBackend(), session["ports"])
            iteration(updater, p, manifest, emit, run_dir, seconds=a.health_seconds,
                      expected_before=session["current_source_sha256"], audio=session.get("audio_capture"))
            emit("passed")
            session["armed"] = session["remaining_flashes"] > 0
            session["current_source_sha256"] = manifest["source_sha256"]
            save_session()
        except BaseException as e:
            emit("failed", error=str(e), session_disarmed=True)
            raise
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command")
    inspect = sub.add_parser("inspect", help="offline only; no MIDI access")
    inspect.add_argument("package", type=Path)
    sim = sub.add_parser("simulate", help="offline host update/monitor loop; never opens MIDI")
    sim.add_argument("--board", choices=list(pkg.PROFILES), default="blackbox-v23")
    sim.add_argument("--fault", choices=["stalled", "disconnect", "wrong-build"])
    sub.add_parser("ports", help="list ports; sends no MIDI")
    info = sub.add_parser("info", help="read-only identity; no upgrade commands")
    info.add_argument("--port", required=True, help="exact name (ALSA client number may change)")
    monitor = sub.add_parser("monitor", help="observe our firmware; no flash writes")
    monitor.add_argument("--port", required=True)
    monitor.add_argument("--board", choices=list(pkg.PROFILES), required=True)
    monitor.add_argument("--seconds", type=float, default=10)
    monitor.add_argument("--capture", type=Path)
    monitor.add_argument("--audio-device", help="optional ALSA capture; plays a low-velocity A4, no volume change")
    monitor.add_argument("--audio-kind", choices=["usb", "analog"])
    bridge = sub.add_parser("bridge", help="route Q mini/keyboard MIDI, or panel-key edges; no flash")
    bridge.add_argument("--input", required=True, help="exact keyboard MIDI input")
    bridge.add_argument("--port", required=True, help="exact Blackbox MIDI port")
    bridge.add_argument("--panel-first-note", type=int, help="command mode: first of 27 notes -> FM-1 key 14")
    bridge.add_argument("--seconds", type=float, default=0, help="0 runs until Ctrl-C")
    it = sub.add_parser("iterate", help="build/test/flash/observe once; requires qualified session")
    it.add_argument("--session", type=Path, required=True)
    it.add_argument("--build-id", type=int, default=950)
    it.add_argument("--execute", action="store_true", help="explicitly enable this development flash")
    it.add_argument("--health-seconds", type=float, default=10)
    a = ap.parse_args()
    try:
        if not a.command:
            ap.print_help()
            return 0
        if a.command == "inspect":
            print(json.dumps(pkg.inspect(a.package.read_bytes()).report(), indent=2))
        elif a.command == "simulate":
            from blackbox_sim import SimulatedBlackbox
            folder = ROOT / "build" / a.board
            manifest = json.loads((folder / "manifest.json").read_text())
            p = validate_artifacts(folder / "blackbox-fm1-950.fwsc", manifest, a.board)
            backend = SimulatedBlackbox(p, manifest, a.fault)
            updater = BoundUpdater(backend, ["SIM Blackbox", "SIM Update"])
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            dest = ROOT / "artifacts/runs" / ("sim-" + stamp)
            dest.mkdir(parents=True)
            delays = dict(ota.DELAY)
            ota.DELAY.update(open=0, start=0, reply=0, loader=0, reboot=0, retry=0,
                             poll=0.01, hs=0.02, idle_check=0.1, idle_write=0.1,
                             wait_loader=0.2, wait_reboot=0.2)
            with (dest / "events.jsonl").open("w") as events:
                def emit(event, **data):
                    text = json.dumps({"event": event, "simulated": True, **data})
                    print(text, flush=True)
                    events.write(text + "\n")
                try:
                    iteration(updater, p, manifest, emit, dest, seconds=0.01)
                    emit("passed", physical_display="not measured", analog_audio="not measured")
                except BaseException as e:
                    emit("failed", error=str(e), automatic_retry=False)
                    raise
                finally:
                    ota.DELAY.update(delays)
        elif a.command == "ports":
            backend = MidiBackend()
            print(json.dumps({"inputs": backend.input_names(), "outputs": backend.output_names()}, indent=2))
        elif a.command == "iterate":
            if not a.execute:
                ap.error("iterate requires --execute; no device was opened")
            if not 1 <= a.health_seconds <= 300:
                ap.error("health seconds must be 1..300")
            return run_iteration(a)
        elif a.command == "bridge":
            from blackbox_bridge import bridge
            if a.panel_first_note is not None and not 0 <= a.panel_first_note <= 101:
                ap.error("panel-first-note must be 0..101")
            if a.seconds < 0:
                ap.error("seconds must be nonnegative")
            bridge(BoundUpdater(MidiBackend(), [port_key(a.port)]),
                   a.input, a.panel_first_note, a.seconds)
        else:
            updater = BoundUpdater(MidiBackend(), [port_key(a.port)])
            if a.command == "info":
                dev = updater.find()
                if dev is None: raise ConnectionError("Blackbox not found on the exact port")
                try: print(dev.id.text)
                finally: dev.link.close()
            else:
                if not 1 <= a.seconds <= 3600: ap.error("seconds must be 1..3600")
                dev, panel, hello = open_panel(updater)
                try:
                    print(json.dumps(hello))
                    observe(panel, hello, a.board, None,
                            lambda event, **data: print(json.dumps({"event": event, **data}), flush=True),
                            a.seconds, a.capture)
                    if a.audio_device:
                        from blackbox_audio import record_probe
                        if not a.audio_kind: ap.error("audio-device also needs audio-kind")
                        dest = ROOT / "artifacts/runs" / datetime.now(timezone.utc).strftime("audio-%Y%m%dT%H%M%S.%fZ")
                        dest.mkdir(parents=True)
                        print(json.dumps({"audio_kind": a.audio_kind,
                                          **record_probe(panel, a.audio_device, dest)}))
                finally:
                    try: panel.request(6)
                    finally: dev.link.close()
    except (ValueError, OSError, RuntimeError, TimeoutError, ota.InstallError) as e:
        print(f"STOP: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("STOP: interrupted; no automatic recovery/retry", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

# SPDX-License-Identifier: GPL-3.0-only
import json
from pathlib import Path

import pytest

from blackbox import BoundUpdater, iteration, validate_artifacts
from blackbox_sim import SimulatedBlackbox
import fm1_install as ota

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("fault", [None, "stalled", "disconnect", "wrong-build"])
def test_host_update_loop(tmp_path, monkeypatch, fault):
    folder = ROOT / "build/blackbox-v23"
    if not (folder / "manifest.json").exists():
        pytest.skip("build the Blackbox V23 target first; simulation needs a real validated package")
    manifest = json.loads((folder / "manifest.json").read_text())
    p = validate_artifacts(folder / "blackbox-fm1-950.fwsc", manifest, "blackbox-v23")
    sim = SimulatedBlackbox(p, manifest, fault)
    for key in ota.DELAY:
        monkeypatch.setitem(ota.DELAY, key, 0.01)
    monkeypatch.setitem(ota.DELAY, "reply", 0)
    events = []
    run = lambda: iteration(BoundUpdater(sim, ["SIM Blackbox", "SIM Update"]), p, manifest,
                            lambda event, **data: events.append((event, data)), tmp_path, seconds=0.001)
    if fault:
        with pytest.raises((ValueError, ota.InstallError)):
            run()
        assert sim.upgrades <= 2  # never an automatic retry
        if fault == "stalled":
            assert sim.upgrades == 0
    else:
        run()
        assert sim.upgrades == 2
        assert (tmp_path / "screen.rgb565").stat().st_size == 28800
        assert any(name == "health_pass" for name, _ in events)

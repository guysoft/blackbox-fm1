# blackbox-fm1

Independent port of [Felucca](https://github.com/hugelton/Felucca) to the
M-VAVE ANN BlackBox. GPL-3.0-only; see [upstream credits](CREDITS.md) and
[licensing](LICENSING.md). Not supported by Felucca or M-VAVE.

**Pre-hardware development. No build has been tested on a Blackbox.**
Do not install an FM-1 package on a Blackbox or bypass the hardware-validation gate.

## Goal

One supervised initial install, then a monitored command-line loop:
build → test → validate → flash → reconnect → health check → collect evidence.
Stop on failure, retain every run's logs, and never confuse MIDI identity with
proof of working audio/display or recovery.

The synth runs on the pedal. An Android USB-host companion can supply the full
FM-1 panel, alongside an optional Alesis Q mini. Harbor's UI is a reference;
code reuse is blocked until its licence is clarified.

## Start here

- [Progress and next hardware session](PROGRESS.md)
- [Development and hardware gates](docs/BLACKBOX-DEVELOPMENT.md)
- [Controls and Android companion](docs/BLACKBOX-CONTROLS.md)
- [Remote-panel wire protocol](docs/REMOTE-PANEL.md)
- [Architecture](INTERNALS.md), [rules](RULES.md), [requirements](PRODUCT.md)
- [Original Felucca README](docs/FELUCCA-UPSTREAM.md) and [FM-1 build instructions](BUILDING.md)

Source lives in this repository's root. Local downloads, reference checkouts,
build evidence and private backups belong in `artifacts/` (ignored by Git).
No GitHub repository is created or published automatically.

```sh
make setup     # explicit project-local tooling/dependencies
make baseline
make build BOARD=blackbox-v23
make test
make simulate  # offline; never opens a real MIDI port
```

V20 and V23 need different profiles. The default is for offline development,
**not** an instruction to install V23 or select that profile on your unit.

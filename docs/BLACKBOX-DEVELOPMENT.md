# Blackbox development

## Safety boundary

Hardware is not present yet. Host tests and a target compiler cannot prove safe
flashing, boot, analog output or recovery. The project's default action must not
open a MIDI port or write any flash.

Stock V20 and newer reference projects describe different flash lengths and VM/
factory-bank boundaries. Never choose a layout from the product name alone.
Felucca's FM-1 persistence map overlaps stock Blackbox contents; persistence must
remain disabled for the first bring-up. OTA staging itself also changes flash.
A stock updater package is not a backup of patches, IRs, models or calibration.

Keep the first 0x4000 bytes and the final key/MAC sector untouched. Preserve a
verified stock package and private full dump when a safe read route is available.
Do not promise that USB ROM recovery is always reachable after a valid but hung app.

## Artifacts

`artifacts/reference/`: pinned source references; `downloads/`: original binaries;
`toolchain/`: local compiler; `sdk/`: package-only SDK files; `logs/`: build/test
logs; `runs/`: flash and health evidence; `backups/`: private per-unit data.
None are committed. Track provenance and checksums in docs/reference-lock.json.

## Automatic iteration acceptance

One supervised initial install is allowed, followed by normal repeat flashing
without a new manual approval each time within an explicitly armed session.
Qualification requires actual target identity, expected USB ports, backups,
working software update entry, reconnect and health checks, a successful pilot,
and a tested recovery route. A machine-readable session is not itself evidence.

Each iteration builds and tests before writing, checks the exact package hash/
identity/map, records before/after firmware identity and runtime counters, and
fails closed on timeout, unexpected reset, stalled audio/UI or protocol error.
No automatic restore, retry after interrupted write, partition migration or
factory-data overwrite. A failed run retains all evidence and disarms the loop.

Device counters demonstrate progress, not sound quality. USB capture verifies
the exported stream; an external audio capture verifies physical outputs.
Remote screen snapshots verify rendered pixels, not the physical LCD.
Keep missing measurements explicitly marked unavailable.

## Commands (Linux x86-64)

```sh
make setup                    # explicit pinned local downloads + uv sync --frozen; no system install
make baseline                 # original FM-1 build, never install this on Blackbox
make build BOARD=blackbox-v20  # experimental, offline only
make build BOARD=blackbox-v23
make test
make upstream-test
make simulate                 # full host OTA/monitor state machine on scripted MIDI peer
.venv/bin/python tools/blackbox.py simulate --fault disconnect
```

The simulation transfers every byte through the real host updater, but its
runtime counters/screen are scripted. Separate C tests execute the actual loader
against simulated NOR and both built packages, verifying corruption refusal,
installed-base mismatch refusal, head/data preservation and repeat installation.
The real remote handler has host tests with 20,000 malformed requests under
ASan/UBSan. None of this establishes successful hardware flashing.

When hardware is available, start **read-only**:

```sh
make ports
make info PORT='exact port name from the list'
```

No initial-install command is exposed by this project's CLI yet: profile choice,
full backup feasibility and recovery entry must first be checked on the unit.
The upstream installer is a low-level tool, not a way around this gate.

After supervised installation and qualification:

```sh
make monitor PORT='qualified application MIDI port'
.venv/bin/python tools/blackbox.py monitor --port 'qualified application MIDI port' \
  --board blackbox-v23 --seconds 30 --capture artifacts/screen.rgb565
make iterate SESSION=artifacts/device-session.json
```

Copy docs/session.example.json only after the hardware session, then fill it
from actual measured evidence. Qualification evidence paths refer to saved logs/
backup reports with SHA-256, not self-attested empty markers. Backups must cover
the preserved boot head, factory/calibration/per-unit data and user banks, with
read-back/checksum verification and documented restoration limitations.
Check the actual unit's flash ID against the runtime driver's allowlist.
`current_source_sha256` comes from HELLO on the successfully qualified device.

Arming authorizes at most 20 normal flashes for at most 24 hours; the session
has a process lock, is disarmed atomically before work, and consumes a flash
budget even on failure. A normal successful run re-arms with one fewer flash and
the new measured source fingerprint. Build/test/health failures leave it disarmed.
Only qualified normalized application/loader names are opened; ambiguity fails.
ALSA client numbers can change, but device-name substring matching is forbidden.
This is a single connected target workflow, not per-unit cryptographic identity.

Each run saves events.jsonl, build.log, tests.log, package.fwsc, manifest.json
and screen.rgb565 under artifacts/runs/. The firmware reports its source hash;
the loader checks incoming CRCs and reads back each written sector.

### Optional audio evidence

After choosing the correct capture device on real hardware, add:

```json
"audio_capture": {"kind": "usb", "device": "hw:THE_VERIFIED_CARD,0"}
```

Use kind `analog` only with an external interface wired to the physical output.
The host uses an existing `arecord` executable (never auto-installs it), plays
one low-velocity A4, always releases the note, records PCM16 and checks activity/
clipping. It does not change volume or presets, or verify pitch/timbre.
Silence is a failure, not a reason to turn volume up automatically. The run
retains WAV and capture logs. Without configuration it explicitly reports audio
unavailable rather than passing an audio check.

For an explicitly requested standalone audio probe:

```sh
.venv/bin/python tools/blackbox.py monitor --port 'qualified MIDI port' \
  --board blackbox-v23 --audio-device 'hw:THE_VERIFIED_CARD,0' --audio-kind usb
```

The host must release its USB ports for a phone to become the USB host. A phone
companion and desktop updater cannot both own the same USB device connection.

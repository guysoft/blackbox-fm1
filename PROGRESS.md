# blackbox-fm1 progress

## Status

Host-side bring-up implemented. **No device connected, flashed or hardware-tested.**
Stop here for a read-only device survey before attempting the first installation.

## Milestones

- [x] Own local Git repository, Felucca ancestry retained, branch blackbox-fm1.
- [x] Felucca BSP/engine submodules and local reference checkouts.
- [x] Project requirements, safety rules and artifact layout.
- [x] Reproduce baseline FM-1 build and host tests (98 golden renders unchanged).
- [x] Compile V20/V23 Blackbox targets and host-test board/control/protocol adapters.
- [x] Validate pinned stock packages, distinct boot bases and experimental package boundaries.
- [x] Build/test guarded iteration tools and monitoring on a scripted MIDI peer.
- [x] Real C loader on simulated NOR: corruption/layout refusal, preserve boot head/data, repeat update.
- [x] Remote handler under ASan/UBSan, including 20,000 malformed requests and lease cleanup.
- [x] Reusable porting skill with read-only scenario review; no benchmark improvement claimed.
- [ ] Complete first read-only hardware survey and backup.
- [ ] Supervised first flash; prove subsequent software-only update.
- [ ] Qualify automatic iteration and recovery on actual unit.
- [ ] Android companion (Harbor reuse licence unresolved).

## Evidence

- Source-inspected: both linked Blackbox firmwares use Felucca-derived USB/HAL.
- Source-inspected: 240×240 display; different SPI/audio/input wiring.
- Source-inspected: reference flash maps differ by firmware generation.
- Source-inspected: Harbor panel has seven encoders, fourteen buttons, 27 keys.
- No hardware evidence yet. Build/tests and checksums will be recorded below.

## Implemented

- Pinned local toolchain, uv lockfile, SDK package assets, V20/V23 donor downloads.
- Board adapters: external TX codec, LCD SPI pins/init, direct/ADC-ladder inputs,
  master/battery ADC, long-press reset disable, profile-specific XIP mapping.
- All fourteen logical buttons and seven encoder roles represented through
  physical modifiers/role cycling and the full remote-panel protocol.
- USB update code remains reachable early in startup; normal software update
  entry, runtime health, logical LEDs and 120×120 render capture are compiled in.
- One exact target/loader port set; source hash, bounded session, atomic disarm,
  process lock, no automatic retry or stock restore.
- Optional ALSA audio recording with a low-velocity test note and offline
  activity/clipping checks. No actual audio capture has run.
- Q mini/computer MIDI bridge with optional panel-key command mode, bounded input
  queue, SysEx filtering and disconnect cleanup. Actual keyboard routing untested.

## Limitations / hardware gates

- Both image profiles are experimental, not recommendations for the unit's stock version.
- Persistence and sample writes disabled; first-stage OTA still overwrites
  0xE0000..0xE5000 of the stock sound bank. Backup is mandatory.
- Stock V23 also changes the trailing directory format. Offline packaging
  validates it; acceptance by the vendor's running updater is not yet established.
- Physical LED output/backlight control and codec timing/DMA phase need verification.
- CPU2 is compiled but off by default. Polyphony/performance not measured on Blackbox.
- Render capture is not physical-screen verification. USB sound capture is not
  physical-output verification. Recovery reachability is unknown on this unit.
- No first-flash shortcut or pre-armed hardware session is supplied.
- Android app is not implemented; protocol/backend contract is ready. Harbor
  licence remains unresolved; no Harbor code/artwork copied.

## Validation artifacts

`artifacts/logs/`: setup, baseline build, both target builds, upstream suite,
Blackbox pytest and scripted iteration logs. `artifacts/runs/sim-*`: simulated
events and synthetic screen captures. `build/blackbox-v20/manifest.json` and
`build/blackbox-v23/manifest.json`: package, app, loader and source hashes.
These are generated and ignored by Git; pinned input hashes are tracked in
docs/reference-lock.json.

Host validation includes Blackbox pytest cases for both profile loader
tests, real remote-handler fuzzing, exact-port/session guards, failure disarming,
audio-file validation, keyboard mapping and simulated update failures. The upstream suite passed,
including 98 unchanged golden sound renders; unavailable external reference/
browser-tool checks remain skips, not hardware evidence. Final target rebuilds,
reproducibility checks and suite results are recorded in artifacts/logs/.

## Next hardware session

1. Identify exact Blackbox model, stock version, USB interfaces and flash revision.
2. Preserve stock package, user presets/models/IRs/settings and per-unit data.
3. Determine a safe full-flash read/recovery path without first installing our app.
4. Confirm package/map compatibility, direct stable USB power and recovery assets.
5. First supervised install at low monitoring volume; verify cold boot, USB update
   entry, display, input, MIDI, audio and storage exclusions.
6. Prove a second update without pressing buttons or reconnecting manually.
7. Arm bounded automatic iteration only after its required checks pass.

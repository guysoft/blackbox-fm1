# blackbox-fm1 progress

## Status

Device connected: stock identity **BlackBox_017 (V17)**. USB enumeration and
read-only preset queries are hardware-tested; custom firmware is not installed.
**First custom installation completed:** `BlackBox_950`, V17 profile. Runtime
identity/source hash and execution counters verified, but screen capture failed.
Automatic iteration remains disarmed. User reports visible working UI, PARA
role switching and audible output; screen-capture transport remains broken.
Original full-flash backup is preserved; stock restoration is untested.

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
- [x] Complete hardware survey and full backup via supervised RAM-only reader.
- [ ] Supervised first flash; prove subsequent software-only update.
- [ ] Qualify automatic iteration and recovery on actual unit.
- [ ] Android companion (Harbor reuse licence unresolved).

## Evidence

- Source-inspected: both linked Blackbox firmwares use Felucca-derived USB/HAL.
- Source-inspected: 240×240 display; different SPI/audio/input wiring.
- Source-inspected: reference flash maps differ by firmware generation.
- Source-inspected: Harbor panel has seven encoders, fourteen buttons, 27 keys.
- Hardware-tested: USB `4c4a:c755`, stock identity `BlackBox_017`, MIDI and
  stereo 24-bit/44.1 kHz audio descriptors. Audio operation itself is not tested.
- Hardware-tested: all 64 stock preset records (92 bytes each) read twice with
  matching results; working buffer saved, status unchanged. Reply checksums
  and lengths verified. This is NOT a full flash, model or IR payload backup.

## Connected-device session (2026-11-18)

- Private USB/MIDI/ALSA survey: `artifacts/surveys/20261118T163248Z/`.
- Private preset backup: `artifacts/backups/stock-v17-presets-20261118T163357Z/`.
  Both contain checksum manifests; serial identifiers remain outside Git.
- Added a strictly allowlisted read-only stock preset/status codec in
  `tools/blackbox_stock.py`. No write, preset-change, upgrade or reboot operations.
- Protocol reference inspected: `Bulrok/mvave-blackbox-linux`, tested upstream
  on V20; status and preset reads now verified independently on this V17 unit.
- Exact-version donor located after the initial survey: archived official
  `BlackBox_017`, detailed below. Device flash capacity/JEDEC ID and installed
  boot map are still unmeasured.
- OpenPocket documents a RAM-loader full-flash read in USB ROM mode, primarily
  tested from macOS on crash-looping units. Entering and leaving that mode on
  this healthy V17 unit is not qualified. No UBOOT/reboot command sent.
- No flash writes, upgrades, preset changes or audio probes issued. Automatic
  iteration remains disarmed. Next: establish complete readout/recovery and
  derive a V17 profile from a verified package/dump before supervised install.
- Host suite after adding the stock read codec: **47 pytest cases passed**.
  Existing generated firmware manifests predate these source/document changes;
  the automatic loop must rebuild rather than reuse those packages.

### V17 download and Wine search

- Checked `~/.wine/bottles/`, including `mvave`, and the editor found at
  `~/workspace/music/m-vave/M-EFCS/`. No cached `.fwsc` found; editor
  `userData/amxFiles/` and `irFiles/` are empty. No Wine application launched.
- Official release notes identify V17 as 2025-06-06; today's live link serves
  V23. Wayback CDX lists an archived official binary at `20250705173303`.
- Download: `artifacts/downloads/BlackBox-wayback-20250705.fwsc` (692,244 bytes).
  SHA-256 `fa8e38dadf871c162e51b89d89a36d0117d93adca413a86516ad3f4dbaba9382`.
  SHA-1 matches the archive CDX digest; package identity is `BlackBox_017`.
- Offline parser checks passed for container, flash/app directories and payload
  CRCs. Opaque vendor metadata was accepted only for this exact SHA-256 in an
  in-memory research profile; no build profile or parser allowlist was changed.
- Donor app range `[0x4000,0xA3000)`, chip key `0x980f`. This is package evidence,
  not proof that our custom image works on the connected unit.
- Source URL and inspection details are saved beside the download as
  `BlackBox-wayback-20250705.inspection.json`. Still no flash/reboot commands.
- Official docs mention 80 presets, while the community protocol tool backed up
  slots 0–63. Those 64 records are verified, but total preset coverage is NOT yet
  established; do not call that a complete preset-bank backup.

### User M-EFCS export

- User exported `/home/guy/workspace/music/m-vave/presets-11-2026.abkx`.
  Original left unchanged; private copy and inspection metadata saved to
  `artifacts/backups/mefcs-export-20261118/`.
- Size 7,370 bytes: 80 × 92-byte preset records followed by `PATCHEND\0\0`.
  SHA-256 `72861161d17a519158a9264fdca1e4b3720596a291cde930780b2586b3b80e03`.
- Export records 1–63 (zero-based) match the earlier USB reads exactly.
  Record 0 differs in four bytes; preserve both snapshots, do not overwrite or
  assume which state the user wants. Records 64–79 are present in the export
  but not independently read back over USB.
- This supplies an 80-record preset export, not amp/IR payloads, globals,
  bootloader, calibration or a raw flash backup. Restore remains untested.

### Local IR sources and full-dump option

- User accepts `~/workspace/music/impulse_response/` as their intended set of
  CAB source files, despite the two screenshot names not being located.
  Preserved all 10 files (including `out/` variants) with SHA-256 manifest under
  `artifacts/backups/local-ir-sources-20261118/`; originals unchanged.
- This is user-selected source coverage, NOT verified device-payload equality.
  Do not claim that the V17 package plus presets/IR sources reconstructs every
  factory/per-unit/global byte.
- Inspected OpenPocket's `uboot_rescue.py`: libusb transport is not restricted
  to macOS and Linux already has `libusb-1.0.so.0`. A RAM loader can expose full
  flash reads (FD05); no erase/program permission is needed for that path.
- Actual USB ROM entry/exit and RAM-loader compatibility remain untested on
  this V17 device. Requires a separate supervised mode transition, not an
  automatic flash fallback. No reboot/loader commands have been sent.

### Supervised full-flash backup succeeded

The earlier pending ROM/dump limitations above are superseded by this session.

- User approved proceeding with the supervised ROM/RAM backup operation.
  M-EFCS closed; sent `F0 22 24 35 7D F7` exactly once to the identity-checked
  stock MIDI port. Device enumerated as USB `4c4a:8057`, INQUIRY
  `WL82 UBOOT1.00`. No manual button operation or root access was needed.
- Pinned RAM loader SHA-256
  `d41da6126760c9d66660bcc0cac8d27d221806c5e369a8036921efe68dca5376`.
  Device reported chip key `0x980f`, JEDEC `0xEB6014`, flash size 1,048,576 bytes.
- Two complete flash dumps match SHA-256
  `24aaca6c3eaef7dc7acc9fdfaa62f1428539fca87cc7bc90a9cf7372ff93e350`.
  Files, mode-entry record, logs, manifest and donor comparison are private under
  `artifacts/backups/full-flash-v17-20261118-attempt1/`.
- Independent transport guard blocks erase/program/key-burn commands. RAM writes
  are restricted to the pinned loader's address range. No flash mutations sent.
- RUN_APP returned the unit to USB `4c4a:c755`; identity rechecked as
  `BlackBox_017`. Physical screen/audio confirmation still belongs to the user;
  MIDI identity alone is not that evidence.
- Installed boot-directory base is `0x4000`, matching the archived V17 donor.
  Preserved boot head `[0,0x4000)` matches the donor byte-for-byte. Decrypted
  application payload also matches exactly. Only 31 bytes in the final 32 bytes
  of the donor's app region (`0xA2FE0..0xA3000`) differ; preserve the original
  dump rather than assuming those bytes are disposable.
- `tools/blackbox_dump.py` is dump-only, with no restore option or automatic mode
  entry/retry. Tests cover command blocking, two successful reads, disconnect,
  mismatching reads and no RUN_APP on a failed backup.
- Next: confirm the stock screen is normal, implement an explicitly pinned V17
  build, audit support for this EB flash part (current app allowlist excludes
  it), and host-test before the supervised first install. Do not flash V20/V23.
- Full restore has NOT been exercised; do not claim recovery writes are proven.

### V17 build preparation

- Added the archived V17 donor SHA-256 and explicit profile `[0x4000,0xA3000)`;
  `make build BOARD=blackbox-v17` selects it without changing V20/V23 defaults.
- Added Blackbox-only exact JEDEC recognition for measured `0xEB6014`, retaining
  `0x856014` and `0xB36014`; unknown IDs fail closed in app and update loader.
  SPI opcodes/erase/page geometry remain the unchanged pinned BSP implementation.
  Flash writes on this hardware remain untested.
- Removed FM-1 plaintext-XIP-window setup and user-data/sample scans from
  Blackbox boot, not just writes. Persistence still disabled; OTA staging remains
  destructive to `[0xE0000,0xE5000)` and is covered by the full backup.
- First compile: app 510,624 bytes; RAM 61,856/73,728 bytes; pool
  355,020/368,640 bytes. Final manifests/logs record the rebuilt source fingerprint.
- 60 host tests passed, including V17 loader execution on simulated NOR initialized
  from the actual private flash dump, wrong-chip refusal, and the real
  Blackbox boot function compiled without FM-1 persistence helpers.
- V17 scripted host update/monitor simulation passed. This does not validate
  physical boot, screen, sound or repeat flashing.
- No device commands or installation performed during build preparation.

### First supervised installation (2026-11-18)

- User explicitly authorized install and confirmed MASTER fully down, stock
  screen normal, stable cable/power and M-EFCS closed.
- Revalidated both full-backup hashes, installed stock identity `BlackBox_017`,
  boot-map evidence, build source fingerprint and exact V17 package SHA-256
  `d2279359c149f632e3285ae68de21a63f70ca2ae2b579c5cafc5dad319670006`.
- Single install through stock OTA → our update loader → `BlackBox_950`;
  booted without manual cable/button action. Runtime HELLO reports expected
  `[0x4000,0xA3000)` map and source fingerprint
  `fdf8cfd11e9974c775b26abb8597b109d5e78dbc19dd6fff5a760f9c695db00b`.
- Logs, package and manifest: `artifacts/runs/first-install-v17-20261118/`.
  This is the first actual app/staging flash write; original backups remain intact.
- Hardware runtime evidence: boots=1, advancing uptime/audio-halves/UI frames,
  no audio deadline misses, LCD timeouts=0, flash_ok=1, idle CPU ratio ~34/256
  (~13%). These counters do not establish audible sound or physical LCD quality.
- SCREEN freeze/read timed out; cleanup then received rc=2 (expired remote
  session). Capture NOT passed. No retry/reflash/stock restore automatically run.
- Subsequent read-only HELLO/STATE checks confirm same source, boots still=1
  after ~64 seconds, counters advancing and late/timeouts still=0.
- Next: user screen confirmation, diagnose screenshot transport failure without
  further writes, then audio/input testing. Second software-only update and
  automatic-session arming remain unqualified.

### User confirmation after first install

- User sees the firmware UI working, can cycle virtual knob roles with PARA,
  and hears audio. Record this as user-observed physical display/control/audio
  evidence, not automated audio measurements or exhaustive hardware validation.
- Explained current mapping: PARA click cycles encoder roles; turning changes
  the active value. HOME + right footswitch provides OCT+/Confirm, HOME + left
  provides OCT−/Cancel in dialogs. PARA click is not a generic Enter button.
- No further flash performed. Screenshot capture failure, second software-only
  update and automation qualification remain outstanding.

### Publication / first experimental release

- User authorized publishing the repository and a tagged firmware release.
  Target repository `guysoft/blackbox-fm1`, first tag `v0.1.0-alpha.1`.
- README includes the generated control cheat sheet at
  `docs/blackbox-controls.png`, plus OCT+/Confirm explanation and release links.
- Added SHA-pinned GitHub Actions builds for V17/V20/V23, deterministic V17
  rebuild, host tests and simulated V17 OTA. Successful tag builds publish only
  experimental pre-releases.
- Release assets mirror upstream's `.fwsc`, app and complete corresponding
  source layout, with loader, licences, checksums, manifest and cheat sheet.
  Vendor-donor bytes are explicitly distinguished from GPL source; third-party
  licences retained. No private device files are packaged.
- Complete source includes pinned submodules and a verified fingerprint lock
  so rebuilding an extracted archive does not require Git metadata.
- 64 local tests pass after release-packaging tests. Source and CI changes
  require a fresh build; the exact publication package is not hardware-tested.
- Publishing and CI completion are recorded by GitHub; see docs/RELEASING.md.

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

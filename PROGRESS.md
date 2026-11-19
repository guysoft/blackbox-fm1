# blackbox-fm1 progress

## Status

### Release preparation / companion repository split (2026-11-19)

- User requested steps 1–3 (HELLO fix, CI/assets, version/signing/commit), not a
  release tag or a new hardware flash. Reproduced the HELLO regression in the
  actual C handler first; it failed on the old code.
- Same transport/token HELLO now renews/replies without clearing holds or
  scheduling lost-link cleanup. New-token rollover resets panel holds without
  that asynchronous cleanup; old tokens are rejected. RELEASE/lease expiry
  still schedule BLE MIDI cleanup. Regression covers repeated HELLO, later
  main-loop service/heartbeat, preserved holds/master, token rollover and RELEASE.
  Host-tested only; installed pedal firmware is unchanged.
- Companion moved intact to the sibling repo `guysoft/blackbox-companion-app`
  (public, user-selected name). Its README embeds a real connected-app screenshot
  and links the firmware. Original folder/config/build outputs backed up in the
  ignored `artifacts/backups/android-before-repo-split-20261119.tar.gz`.
  Current Android sources/CI/tests are no longer part of firmware releases.
- User chose experimental development APKs. Package ID retained, versionCode=2,
  versionName=0.2.0-alpha.1. Existing private development key stored as the new
  repo's private Actions secret; never committed or printed. Missing key blocks
  tag publication; test-only PR builds may use an ephemeral debug key.
- Firmware packaging now validates separate USB-only and BLE-selfcal V17 inputs,
  rejects diagnostic/wrong-flag/stale/tampered builds, and includes all imported
  notices/licences. Both variants get manifests/raw components. CI reproducibility
  covers each variant; companion APK/source/signature/checksum assets have
  independent Android CI and tag-only pre-release publication.
- Preparing v0.2.0-alpha.1 metadata. No release tag/publication or device write.

### Android REC + F3 layer shortcut (2026-11-19)

- User could not invoke F + REC. Source/upstream UI tests identify the shortcut
  as REC held + lowest F3: clears the selected track's sequence (not song order).
  Android's default MIDI-note mode did not send physical/logical key events.
- Added automatic panel-key routing while FX/SCL/EDIT/GLO/SEQ/REC is held, retaining
  normal MIDI playing otherwise and the manual Panel keys override. Releases
  use the old route. Existing fingers are suppressed until lifted/freshly
  pressed, so switching routes cannot turn held notes into destructive shortcuts.
- Java tests cover modifier overlap, manual override, release ordering, repeated
  release and old-finger suppression. 87 pytest tests and APK build/lint pass.
- Installed APK without clearing data, SHA-256
  `1f17cc0c72eb9693dc62193180e857b90fe2bf63bfbb0f0a3d9704cb7e8690c4`;
  connected and heartbeats advancing, boots=9/late=12 unchanged, fault/drops=0.
  No REC+F3 command, song erase, volume change or pedal firmware write performed.
  Destructive chord is host-tested only; left connected for the user's test.
- Initial reconnect returned remote rejection rc=2; the next explicit reconnect
  succeeded. An ignored host-only negative control reproduces a separate existing
  firmware bug: duplicate same-token BLE HELLO calls `bb_remote_clear`, schedules
  `bb_ble_io.lost`, and can subsequently clear its newly established panel session.
  No fix flashed (this task was app-only). Fix HELLO idempotence with regression
  coverage before claiming fully reliable Android startup retry behavior.
- Evidence: `artifacts/runs/android-layer-chords-20261119/`.

### Android rotation fix installed (2026-11-19)

- User reported brief working Android control, then failure on rotation.
  Source inspection found activity recreation plus unconditional pause/destroy
  MIDI cleanup. Pedal remained healthy: boots=9, late=12, fault/drops=0.
- MainActivity handles orientation/size configuration changes itself, releases
  old touch holds, and rebuilds portrait/landscape views using the same MIDI
  controller. Keyboard mode, MASTER slider position and status are preserved.
  Actual backgrounding still disconnects; no automatic reconnect introduced.
- Added a source-contract regression plus host shared-finger rotation cleanup
  checks. Java host tests, offline APK build/lint and 87 pytest tests pass.
- Updated APK without data clearing; SHA-256
  `bfac303ce2d31e6a74b3d31701caf0f95ff590e000583f3a68b41fe40557eef1`.
  Four real portrait/landscape switches preserved the activity PID, connected UI,
  MIDI-ready state and ongoing heartbeats; keyboard mode stayed selected.
  No new deadline misses, reboot, queue drops or RF faults.
- Original phone rotation settings restored. Normal MIDI-keyboard mode restored;
  app left foreground, portrait and connected for user testing. No test notes
  played or volume changed. Held-note behavior during actual audible rotation
  remains a user/hardware test, not proven by heartbeats.
- No pedal firmware/calibration writes. Evidence:
  `artifacts/runs/android-rotation-20261119/` (before log, XML/screenshots,
  original settings and per-rotation telemetry).

### Android connected for user testing (2026-11-19)

- Phone reconnected; user requested connecting it to the pedal. App BLE scan
  found the verified peer. First attempt timed out before GATT setup completed.
  Android logs explicitly showed `BluetoothMidiDevice: not ready to send packet
  yet`: MidiManager delivered open ports before the transport could transmit.
- Added a bounded ten-second HELLO-only retry window with the same token, at
  500 ms intervals. No key/encoder/MASTER/note action is retried; controls stay
  disabled until the full identity handshake succeeds. Close cancels retries.
  Removed the app's obsolete "BLE receiver not yet installed" hint.
- Java host tests, offline APK build/lint and all 86 pytest tests pass. Updated
  app with `adb install -r` (no data clearing), APK SHA-256
  `b878efee9f1f13ef0af1ed706d7d4ae71b810c53781bfe9907761726a318a5eb`.
- Selected `Blackbox MIDI 8CE3` in the Android app; status now
  `BlackBox_950 · panel connected · screen unavailable`. USB non-owning telemetry
  confirms connected=1/MIDI-ready=1 and increasing RX/TX during app heartbeats.
  Boots=9/late=12 unchanged, drops/fault=0, runtime healthy.
- Left the app foreground and connected for the user. Did not change volume or
  play notes; Android keyboard/audio tests are for the user next. No firmware,
  calibration or partition writes and no existing pairings removed.
  Evidence: `artifacts/runs/android-ble-connect-20261119/`.

### BLE working on Linux / latest installed state (2026-11-19)

- After crash-based diagnosis and a new supervised authorization, installed
  guard-fix package `db52806d6464aa48fa5ca6f70b7e4514e4b4a0c6dfa1a47d1ab134b1ee32cfb2`,
  source `caad76381e727eca657112d3512b891b919f0174555beb0394282707e551e27b`.
  Build: `BOARD=blackbox-v17 BLE=1 BLE_SELFCAL=1`. No vendor Bluetooth libraries.
- Community RF calibration succeeded: scan/trim return 0, midpoint 55, bank 53,
  filter codes 255/133/57, TX LO 75/60; scan ~44 ms, trim ~109 ms, no RF timeouts.
  Stored-record mask remains 0 because the VM is blank; this is expected for
  self-calibration, not an indication of missing measurements.
- Linux BlueZ received `Blackbox MIDI 8CE3`, discovered standard MIDI service/
  characteristic, and exposed a bidirectional ALSA MIDI port. Full BLE HELLO
  returned the installed source fingerprint; panel key down/up acknowledged.
  MIDI note-on/off and chord/sustain traffic were sent; analog output unmeasured.
- 60-second traffic test: 120 three-note/sustain cycles, zero reported queue drops
  or RF faults, boots=9 unchanged, cumulative late=12 unchanged, LCD timeouts=0.
  Heartbeat RTT (not audio latency): median ~33 ms, p95 ~56 ms, max ~160 ms.
- Disconnect and reconnect with another full HELLO passed. Immediate link-loss
  cleanup remains INCONCLUSIVE: BlueZ disconnect took ~2.5 s, exceeding the
  two-second panel lease. The first harness marked this timing assertion STOP;
  no firmware health failure occurred. A following native D-Bus attempt found a
  removed transient BlueZ object; keeping receiver discovery active resolved it.
  Preserve these failed/inconclusive harness logs; do not call them firmware faults
  or claim prompt voice cleanup/audio silence from the successful reconnect.
- Final USB health: advancing audio/UI, boots=9, late=12 stable, idle CPU ~13%,
  fault=0. Laptop disconnected deliberately to free the peripheral's one link
  for the phone; radio stays enabled and advertising. No pairing removed.
- Evidence: `artifacts/runs/ble-guard-fix-20261119T110652Z/`.
  Host tests at install: 86 passed. No stock restore, partition/calibration write
  or automatic-session arming. Android phone still absent from ADB.
- Remaining: Android app transport, physical sound/display on this build,
  measured note-to-audio latency, prompt link-loss voice cleanup, cold boot and
  longer/range/temperature qualification. This is experimental, not release-ready.

### Community RF trial / identified boot guard bug (2026-11-19)

- User authorized the unique-ID diagnostic followed by one RF pilot if it
  passed, and enabled laptop Bluetooth. Diagnostic source
  `7cbfdc85d47bed852b6e6256214031019a6b60a11cae1614f88d753cd3257d01`
  passed: live nonconstant UID, matching raw boot/app controls, blank-VM
  selection gate, healthy runtime/full capture, and no RF activity.
- RF package `6557dd472d2b67fbfd2626e5d4ad6196b1f935197783f123b071fee5b27c54f8`
  then installed once. Startup crashed and rebooted; the subsequent boot
  suppressed radio (state=3, fault=6). Trial stopped without retry/restore.
- Evidence: `artifacts/runs/ble-community-pilot-20261119T104418Z/`.
  Stable post-stop USB: boots=8, late=11, advancing audio/UI, LCD timeouts=0.
  Per-step calibration results did not survive the reset; no RF reception or
  audio correctness is claimed. A breadcrumb alone is not measurement proof.
- Enabled the existing USB SERIAL preference in RAM via editor MENU_SET;
  reply rc=3 confirms unsaved setting. Blackbox persistence guards forbid its
  flash save. CDC `/dev/ttyACM0` exposed the retained crash without reflashing.
  Only `crash`, `dbg` and bounded RAM `memr` commands were read afterward.
- Crash count=1, vec=1, PC `0x02037690`, DBG `0x2000`, saved r1=`0x01C7FE2C`,
  r2=`0x02000494`: disassembly identifies the preceding store as ALNK0's vector
  write. DBG bit 13 is the top-of-RAM write guard. The BLE adapter prematurely
  locked that guard; main's audio initialization still needed to write vector 11.
  Breadcrumb `0xB10A0D0F` had reached advertising-start, not a calibration timeout.
- Fixed boot-only attachment to leave guard locking to main after audio init.
  Added a host regression executing the actual helper and checking main's order.
  Suppressed boot now initializes diagnostic schema rather than returning an
  all-zero unversioned reply. These fixes are NOT installed yet.
- No further firmware writes until the understood-failure fix is host/target
  tested and the user makes a new supervised trial decision.

### Raw-reader control validation and community adaptation (2026-11-19)

- Continued supervised diagnostic trial after user requested continuing through
  the agreed community-first list. Schema-2 diagnostic package
  `5e0ab7d16368c59efc4b98d0cdc21d623b4ed0ccc516aea2a6bc5dce63e78f85`
  installed source `eff8d5f762c9dbb2e74bd96402af3db2d91a23c6f138fef0f7c3fb4d1870af4e`.
- Raw boot-header and current app-header 32-byte FNVs both match the original
  backup/current package respectively; JEDEC still `0xEB6014`. VM still returns
  the all-FF fingerprint. Strong evidence of absent VM contents, not a general
  read failure; the timing/cause of any erase remains unproven.
- Runtime/full capture passed. Boots=5; late=10 at the first post-update sample,
  unchanged through monitoring (previous build's cumulative count was 9; the
  update/boot interval was unobserved). LCD timeouts=0. No RF enabled.
  Evidence: `artifacts/runs/ble-control-probe-20261119T095520Z/`.
- Added separately pinned verbatim community RF/calibration source headers;
  existing BSP/Optimist pins untouched. Optional BLE_SELFCAL build measures
  trims in RAM, rejects malformed nonblank VM and all calibration errors, and
  uses a live unique ID rather than identical defaults for BLE addresses.
  Host fake-radio tests exercise real source calculations and failure timeouts;
  these are not RF measurements. No self-calibration image installed yet.
- Laptop BlueZ controller is available for advertising/GATT tests; rooted phone
  is still absent from ADB. No tools or system packages installed/upgraded.

### Calibration diagnostic preparation (2026-11-19)

- Added isolated `BLE=1 BLE_DIAGNOSTIC=1` build: reads the same VM sector, but
  compile-time exclusion prevents radio startup even when all records validate.
- USB-only BLE_CAL command 11 reports the boot-time SPI return code/address,
  byte count, header, sector FNV-1a, SFC mode and parser offset/ID/length/CRCs.
  Original strict parser refusal is unchanged; diagnostics never write flash.
- Host tests execute the actual boot reader with read failures, invalid header,
  corrupt tail, valid records and the private original backup, in both modes.
  Initial suite: 79 passed. Target diagnostic build passes RAM/RAM-code checks.
- At preparation, no new firmware had been installed. Pedal MIDI port was
  present; phone absent from ADB. The diagnostic trial below followed.

### Calibration diagnostic hardware result (2026-11-19)

- User confirmed readiness for one supervised diagnostic install. Package
  `38f3dd6a71f0a11c3a63bdbc9bdf3bf7674e826fc0a1e6cdf9be6d03d94a98f3`,
  installed source `1f4c372f15470d152f134291fcd499c9104286080ce726f20246a65259e348ee`.
  No retry, restore, calibration write or RF start was performed.
- All 16 raw-reader calls returned 0, totaling 4096 bytes. Returned header
  `0xFFFFFFFF`, FNV-1a `0x34E76DC5`, matching a completely FF-filled sector's
  fingerprint rather than the original backup. Parser correctly reports bad
  header, found mask 0. This distinguishes parser rejection from a reported
  read failure, but does NOT independently establish that physical flash is
  erased: the SPI helper does not propagate per-byte wait failures.
- Radio-held=1, state=0, RF sections/IRQs=0. Runtime passed 8 seconds plus a full
  28,800-byte capture: boots=4 stable, cumulative late=9 stable, LCD timeouts=0.
  Analog sound and the physical LCD were not measured on this image.
- Evidence: `artifacts/runs/ble-cal-diagnostic-20261119T094608Z/`.
- Inspected fm1-base's BSP pin `2a5af3dfc8bccb92e37d48a3e7e0bf9a5827e51f`:
  `chip/fm1_rf_cal.h` is Apache-2.0 source with bounded waits and per-start
  measurements. Its `fm1_ble_rf.h` hooks differ from our older Onyx hooks;
  dropping the calibration header into this tree alone is not an integration.
  Reference downloads/hashes are private artifacts; no dependency upgraded.
- Offline comparison: this unit's original records 106/107/108 match that
  implementation's SDK board constants. This is one-unit evidence, not a
  blanket default for all Blackboxes.
- Next: validate the raw reader against known non-erased control bytes before
  claiming flash loss; adapt the community self-calibration startup with explicit
  error/timeout gating and host tests. Do not restore stock trims to flash.
  Installed diagnostic image stays radio-disabled. Phone must be reconnected
  to ADB before wireless testing; automatic flashing remains disarmed.

Device surveyed on stock **BlackBox_017 (V17)**; now runs community self-calibrating
BLE **BlackBox_950**. The VM still returns an FF-sector fingerprint, but the
explicit self-calibration variant no longer depends on its stored record 187.
USB runtime, full capture and Linux BLE panel traffic pass.
First install (`BlackBox_950`, V17) had healthy counters and user-confirmed
UI/PARA/audio, but capture failed. The supervised capture-fix update now passes;
the subsequent BLE pilot stopped at its calibration gate (details below).
Automatic iteration remains disarmed.
Original full-flash backup is preserved; stock restoration is untested.

### Latest supervised pilots (2026-11-19)

- User confirmed present, MASTER down, secure USB/power and M-EFCS closed;
  authorized USB-only fix pilot, then BLE only if USB checks passed.
- USB-only package `7a338c38890c0fad37eabafd9725b9228bc350373e30acf6ddd87ee91e4fcac0`
  installed by software update without cable/button intervention. Expected map
  and source `69e0bbfd2852aaf359ff011d1600bd10e3cf1de01e7349afdac0627d653b8b98`
  verified. Three complete 28,800-byte unpaced captures passed, plus another
  before the BLE pilot. Capture ordering/dispatch fix is hardware-tested.
- First post-update late=9, unchanged during all subsequent checks; this .noinit
  counter is cumulative and was not observed during the update itself. Do not
  describe it as zero or claim measured analog audio. Boots advanced 1→2.
- Evidence: `artifacts/runs/usb-capture-fix-pilot-20261119/`.
- BLE package `bd17e7e7ec378619d5db9a6fc9cc4b6b06383c4b4ede5d7e7f03462b4022ecf0`
  then installed once under the same supervised authorization. Expected
  source/map verified; boots=3. BLE_STATE: state=0, calibration_mask=0,
  fault=5, VM address `0xA3000`, RF sections and IRQ counters all zero.
- **STOP:** runtime calibration read/validation failed. Radio never enabled;
  no discovery, pairing, connection, wireless notes or RF latency tested.
  No retry, restore, factory-data write or automatic-session arming followed.
  The original backup still passes the offline parser; the live read needs
  diagnosis. This does not prove the on-device calibration is missing/damaged.
- Post-stop USB health: advancing audio/UI, boots stays 3, late stays 9,
  LCD timeouts=0, idle CPU ~13%. Pedal remains on the BLE-capable image with radio
  safely off. Evidence: `artifacts/runs/ble-first-pilot-20261119/`.
- Next: distinguish SPI read failure from returned-byte/VM validation failure
  using read-only evidence and offline review. Any further pilot needs a new
  supervised decision after the cause is understood; no automatic retry.

## Android controller first implementation (2026-11-18)

- Added original GPL Android app in `android/`; Harbor remains unlicensed in the
  inspected revision, so no source/artwork was copied. No emulator/firmware assets.
- Full logical panel: 14 holdable buttons, seven relative encoders, MASTER
  ceiling, 27-key multitouch implementation, explicit MIDI-note/panel-key modes.
- Android MIDI port-pair selection and BLE-MIDI service discovery/opening;
  HELLO validation, serialized bounded queue, 500 ms idle heartbeat, reply timeout,
  stale-open guards and best-effort note/session cleanup on pause/disconnect.
- Host-tested codec/framing/identity/pointer ownership. APK builds; Android lint
  passes with warnings; existing 64 pytest tests also pass. Installed and UI-tested through Mobile MCP on attached
  Galaxy S10e / Android 15: portrait/landscape, MIDI no-device explanation,
  Nearby Devices permission, BLE scan start/stop (no devices listed), mode toggle
  and disconnected key touch. Exit diagnostics show APK update only, no crash.
- **Not hardware-tested:** USB/BLE MIDI delivery, actual chords, lease/reconnect
  transport behavior, audio/latency. Installed pedal has no BLE receiver. No
  firmware changes/writes; automatic flashing remains disarmed.
- Screen/LED readback and Q mini routing remain absent. Details/build commands
  and honest limits: `android/README.md`.

## Optional BLE integration (2026-11-19)

- User requested BLE integration. Added opt-in V17-only build, isolated at
  `build/blackbox-v17-ble/`; radio is absent from normal builds.
- Pinned Optimist stack and Onyx RF-hook provenance/licences. Board adapters
  retain USB, use BLE IRQs below audio/TIMER5, disable CPU2 only in BLE builds,
  guard storms/overload and suppress RF restart after failed/watchdog boots.
- Located all four RF records in the original dump's VM at `0xA3000`; actual
  private backup passes the firmware parser, including both record CRC layers.
  Dedicated bounded runtime reads, no factory-data writes or private trims in Git.
- BLE notes have separate ownership from USB and physical keys. Host tests cover
  overlapping notes, sustain, disconnect releases and stale queued-note removal.
  BLE panel frames/replies are transport-bound; OTA/editor namespaces are blocked.
  Stateless USB health/radio reads do not steal or refresh a phone's session.
- Initial target compile passed RAM/pool and RAM-code checks. Host suite now
  passes 73 tests, including sanitizer fuzzing, remote transport ownership and
  real synth sources. Validation artifacts: `artifacts/runs/ble-integration-20261119/`.
- Rebuilt unmodified Git HEAD independently: normal FM-1 application and update
  loader are byte-identical to the modified tree's normal FM-1 rebuild.
- **No firmware flashed. No BLE advertisement/connection/audio/latency measured.**
  Existing capture failure and supervised repeat-update gate remain unresolved.
  Onyx's experimental baseband profiles and rail changes were not imported;
  analog startup/clock/channel-map behavior need hardware validation.
- Build, diagnostics, pairing limitations and next gate: `docs/BLACKBOX-BLE.md`.

## Milestones

### Capture failure diagnosis / supervised pilot preparation (2026-11-19)

- Read-only checks confirm the original installed source, boots=1 after ~12.7 h,
  progressing audio/UI, late=0 and LCD timeouts=0. No firmware write or reboot.
- Single tail (128 B) and full-sized (256 B) screen reads succeed. Continuous
  capture drops an entire request intermittently, even with 10 ms spacing.
  Raw MIDI trace contains complete 302-byte replies without parse errors before
  the missing response. Diagnostics/cleanup still work; runtime remains healthy.
- Source-inspected causes: reply published before freeing the RX frame; and
  a remote request arriving after the first remote poll can reach editor's
  non-editor fallback and be consumed by OTA. Blackbox-only fixes release RX
  before sending and claim remote frames at the editor dispatch point.
- Regression tests exercise the real dispatcher with arrival between polls and
  assert RX is released before F7 is visible. Screenshot cleanup now preserves
  the original timeout if releasing the frozen screen also fails. 75 tests pass.
- Evidence: `artifacts/runs/screen-*-diagnosis-20261119/` and
  `artifacts/runs/screen-stream-trace-20261119/`. Firmware fixes not yet installed.
- Next: supervised USB-only fix pilot, full capture and runtime checks; only if
  those pass, a supervised BLE pilot. No automatic session armed, retry or restore.

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
- Published: https://github.com/guysoft/blackbox-fm1/releases/tag/v0.1.0-alpha.1
  at commit `6dacbcca3115c5cc12ffd9d40af4f3ebfebfe7a4`. Branch and tag CI passed
  (runs `44382097802`, `44388058188`). All published asset checksums verified.
- Complete-source archive rebuilt without Git metadata to byte-identical firmware;
  local, GitHub CI and published `.fwsc` all match SHA-256
  `53d7c554e097d4ff56558764b64c65d787f8c69c90a4bd5dbaa9f45972a510a0`.
  Publication did not flash or otherwise operate the connected pedal.

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

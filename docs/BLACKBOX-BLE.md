# Experimental Blackbox BLE-MIDI

**Community self-calibration variant works on the surveyed V17 unit with Linux.**
BlueZ verifies advertising, standard MIDI GATT discovery, full bidirectional
panel HELLO and key messages. A one-minute chord/sustain traffic test and
reconnect passed without runtime faults. Android transport, audible output,
cold boot and prompt link-loss voice cleanup remain unqualified.
Automatic flashing remains disarmed.

## Build

```sh
make build BOARD=blackbox-v17 BLE=1
```

Output: `build/blackbox-v17-ble/`, separate from ordinary V17 builds.
The manifest records `ble: true`, `ble_hardware_tested: false`,
`ble_vm_area: 667648` (`0xA3000`) and `cpu2: false`.
Only the surveyed V17 layout is accepted; BLE is off in every other build.
Identity stays `BlackBox_950`; use the source fingerprint, not identity alone.

## Integration and boundaries

- Optimist pin `fcdc4881e8788365c62ea8be7fa11b4d82966bac`; RF HAL hooks from
  Pocket-Onyx `8ebf3090d8df82a3f5e8806aec964c1e1e9079d1`.
  Licences and exact imported-tree digest are preserved in
  `firmware/third_party/optimist_ble/NOTICE.md` and `docs/reference-lock.json`.
- Board glue: `firmware/boards/blackbox/ble_*.h`. No BSP/engine submodule edits.
  Peripheral-only BLE-MIDI, not Bluetooth audio or Wi-Fi.
- Reads exactly `[0xA3000,0xA4000)` using short RAM-reader windows. This VM sector
  was found in both matching original full dumps. Header, record bounds, CRCs,
  lengths and record 187's inner CRC must pass. Missing/bad calibration refuses
  radio startup. No private trims compiled into shared source; no flash writes.
- Advertises **Blackbox MIDI XXXX**, standard MIDI service, every 250 ms.
  Preferred interval 7.5–11.25 ms; the central chooses the actual interval.
  Stable random-static address/name suffix are derived from this unit's trims.
- IRQ 29/45 run at priority 2, below audio (3) and TIMER5 (4). The imported
  assembly entries call C bodies, never another RTI entry. Storm/queue faults
  stop BLE; a failed/watchdog boot suppresses the next radio startup.
- Second-core support is omitted only in this experimental BLE build.
- Uses Optimist's baseband driver, **not** Onyx's experimental window/channel-map
  profiles. The adapter uses Onyx-derived VCO divider/bank measurements,
  conservative reference-dependent waits, LUT hooks and final measured-bank
  latch. Supply-rail experiments and Pocket AMP flash maps are not copied.
  RF startup, analog trim completeness, clock accuracy and channel-map behavior
  remain hardware risks.

## MIDI and panel

BLE IRQ → bounded ring → TIMER5 (up to eight packets/tick) → existing audio MIDI
queue, source 3. Channel voice messages use a separate 16-channel ownership bank
but the same routing/synth. USB and physical keys can hold the same note.
Disconnect, unsubscribe, panel RELEASE/lease expiry and overload release BLE
sustain/notes in audio context. Queued pre-loss BLE notes are discarded without
discarding USB traffic. Part bend/modulation remain shared, last-controller-wins.
No timestamp jitter buffer, BLE clock/transport input or synth-note output
forwarding is implemented in this first integration.

BLE SysEx is separately bounded and accepts only remote-panel `7D 42 42` frames.
It never reaches the USB ROM-entry, OTA or editor parser. Replies return over
their originating link. One panel owner across USB/BLE: another transport's
HELLO returns rc=5 (busy). BLE SCREEN returns rc=3; no screen traffic on the note
link. Android's existing backend speaks this protocol unchanged.

Peripheral pairing/encryption is supported; keys remain in RAM only. After pedal
power loss the phone may need to forget its old pairing. Just Works is not
authenticated/MITM-resistant: this is experimental nearby control, not a secure
administration channel.

## Non-owning USB diagnostics

In BLE builds only, STATE (4) and BLE_STATE (10) accept token zero over USB,
without HELLO. These reads neither take ownership nor renew the phone's lease:

```python
from blackbox import BoundUpdater, MidiBackend
from blackbox_remote import Panel

device = BoundUpdater(MidiBackend(), ["Felucca:Felucca MIDI 1"]).find()
if device is None:
    raise RuntimeError("Expected Blackbox MIDI port absent")
try:
    panel = Panel(device.link)
    print(panel.state(read_only=True))
    print(panel.ble_state(read_only=True))
finally:
    device.link.close()
```

BLE_STATE's sixteen u32s: state, calibration mask, connected, MIDI ready, RX/TX
packet counters, drops, event/RX IRQ counters, BBP/SPI timeouts, upstream VCO
result, max IRQ microseconds, fault, RF section mask, VM address.
State: 0 not started, 1 starting, 2 enabled, 3 failed/suppressed.
Fault: 0 none, 1 queue, 2 RF operation, 3 IRQ storm, 4 board VCO search,
5 flash/calibration, 6 previous failed/watchdog boot.
`state=2` is not proof of RF reception. `vco_found` is the upstream search's
result, not a sensitivity measurement.
In self-calibration builds the legacy `vco_found` can remain zero: use BLE_RF's
scan result instead. Stored calibration mask can likewise remain zero with a
blank VM; measured trims and stored-record discovery are separate evidence.

### Calibration-only build

`make build BOARD=blackbox-v17 BLE=1 BLE_DIAGNOSTIC=1` produces the isolated
`build/blackbox-v17-ble-diagnostic/` package. The manifest records
`ble_diagnostic: true` and `ble_radio_enabled: false`. It reads/parses the same
bounded VM sector but cannot call radio startup, even with valid calibration.
This is not an installation command.

USB command 11, BLE_CAL, returns sixteen u32s without acquiring a panel lease:
`Panel(device.link).ble_calibration(read_only=True)`. Replies describe the
boot-time snapshot only; requesting diagnostics performs no new flash/RF access.
It is refused over BLE.

Fields: schema version (1), radio held, stage, signed SPI return code, last read
address, successful byte count, little-endian VM header, FNV-1a of successfully
read bytes, parser error, record offset/ID/length, expected/returned CRC,
validated-record mask, SFC control register before the last read.
Stage: 1 unavailable flash, 2 read failure, 3 parser failure, 4 valid set.
Parser error: 1 header/arguments, 2 bounds, 3 record CRC, 4 RF record length,
5 inner 187 CRC, 6 missing records, 0 success. The found mask is diagnostic only:
a corrupt trailing record still rejects the entire set. FNV-1a is a lightweight
comparison aid, not a cryptographic proof of sector identity.

Schema 2 appends sixteen u32s: boot read return code/FNV/first four words,
app read return code/FNV/first four words, JEDEC, valid unique-ID flag,
unique-ID FNV, self-calibration selection. Boot/app fingerprints cover 32 raw
SPI bytes at 0 and `BB_APP_LO`, respectively. The host accepts schema 1 or 2.

### Explicit community self-calibration trial

`make build BOARD=blackbox-v17 BLE=1 BLE_SELFCAL=1` uses the pinned source-only
RF headers in `firmware/third_party/fm1_rf_cal/`, without changing the BSP
submodule or the Optimist stack. Output is `build/blackbox-v17-ble-selfcal/`.
Adding `BLE_DIAGNOSTIC=1` makes a separate radio-disabled image, which checks
the flash unique ID and selection gates but does not run RF calibration.

This is an explicit alternative build, not an automatic fallback on failure.
A valid stored set retains its 106/107/108 values; an entirely FF-filled VM may
use the SDK board constants that match this V17 unit's original backup.
A malformed nonblank VM still stops. The measured 187 and all radio trims stay
in RAM, never written to flash. A nonconstant flash unique ID is required for
the random-static BLE address; defaults must not give every pedal one address.

Upstream's bounded VCO scan, RX filter, TX LO and RX DC measurements run at the
proper points in RF startup. Default TX IQ/DC values remain neutral as in the
upstream minimal BLE calibration. Any scan/trim error, fallback midbank, BBP/SPI
timeout or missing measurement refuses advertising (fault 7). IRQ vectors are
attached with IRQs disabled during boot; the existing main routine locks the
top guard only after audio installs its vector. Locking it inside BLE startup
is incorrect here (unlike a runtime radio toggle).

USB-only BLE_RF (12), `Panel.ble_rf(read_only=True)`, reports schema 1 and:
selfcal, signed scan/trim return codes, midpoint/bank, three filter codes,
TX LO I/Q, scan/trim microseconds, filter/estimator/BBP timeouts, current/previous
breadcrumb, previous/current register address. It is a fixed startup snapshot
plus breadcrumbs, not an RF command.

## Evidence and next gate

Host tests execute real calibration/codec, remote handler and synth ownership
code, including sanitizer fuzzing and the actual private backup. No hardware
radio, latency or audio claims follow from them.

Read-only tracing found intermittent whole-request loss, while individual screen
chunks and runtime health checks pass. Regression tests expose remote/editor/OTA
dispatch and reply-before-RX-release ordering bugs; the Blackbox builds include
fixes, subsequently hardware-verified by complete unpaced captures.

The supervised USB-only fix pilot passed three full captures, plus one before
the BLE install. The BLE pilot then returned calibration_mask=0/fault=5, with
no RF operations or interrupts; the trial stopped. Backup parser success does
not establish the contents returned by the live SPI reader. Distinguish read
errors from validation errors before requesting a new supervised pilot.

The following supervised radio-disabled diagnostic trial read all 4096 bytes
with return code 0, header `0xFFFFFFFF` and FNV-1a `0x34E76DC5` (the fingerprint
of 4096 FF bytes). The parser rejects the header correctly. Runtime/capture
passed with boots=4, late=9 unchanged and no LCD timeout. Because the SPI helper
does not propagate its per-byte wait failures, a known non-erased control read
is still needed before concluding that flash contents were erased.

After startup is resolved, verify USB source/layout/health, BLE advertisement/discovery,
bidirectional HELLO, controls, chords/sustain/disconnect and measured audio.
Compare latency with USB. Stop on failures; no blind retries, automatic stock
restore, partition changes or factory-data writes.

2026-11-19 result: the understood vector-guard fix passed a new supervised pilot.
BLE_RF scan/trim return 0, no calibration timeouts; Linux receives advertising
and exchanges full panel replies through BlueZ's ALSA MIDI port.
Evidence: `artifacts/runs/ble-guard-fix-20261119T110652Z/`. The 60-second test
reported zero drops, no new audio deadline misses or reboot. Command RTT median
~33 ms/p95 ~56 ms/max ~160 ms is not note-to-audio latency.
BlueZ link disconnect took ~2.5 seconds; this test cannot separate immediate
disconnect cleanup from the two-second panel lease. Reconnect/full HELLO passed.
The laptop was disconnected afterward to free the single peripheral link.

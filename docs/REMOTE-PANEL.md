# Blackbox remote panel protocol v1

Optional BLE transport and command 10/11 diagnostics:
[BLACKBOX-BLE.md](BLACKBOX-BLE.md). USB/BLE share one panel owner; BLE never
forwards SysEx to OTA/editor. USB token-zero diagnostic reads in BLE builds
do not acquire/refresh the panel session.

Experimental, host-tested; not hardware-qualified. Uses USB MIDI SysEx,
independent of Felucca's existing editor and OTA namespaces.

Request: `F0 7D 42 42 command arguments F7`.
In BLE-capable builds, retrying HELLO with the same transport/token is idempotent:
it renews the lease and returns identity without clearing held inputs or scheduling
link-loss cleanup. A new token on that transport resets panel holds but keeps the
MIDI link; another transport cannot steal an active session. RELEASE/lease expiry
still request BLE MIDI cleanup.
Reply: same header/command, then `rc`, payload, `F7`.
Every data byte is 7-bit. `rc`: 0 OK, 1 arguments, 2 missing/wrong session,
3 unavailable screen, 4 unknown command, 5 owner busy (BLE builds).
Serialize requests; do not pipeline.
Unrelated messages (editor pushes, MIDI notes) are not replies.

| Command | Arguments | Reply payload |
| --- | --- | --- |
| 1 HELLO | token 1..127 | version=1, token, width=120, height=120, encoders=7, buttons=14, keys=27, app_lo u32, app_hi u32, product NUL, source SHA-256 ASCII NUL |
| 2 KEY | token, ID 0..40, down 0/1 | empty |
| 3 ENCODER | token, raw encoder ID 0..6, delta+64 (1..127) | empty |
| 4 STATE | token | nine u32 fields below |
| 5 PING | token | empty |
| 6 RELEASE | token | empty; ends session |
| 7 SCREEN | token, op 0 freeze / 2 release | empty |
| 7 SCREEN | token, op 1, byte offset u21 | byte count u14, pack7 bytes (up to 256) |
| 8 LEDS | token | 41 logical brightness bytes, 0..127 |
| 9 MASTER | token, own 0/1, value u14 (0..1023) | empty |

u14/u21/u32: 2/3/5 bytes, least-significant seven bits first. u32's final byte
is at most 15. pack7: a top-bit mask followed by up to seven low-seven-bit bytes;
mask bit j is bit 7 of byte j. Unused mask bits must be zero.

STATE: uptime_ms, boots, audio_halves, late, ui_frames, lcd_timeouts, cpu_q8,
reset_source, flash_ok. CPU load is a **ratio ×256**, not percent ×256.

Raw encoder IDs: 0 SELECT (normally tempo), 1 ALGORITHM (track), 2..5 KNOB 1..4,
6 PRESETS. Button IDs: 0 OCT−, 1 OCT+, 2 FX, 3 SCL, 4 ENV, 5 LFO, 6 EDIT, 7 GLO,
8 HOME, 9 SAVE, 10 ARP, 11 SEQ, 12 PLAY, 13 REC. IDs 14..40 are the FM-1's
27 panel keys F3..G5. Send panel edges for UI gestures; ordinary MIDI notes remain
available for velocity-sensitive keyboard playing.

HELLO releases the previous remote session. A session expires after 2 seconds
without a successful request: keys, buttons, remote master and frozen screen
release. Physical holds remain held. Send PING at least every second when idle.
One remote controller owns the panel; concurrent apps must not compete for it.
This token is a stale-session guard, not authentication.

MASTER imposes a remote ceiling, never raises the physical master level.
No command writes projects, settings, samples or firmware flash.

Screen data is a 120×120 RGB565 little-endian image (28,800 bytes), downsampled
from actual drawing operations. Freeze, read chunks, release. Each freeze has a
consistent buffer; it is not a camera/readback of the physical display.
If interrupted, expiry unfreezes and forces a redraw. Logical LEDs describe
firmware state, not verified physical LEDs.

Android can use MidiManager's USB input/output ports and this protocol without
running any emulator. Keep note events prioritized, coalesce encoder turns,
serialize replies, poll LEDs modestly and request screens on demand initially.
Do not embed Harbor's code/artwork without licence clearance.

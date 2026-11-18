# Controls and companion

Implemented bring-up mapping (host-tested logic, not a hardware-tested UI):

| Physical control | Main action | HOME modifier |
| --- | --- | --- |
| HOME | Home/back | Shift; unused hold opens menu |
| FX | FX | LFO |
| AMP | Edit/engine | Envelope |
| MOD | Scale | Arpeggiator |
| DLY | Sequencer | Global/song |
| REV | Record / hold for recording layer | Same |
| CAB | Save pages / hold for undo | Same (repeat taps reach projects) |
| Left footswitch | Play/stop | OCT− / Cancel in dialogs |
| Right footswitch | Record arm | OCT+ / Confirm in dialogs |
| PARA turn | Selected virtual encoder | Same |
| PARA click | Cycle encoder role | Same |
| MASTER | Master volume | Unchanged |

Do not require simultaneous DLY/REV/CAB: they share PC10's resistor ladder.
Physical reachability of every action remains a test requirement, not a claim.
PARA roles cycle KNOB 1..4 → PRESET → TEMPO → TRACK; an on-screen message names
the role. To change track, select TRACK and turn PARA. Remote MASTER can lower
the level but never raise it above the physical master pot; lease expiry
returns control to the physical pot.

## Full panel

Remote panel retains FM-1 IDs: keys 14..40, buttons 0..13, encoders 0..6.
Transmit edges and relative turns, not only MIDI notes/parameter values. A held
key on a layer or sequencer page has different behavior from a MIDI note.
Use an explicit session/heartbeat and release remote holds on expiry/disconnect.
Merge physical and remote holds without one source releasing the other's keys.

Harbor's existing Compose panel routes directly to its NativeEngine emulator.
A hardware backend needs outgoing Android MIDI, response parsing, capability
negotiation and device screen/LED feedback. Do not run a second emulator to
guess the real device's screen. Keep audio local to Blackbox initially.

Harbor has no identified reuse licence in the inspected checkout. Until clarified,
do not copy its Kotlin/Rust/UI artwork into this repository. Architecture and
public protocol research are not a code-copy licence.

Android acts as USB host/OTG, not as USB MIDI gadget. A powered hub can connect
Blackbox and Q mini concurrently; host/power behavior needs phone testing.
Wireless control is deferred until USB is proven.

## Coverage checklist

- All 14 buttons and 7 encoder roles, 27 keys, master and holds.
- Parameter locks, step editing, layer shortcuts, octaves and naming.
- Confirmation/cancel, engine-specific pages, projects and undo.
- MIDI note/bend/modulation/sustain without control-message collisions.
- Reconnect, heartbeat loss and Android background/screen-off behavior.
- Physical/remote key overlap, multi-touch and input ownership.

## Computer-host keyboard bridge

After installing/qualifying our firmware, route a Q mini's notes, velocity,
bend, modulation and sustain through the computer:

```sh
.venv/bin/python tools/blackbox.py bridge --input 'exact Q mini input' --port 'exact Blackbox port'
```

Optional command mode maps 27 consecutive incoming notes to FM-1 panel keys:

```sh
.venv/bin/python tools/blackbox.py bridge --input 'exact Q mini input' \
  --port 'exact Blackbox port' --panel-first-note 53
```

53 is an example, not a claim about the Q mini's octave setting. Observe its
actual notes first. Command mode retains panel holds for layers/step editing
but does not provide velocity-sensitive playing; restart without the flag to
play normally. Blackbox's buttons still select pages. The bridge drops all
keyboard SysEx so a keyboard cannot accidentally trigger OTA/editor writes.
It releases its held notes/sustain on normal exit, and remote panel holds expire
on loss of the host. Stop the bridge before running monitor/iterate: one remote
controller owns the USB panel protocol at a time.

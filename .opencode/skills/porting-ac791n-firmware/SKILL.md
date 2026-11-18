---
name: porting-ac791n-firmware
description: Use when porting FM-1 custom firmware to M-VAVE Blackbox or another JieLi AC791N board, adapting controls or flash layouts, or preparing automated USB firmware iteration and remote panels.
---

# Porting AC791N firmware

Preserve the application's behavior; replace the board assumptions. A matching
SoC or a renamed `.fwsc` is not a port.

## Before editing

Read the project's README, PROGRESS, rules and existing build/tests. Pin source,
BSP, engines, compiler and donor firmware. Review licences before copying code,
UI/artwork or vendor payloads; public source without a licence is not permission.

Reproduce an unmodified build and regression renders first. Label evidence
**source-inspected**, **host-tested**, **simulated** or **hardware-tested**.

## Audit the actual target

Record board revision, JEDEC ID/capacity, CPU clocks, RAM budget, GPIO, display,
codec framing, DMA/interrupt behavior and USB descriptors.

Read the application base from the package's boot entries, not a product name
or a sibling's offsets. Blackbox V20 uses 0x4000; the inspected V23 uses 0x6000.
Check all container bounds/CRCs and use whole-file checksums for opaque metadata.
Unknown revisions stop for investigation rather than inheriting a profile.

Audit application, loader, staging, settings/samples, factory bank, calibration,
boot head and per-unit key/MAC ranges together. A stock updater is not a backup
of user models/presets/calibration. Preserve those separately.
All ranges are half-open. In blackbox-fm1, even the persistence-disabled build
stages OTA at 0xE0000..0xE5000, overwriting part of the stock sound bank.
Check the pinned digest/profile in tools/blackbox_pkg.py, and verify the loader
also matches the installed boot-directory base before its first erase.

## Port narrowly

Keep shared chip/DSP code pinned. Add board adapters without editing submodules
in place. Match codec pin routing, sample justification and DMA half semantics;
do not carry a hardware-toggled half flag to a board where it never toggles.
Disable unsupported peripherals and persistence until their maps are reviewed.
Compile and enforce RAM/flash headroom on every change.
This port retains at least 4 KiB general RAM and 8 KiB pool headroom.

Make a control-coverage matrix: logical buttons, keys, all encoder roles,
held/released actions, naming, dialogs and sequencer parameter locks.
Avoid chords between keys on one ADC ladder. A MIDI note is not always a panel
key event. Merge remote/physical holds by source; expire remote leases.

## Establish repeatable iteration

First device session is read-only; preserve backups and recovery assets.
After a supervised first flash, demonstrate a second software-only update.
Qualify recovery on that unit before claiming unattended recoverability.
This project's hardware-qualified automatic sessions require recovery evidence;
until then, only a supervised pilot is eligible.
Honor a user's scoped authorization for normal repeat flashes; do not demand a
fresh confirmation for every iteration once the session is armed.

Bind exact, unambiguous application/loader ports. Build/test/validate before
writing; match runtime layout and source fingerprint after reconnect. Bound
sessions, record package hashes and every stage, disarm before operations, and
re-arm only on success. Stop on errors; never blindly retry, restore stock or
change partitions as an automatic fallback.

Identity proves neither sound nor display. Counters prove execution progress;
render capture proves rendered pixels, not the physical LCD. USB audio capture
and analog-output recording are separate measurements. Report unavailable
checks as unavailable, not passed.

## Reuse

Keep board support, update transport and remote-panel wire protocol separate
from each firmware's parameter/storage schema. A phone is the USB host/OTG;
two USB peripherals need a host, not just a cable/hub.

See `references/blackbox.md` for this port's implementation and open hardware
gates. Run the project's tests; update PROGRESS with failures and skipped checks.

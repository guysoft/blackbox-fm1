# Workflow

- Project name: blackbox-fm1; current directory is the repository root.
- User wants preparation completed before plugging in hardware.
- One supervised initial flash is acceptable. Subsequent normal development
  flashes should be automated and monitored end-to-end within an armed session.
- Android companion supplies a full virtual FM-1 panel; keyboard is optional.
- Keep PROGRESS.md current, including failures, skips and unknowns.
- No publication, dependency upgrades or destructive restore without approval.
- User authorized public GitHub publication and an experimental tagged release,
  following upstream's complete-source/firmware asset layout.
- Device was surveyed on stock V17; do not select V20/V23 from the product name.
- Full stock flash is backed up twice. The first install's capture failure was
  fixed by a supervised software-only update. No automatic recovery is authorized.
- Latest (2026-11-19): guard-fix community BLE source
  caad76381e727eca657112d3512b891b919f0174555beb0394282707e551e27b
  installed and working with Linux BlueZ/ALSA: discovery, full BLE HELLO, panel
  keys, one-minute chord/sustain traffic and reconnect. Boots=9, late=12 stable.
  Laptop disconnected to free the phone's one BLE link; advertising remains on.
  Later Android scan/full HELLO/heartbeats passed after a bounded startup retry
  fix. Rotation now retains the controller; four real rotations passed without
  disconnecting. App left portrait/connected, normal MIDI-keyboard mode.
  User reported brief working control; formal Android audio/cold-boot evidence
  remains incomplete. Phone is now attached through ADB.
  Later app update adds automatic layer-key chords (REC + F3); left connected,
  no song clear executed. Duplicate BLE HELLO self-cleanup is host-reproduced
  but remains an unflashed firmware issue; see PROGRESS.md.
  No automatic flashing/recovery armed. Detailed evidence and caveats: PROGRESS.md.

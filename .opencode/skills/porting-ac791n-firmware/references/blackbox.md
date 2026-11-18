# blackbox-fm1 reference

- Project: current repository; read PROGRESS.md and docs/BLACKBOX-DEVELOPMENT.md.
- Source fork: Felucca 1.8.2; own adapters in firmware/boards/blackbox/.
- Profile/package parser: tools/blackbox_pkg.py, pinned V17/V20/V23 digests.
- Build: tools/build.py --board blackbox-v17|blackbox-v20|blackbox-v23 --stock FILE.
- Host commands: tools/blackbox.py inspect / info / monitor / simulate / iterate.
- Remote panel: tools/blackbox_remote.py; firmware/src/blackbox_remote.c.
- Tests: pytest tests/blackbox; upstream regression: tests/run_tests.sh.
- First bring-up disables persistence. OTA staging still changes 0xE0000..0xE5000
  and overlaps stock factory/user-bank contents. Never call that non-destructive.
- V20 app area 0x4000..0xA5000; inspected V23 0x6000..0x9F000.
- Screen transport PB6/PB7, CS PB1, D/C PB5; PC7 is not a backlight pin.
- PA10 master, PC9 battery, PC10 ladder; PC0/PC1 encoder.
- ALNK0 TX channel 0, PA4..PA7, PA9 enable; 24-bit right-justified.
- Initial full remote render capture is downsampled 120×120 RGB565, 28,800 bytes.
- Surveyed unit is stock V17, JEDEC EB6014, 1 MiB. USB ROM entry, pinned RAM-reader
  full dump (twice identical) and return to V17 are hardware-tested. Full flash
  restore and custom boot/codec/display remain untested.
- V17 app region is [0x4000,0xA3000). Blackbox boot must not apply FM-1 plaintext
  XIP windows or scan stock data as samples/settings, even when writes are blocked.

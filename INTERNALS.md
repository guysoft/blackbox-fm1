# Architecture

Felucca compiles firmware/src/felucca.c as one translation unit. Its ordered
includes assemble engines, voices, effects, sequencer, UI, storage and editor.
firmware/bsp and firmware/engines remain pinned submodules.

Blackbox adapters override the board HAL using include-path precedence. Shared
chip code remains in the BSP. Target build output must be isolated from the
baseline FM-1 build so tests cannot accidentally validate the wrong image.

The Blackbox panel is not an FM-1 matrix: direct GPIO keys, a PC10 ADC ladder,
PC0/PC1 encoder and PA10 master pot. Display SPI1 is PB6/PB7, CS PB1, D/C PB5.
Audio uses ALNK0 TX channel 0, PA4..PA8, PA9 enable, right-justified 24-bit words.
These are source/reference findings, not measurements on our unit.

Host tooling must validate the package before MIDI writes, bind to one exact
input/output port, verify reconnect and poll health. A run directory holds an
append-only event log plus a final verdict. The firmware remains the authority
for state; Android is a remote panel, not a synchronized second emulator.

Stock preset reads use a separate protocol from our remote-panel handler:
`tools/blackbox_stock.py` permits only command 0x04 / marker 0x23 for the
64 aligned 92-byte preset objects, working buffer and 4-byte status. These are
logical objects, not raw flash reads. V17 hardware returned checksum-valid
records; this does not expose its boot map, JEDEC ID or amp/IR payloads.

Full flash backup is separate: `tools/blackbox_dump.py` pins the inspected
OpenPocket libusb implementation and wraps it in a dump-only transport allowlist.
The supervised stock soft key enters USB ROM; a RAM loader reads raw NOR, with
no erase/program rights. Both dumps must match before RUN_APP. Measured V17 unit:
1 MiB NOR `0xEB6014`, chip key `0x980f`, application base `0x4000`.

The V17 build profile ends its app region at `0xA3000`. Blackbox's exact JEDEC
allowlist lives in `firmware/boards/blackbox/flash_policy.h`, used by runtime and
loader. Its `persist_boot` only probes the chip; it does not install the FM-1
plaintext XIP window or interpret stock regions as FM-1 samples/settings.

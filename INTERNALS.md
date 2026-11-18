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

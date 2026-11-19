# Optimist BLE stack

Imported from https://github.com/w0ts/optimist at
`fcdc4881e8788365c62ea8be7fa11b4d82966bac`:
`firmware/src/ble/` → `src/`, and three radio HAL headers → `hal/`.

BLE code by hdavid. Copyright (C) 2026 Leo Kuroshita (@kurogedelic),
Hügelton Instruments and the Optimist contributors.
Stack/HAL: **GPL-3.0-only OR MPL-2.0**. RF startup configuration
`hal/ble_rf_tables_v15.h`: **Apache-2.0**, JieLi / M-VAVE.
Licence texts are in `LICENSES/`. This project uses the GPL option.

One file differs from that Optimist pin: `hal/fm1_ble_rf.h` is the verbatim
Pocket-Onyx version at `8ebf3090d8df82a3f5e8806aec964c1e1e9079d1`,
`custom-fw/third_party/optimist_ble/hal/fm1_ble_rf.h`. Its `PA-MOD` hooks allow
VCO timing and LUT calibration to be supplied by our board adapter.
No other Onyx link-layer/driver modifications are imported.

Blackbox integration is outside this directory, in `firmware/boards/blackbox/`.
Do not edit the imported stack in place. Its hardware register model and analog
startup remain unqualified on Blackbox; compilation is not RF validation.

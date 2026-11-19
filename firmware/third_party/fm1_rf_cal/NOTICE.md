# Community RF calibration

Verbatim source-only import from https://github.com/hugelton/felucca-bsp at
`2a5af3dfc8bccb92e37d48a3e7e0bf9a5827e51f`, the BSP pin inspected in fm1-base:
`chip/fm1_rf_cal.h`, `chip/fm1_ble_rf.h`, `chip/fm1_ble.h`, LICENSE and NOTICE.

The calibration header is Apache-2.0, copyright JieLi and Charles Vestal;
the two RF/baseband headers offer GPL-3.0-only OR MPL-2.0 (GPL chosen here).
Apache-2.0 text is also in `../optimist_ble/LICENSES/`.
No proprietary library is linked. The existing Optimist stack and BSP submodule
are unchanged. Only explicitly selected Blackbox self-calibration builds use
these headers. Blackbox policy and failure gates stay in the board adapter.

Original file hashes are recorded in `docs/reference-lock.json`.

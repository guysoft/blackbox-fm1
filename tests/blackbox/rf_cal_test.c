/* SPDX-License-Identifier: GPL-3.0-only */
/* Run the imported community calibration against a deterministic fake radio.
 * This tests bounded waits and field encoding, NOT RF correctness. */
#include <assert.h>
#include <stdint.h>
#include <string.h>
static uint32_t regs[0x32000 / 4], time_ticks;
static uint8_t windows[4][256];
static int filter_stuck, estimator_stuck, comparator_stuck;
#define FM1_TICKS_PER_US 24u
static uint32_t fm1_ticks(void) { time_ticks += 24u; return time_ticks; }
static void fm1_delay_us(uint32_t us) { time_ticks += us * 24u; }
static struct { uint32_t bbp_timeouts; } fm1_ble_rf_stat;
static uint32_t *reg(uint32_t a)
{
    assert(a < sizeof regs && !(a & 3));
    if (a == 0x11978u) {
        if (regs[0x11968 / 4] & 1u)
            regs[a / 4] = filter_stuck ? 0 : 0x20u | 0x45u << 8;
        else {
            uint32_t cap = regs[0x11938 / 4] >> 19 & 127u;
            uint32_t div = regs[0x1193C / 4] >> 5 & 255u;
            regs[a / 4] = comparator_stuck ? 0 : div + 2u * cap > 171u ? 1u << 18 : 1u << 17;
        }
    }
    return &regs[a / 4];
}
#define FM1_RF_REG(a) (*reg(a))
static uint32_t fm1_bbp(uint32_t a, uint32_t v, int read)
{
    (void)a; (void)v; (void)read; return 0;
}
static void fm1_bbp_win_wr(uint32_t w, uint32_t e, uint32_t v)
{
    assert(w < 4 && e < 256); windows[w][e] = (uint8_t)v;
}
static uint32_t fm1_bbp_win_rd(uint32_t w, uint32_t e)
{
    assert(w < 4 && e < 256);
    if (w == 3 && e == 0x8D) return estimator_stuck ? 3 : 0;
    if (w == 3 && e == 0x80) return 64; /* ADC peak completes at first gain. */
    return windows[w][e];
}
#include "../../firmware/third_party/fm1_rf_cal/fm1_rf_cal.h"
int main(void)
{
    struct fm1_rf_cal c = {0};
    uint8_t record[68];
    uint32_t a = 0x03100000u, b = 0x80008080u;
    assert(fm1_rf_cal_scan(&c) == 0 && c.mid_found && c.bank121 <= 127);
    assert(fm1_rf_cal_trim(&c, record) == 0);
    assert(!c.to_filter && !c.to_dem && !c.bbp_timeouts && c.dem_reads > 300);
    assert(c.flt[0] == 0x45 && c.flt[1] == 0x45 && c.flt[2] == 0x45);
    assert(fm1_rfc_crc16(record, 64) == (record[64] | (uint32_t)record[65] << 8));
    assert(fm1_rf_cal_reg(0x1195C, 0, record) == 0x454545FFu);
    assert(fm1_rf_cal_reg(0x11960, 0, record) == 0x454545FFu);
    assert(fm1_rf_cal_rfd_w0(128, 0x123, record) == (0x123u | 0x200u << 12 | 0x200u << 22));
    fm1_rf_cal_bt_trims(record, &a, &b);
    assert(a == 0x03100000u && b == 0x80007F7Fu); /* Neutral gains 1023 >> 3. */
    estimator_stuck = 1; c.abort = 0; c.to_dem = 0;
    assert(fm1_rfc_dem(&c, 0) == 0 && c.abort && c.to_dem == 1);
    assert(fm1_rfc_txiq_tune(&c) == FM1_RF_CAL_E_TXLO);
    assert(fm1_rfc_rxdc_tune(&c) == FM1_RF_CAL_E_RXDC);
    estimator_stuck = 0; filter_stuck = 1;
    assert(fm1_rfc_rx_tune(&c) == FM1_RF_CAL_E_FILTER);
    filter_stuck = 0; comparator_stuck = 1;
    memset(&c, 0, sizeof c);
    assert(fm1_rf_cal_scan(&c) == FM1_RF_CAL_E_MIDBANK && !c.mid_found);
    return 0;
}

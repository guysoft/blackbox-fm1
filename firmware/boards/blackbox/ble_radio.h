/* SPDX-License-Identifier: GPL-3.0-only */
/* Blackbox adapter for the pinned Optimist peripheral stack. Never FM-1 builds.
 * IRQ 29/45 priority 2, below ALNK0 (3) and TIMER5 (4). No flash writes/bonds. */
#pragma once
#include "ble_calibration.h"
#include "ble_io.h"
#define BLE_DEVICE_NAME "Blackbox MIDI"
#define BLE_NAME_HEX 1
#define BLE_CENTRAL 0
#define BLE_DIAG 0
#define FELUCCA_BLE_BOND 1
#define BLE_ADV_INTERVAL 400u

static bb_ble_io_t bb_ble_io;
static uint32_t bb_ble_status[16];
static uint32_t bb_ble_cal_diag[32];
static uint32_t bb_ble_rf_diag[20];
static uint8_t bb_ble_uid[16];
static volatile uint32_t bb_ble_discard_until;
static volatile uint8_t bb_ble_discarding;
#if !BLACKBOX_BLE_SELFCAL
static uint32_t bb_ble_vco_edge_us = 6, bb_ble_vco_settle_us = 100;
static void bb_ble_vco_scan(void);
static uint32_t bb_ble_lut_word(uint32_t e, uint32_t cmd, uint32_t word);
#define FM1_VCO_STOCK_SCAN bb_ble_vco_scan
#define FM1_LUT_W1(e, c, w) bb_ble_lut_word((e), (c), (w))
#define FM1_VCO_EDGE_US bb_ble_vco_edge_us
#define FM1_VCO_SETTLE_US bb_ble_vco_settle_us
#endif
#define ble_wl82_event_irq bb_ble_event_body
#define ble_wl82_rx_irq bb_ble_rx_body
#include "../../third_party/optimist_ble/src/ble_stack.c"
#undef ble_wl82_event_irq
#undef ble_wl82_rx_irq

/* The stack's assembly trampolines call these C bodies, never another RTI entry.
 * A stuck radio interrupt is masked rather than starving USB/audio to reset. */
static uint32_t bb_ble_irq_count, bb_ble_irq_start;
static void bb_ble_irq_guard(void)
{
    if (++bb_ble_irq_count >= 2000u) {
        uint32_t now = fm1_ticks();
        if (now - bb_ble_irq_start < 100000u * FM1_TICKS_PER_US) {
            fm1_ble_irqs_hold(1);
            bb_ble_io.fault = 3;
            bb_ble_io_lost(&bb_ble_io);
        }
        bb_ble_irq_count = 0;
        bb_ble_irq_start = now;
    }
}
void ble_wl82_event_irq(void)
{
    bb_ble_status[7]++;
    bb_ble_event_body();
    bb_ble_irq_guard();
}
void ble_wl82_rx_irq(void)
{
    bb_ble_status[8]++;
    bb_ble_rx_body();
    bb_ble_irq_guard();
}
BLE_API void ble_app_midi_in(uint32_t pkt, uint16_t ts, uint16_t last_ts)
{
    (void)ts; (void)last_ts;
    bb_ble_io_push(&bb_ble_io, pkt);
}
BLE_API int ble_app_midi_peek(uint32_t *pkt, uint32_t *t_ms)
{
    if (bb_ble_io.tr == bb_ble_io.tw) return 0;
    *pkt = bb_ble_io.tx[bb_ble_io.tr % BB_BLE_QUEUE];
    *t_ms = fm1_ms;
    return 1;
}
BLE_API void ble_app_midi_pop(void)
{
    RING_PUBLISH();
    bb_ble_io.tr++;
    bb_ble_io.sent++;
}
BLE_API void ble_app_state(void)
{
    uint8_t was_ready = bb_ble_io.ready;
    bb_ble_io.ready = (uint8_t)ble_midi_ready();
    if (was_ready && !bb_ble_io.ready) bb_ble_io_lost(&bb_ble_io);
}
/* Keys stay only in the stack's RAM slot. Persistence is still prohibited.
 * A phone may need to forget its old pairing after the pedal loses power. */
BLE_API void ble_app_bond(const uint8_t rand[8], uint16_t ediv, const uint8_t ltk[16])
{
    (void)rand; (void)ediv; (void)ltk;
}
BLE_API void ble_app_peer_id(const uint8_t irk[16], const uint8_t addr[6], uint8_t random)
{
    (void)irk; (void)addr; (void)random;
}

/* VCO feedback-divider calibration adapted from Pocket-Onyx ble_radio.c,
 * Copyright (C) 2026 The Onyx Authors (@28spawn), GPL-3.0-only.
 * Patches the startup LUT from this boot's measurements, not another unit's
 * capture. Supply-rail experiments and Pocket AMP flash addresses are omitted. */
#if !BLACKBOX_BLE_SELFCAL
static uint8_t bb_ble_vco_table[48], bb_ble_vco_ok;
static void bb_ble_vco_cap(uint32_t c)
{
    FM1_WL_VCO_BAND = (FM1_WL_VCO_BAND & ~(0x7Fu << 19)) | (c & 0x7Fu) << 19;
}
static void bb_ble_vco_div(uint32_t d)
{
    FM1_WL_VCO_FINE = (FM1_WL_VCO_FINE & ~(0xFFu << 5)) | (d & 0xFFu) << 5;
}
static void bb_ble_vco_latch(void)
{
    FM1_WL_VCO_BAND &= ~(1u << 16);
    FM1_WL_VCO_BAND &= ~(1u << 18);
    FM1_WL_VCO_EN &= ~(1u << 24);
    fm1_delay_us(bb_ble_vco_edge_us);
    FM1_WL_VCO_BAND |= 1u << 16;
    fm1_delay_us(bb_ble_vco_edge_us);
    FM1_WL_VCO_EN |= 1u << 24;
    FM1_WL_VCO_BAND |= 1u << 18;
    fm1_delay_us(bb_ble_vco_settle_us);
}
static uint32_t bb_ble_vco_probe(void)
{
    uint32_t i, r;
    FM1_WL_CAL_START = (FM1_WL_CAL_START & 0x0FFFFFFFu) | 0x10000000u;
    for (i = 0; i < 8u; i++) FM1_WL_CAL_STROBE = 1;
    FM1_WL_CAL_STROBE = 0;
    r = FM1_WL_CAL_STROBE;
    return ((r >> 16) & 2u) | ((r >> 18) & 1u);
}
static uint32_t bb_ble_vco_bank(uint32_t value)
{
    uint32_t i = 1;
    while (i < 48u && bb_ble_vco_table[i] <= value) i++;
    return (uint8_t)(bb_ble_vco_table[47] - (i == 48u ? 47u : i - 1u));
}
static void bb_ble_vco_scan(void)
{
    uint32_t cap, coarse = 0, div = 73, last = 73, midpoint = 0, i, result = 0;
    *(volatile uint32_t *)0x11940u |= 1u << 24;
    bb_ble_vco_div(73);
    for (cap = 7; cap < 120u; cap += 16u) {
        uint32_t a, b, c;
        bb_ble_vco_cap(cap); bb_ble_vco_latch(); a = bb_ble_vco_probe();
        bb_ble_vco_cap(cap - 7u); bb_ble_vco_latch(); b = bb_ble_vco_probe();
        bb_ble_vco_cap(cap + 8u); bb_ble_vco_latch(); c = bb_ble_vco_probe();
        result = a;
        if (b != a || c != a) { coarse = cap; bb_ble_vco_ok = 1; break; }
    }
    if (!bb_ble_vco_ok) {
        *(volatile uint32_t *)0x11940u &= ~(1u << 24);
        bb_ble_io.fault = 4;
        return;
    }
    (void)result;
    bb_ble_vco_table[47] = (uint8_t)(coarse | 15u);
    for (i = 0; i < 47u; i++) {
        if (i) div = midpoint;
        bb_ble_vco_cap((uint8_t)(bb_ble_vco_table[47] - i));
        midpoint = last;
        for (;;) {
            bb_ble_vco_div(midpoint);
            bb_ble_vco_latch();
            result = bb_ble_vco_probe();
            if (result == 1u) break;
            if (result == 2u) last = midpoint;
            if (++midpoint > 171u) { midpoint = 171; if (result == 2u) last = 171; break; }
        }
        bb_ble_vco_table[i] = (uint8_t)((last + div - 3u) / 2u);
    }
    bb_ble_vco_div(121);
    bb_ble_vco_cap(bb_ble_vco_bank(121));
    *(volatile uint32_t *)0x11940u &= ~(1u << 24);
}
static uint32_t bb_ble_lut_word(uint32_t e, uint32_t cmd, uint32_t word)
{
    if (!bb_ble_vco_ok || (cmd & 15u) != 13u || e > 127u) return word;
    return (word & ~(0x7Fu << 9)) | bb_ble_vco_bank((word >> 21) & 255u) << 9;
}
#endif

/* Boot-only: fm1_main locks the vector table AFTER audio attaches its vector.
 * Do not copy a runtime radio toggle's unlock/lock pair into this boot path. */
static void bb_ble_attach_boot_irqs(void)
{
    uint32_t f = fm1__lock();
    ble_hw_wl82_attach();
    fm1__unlock(f);
}

static void bb_ble_start(const bb_ble_calibration_t *cal)
{
    struct ble_rf_trims trims;
    uint8_t addr[6];
    uint32_t i, hash = 2166136261u;
    const uint8_t *bytes = (const uint8_t *)cal;
    bb_ble_status[0] = 1; /* calibration available, beginning startup */
#if BLACKBOX_BLE_SELFCAL
    bytes = bb_ble_uid;
    for (i = 0; i < sizeof bb_ble_uid; i++) { hash ^= bytes[i]; hash *= 16777619u; }
#else
    for (i = 0; i < sizeof *cal; i++) { hash ^= bytes[i]; hash *= 16777619u; }
#endif
    for (i = 0; i < 6u; i++) { hash ^= i + 0x42u; hash *= 16777619u; addr[i] = (uint8_t)(hash >> 8); }
    addr[5] |= 0xC0u; /* stable random-static address, calibration stays private */
    addr[0] |= 1u; addr[4] &= 0xFEu; /* nonconstant random part */
    memcpy(trims.x106, cal->x106, sizeof trims.x106);
    memcpy(trims.x107, cal->x107, sizeof trims.x107);
    memcpy(trims.x108, cal->x108, sizeof trims.x108);
    memcpy(trims.x187, cal->x187, sizeof trims.x187);
#if !BLACKBOX_BLE_SELFCAL
    {
        /* Onyx's conservative loop-to-time conversion: twice the estimated
         * settling time, selected by the live 4/8 MHz RF reference bit. */
        uint32_t ref = (*(volatile uint32_t *)0x40200u & 1u) ? 8u : 4u;
        bb_ble_vco_edge_us = ((20u + ref - 1u) / ref) * 2u;
        bb_ble_vco_settle_us = ((400u + ref - 1u) / ref) * 2u;
    }
#else
    fm1_rf_cal_on = 1;
#endif
    bb_ble_attach_boot_irqs();
    ble_init(addr, 1);
    ble_hw_wl82_start(&trims);
#if BLACKBOX_BLE_SELFCAL
    bb_ble_rf_diag[1] = 1;
    bb_ble_rf_diag[2] = (uint32_t)fm1_rfc_scan_rc;
    bb_ble_rf_diag[3] = (uint32_t)fm1_rfc_trim_rc;
    bb_ble_rf_diag[4] = fm1_rfc.mid;
    bb_ble_rf_diag[5] = fm1_rfc.bank121;
    for (i = 0; i < 3u; i++) bb_ble_rf_diag[6u + i] = fm1_rfc.flt[i];
    bb_ble_rf_diag[9] = fm1_rfc.txlo_i; bb_ble_rf_diag[10] = fm1_rfc.txlo_q;
    bb_ble_rf_diag[11] = fm1_rfc.us_scan; bb_ble_rf_diag[12] = fm1_rfc.us_total;
    bb_ble_rf_diag[13] = fm1_rfc.to_filter; bb_ble_rf_diag[14] = fm1_rfc.to_dem;
    bb_ble_rf_diag[15] = fm1_rfc.bbp_timeouts;
    if (!fm1_rfc_scanned || !fm1_rfc_trimmed || fm1_rfc_scan_rc || fm1_rfc_trim_rc ||
        fm1_rfc.to_filter || fm1_rfc.to_dem || fm1_rfc.bbp_timeouts)
        bb_ble_io.fault = 7; /* Never advertise with fallback/failed measurements. */
#else
    if (bb_ble_vco_ok) {
        /* Later captured startup words rewrite the band; restore this boot's
         * measured divider/bank and latch it, as Onyx's integration does. */
        bb_ble_vco_div(121);
        bb_ble_vco_cap(bb_ble_vco_bank(121));
        bb_ble_vco_latch();
    }
#endif
    bb_ble_status[9] = fm1_ble_rf_stat.bbp_timeouts;
    bb_ble_status[10] = fm1_ble_rf_stat.spi_timeouts;
    if (bb_ble_io.fault || bb_ble_status[9] || bb_ble_status[10] || fm1_ble_rf_stat.bad_op) {
        if (!bb_ble_io.fault) bb_ble_io.fault = 2;
        bb_ble_status[0] = 3; /* failed: never advertise, USB remains available */
        return;
    }
    ble_enable(1);
    fm1_ble_irqs_hold(0);
    bb_ble_status[0] = 2; /* enabled, not proof of RF reception */
}

/* TIMER5 is the sole producer of midi_in_q, as it is for USB. */
static void bb_ble_tick(void)
{
    uint32_t pkt, limit = 8;
    if (bb_ble_io.lost) {
        bb_ble_io_reset_rx(&bb_ble_io);
        bb_ble_discard_until = mi_w;
        bb_ble_discarding = 1;
        bb_ble_io.release_audio = bb_ble_io.release_panel = 1;
        bb_ble_io.lost = 0;
    }
    while (limit-- && bb_ble_io_pop(&bb_ble_io, &pkt)) {
        uint32_t cin = pkt & 15u, st = (pkt >> 8) & 255u;
        if (bb_ble_io_sysex(&bb_ble_io, pkt)) continue;
        if (cin >= 8u && cin <= 14u && (st >> 4) == cin &&
            !((pkt >> 16) & 128u) && ((cin == 12u || cin == 13u) || !(pkt & 0x80000000u))) {
            if (midi_in_overflow || mi_w - mi_r >= MQ) {
                bb_ble_io.fault = 1; bb_ble_io.lost = 1; break;
            }
            (void)midi_enqueue(pkt, 3u);
        }
    }
}
static void bb_ble_send(const uint8_t *p, uint32_t n)
{
    uint32_t f = fm1__lock();
    (void)bb_ble_io_reply(&bb_ble_io, p, n);
    fm1__unlock(f);
}
static void bb_ble_update_status(void)
{
    bb_ble_rf_diag[0] = 1;
    bb_ble_rf_diag[16] = fm1_ble_bc.now;
    bb_ble_rf_diag[17] = fm1_ble_bc.prev;
    bb_ble_rf_diag[18] = fm1_ble_bc.prev_addr;
    bb_ble_rf_diag[19] = fm1_ble_bc.addr;
    if (bb_ble_io.fault && bb_ble_status[0] == 2u) {
        fm1_ble_irqs_hold(1);
        ble_enable(0);
        bb_ble_io_lost(&bb_ble_io);
        bb_ble_status[0] = 3;
    }
    bb_ble_status[2] = (uint32_t)ble_connected();
    bb_ble_status[3] = bb_ble_io.ready;
    bb_ble_status[4] = bb_ble_io.received;
    bb_ble_status[5] = bb_ble_io.sent;
    bb_ble_status[6] = bb_ble_io.drops;
    bb_ble_status[11] = fm1_ble_rf_stat.scan_found;
    bb_ble_status[12] = ble_hw_stat.isr_max_ticks / FM1_TICKS_PER_US;
    bb_ble_status[13] = bb_ble_io.fault;
    bb_ble_status[14] = fm1_ble_rf_stat.sections;
}

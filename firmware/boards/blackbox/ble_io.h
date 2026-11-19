/* SPDX-License-Identifier: GPL-3.0-only */
/* Bounded BLE IRQ -> TIMER5 ring and main -> BLE IRQ reply ring.
 * Only the remote-panel namespace is assembled; OTA/editor never see BLE. */
#pragma once
#include <stdint.h>
#define BB_BLE_QUEUE 64u
typedef struct {
    uint32_t rx[BB_BLE_QUEUE], tx[BB_BLE_QUEUE];
    volatile uint32_t rw, rr, tw, tr;
    volatile uint32_t received, sent, drops, fault;
    volatile uint8_t lost, release_audio, release_panel, ready;
    uint8_t control[16], assembling[16], pos, collecting;
    volatile uint8_t control_n;
} bb_ble_io_t;

static void bb_ble_io_reset_rx(bb_ble_io_t *s)
{
    s->rr = s->rw;
    s->pos = s->collecting = s->control_n = 0;
}
static void bb_ble_io_lost(bb_ble_io_t *s)
{
    s->ready = 0;
    s->tr = s->tw;
    s->lost = 1;
}
static void bb_ble_io_push(bb_ble_io_t *s, uint32_t pkt)
{
    if (!s->ready || s->lost || s->fault) return;
    if (s->rw - s->rr >= BB_BLE_QUEUE) {
        s->drops++; s->fault = 1; s->lost = 1;
        return;
    }
    s->rx[s->rw % BB_BLE_QUEUE] = pkt;
    RING_PUBLISH();
    s->rw++;
    s->received++;
}
static int bb_ble_io_pop(bb_ble_io_t *s, uint32_t *pkt)
{
    if (s->rr == s->rw) return 0;
    *pkt = s->rx[s->rr % BB_BLE_QUEUE];
    RING_PUBLISH();
    s->rr++;
    return 1;
}
static void bb_ble_io_byte(bb_ble_io_t *s, uint8_t b)
{
    if (b >= 0xF8u) return;
    if (b == 0xF0u) { s->pos = 0; s->collecting = 1; return; }
    if (!s->collecting) return;
    if (b == 0xF7u) {
        if (s->pos >= 4u && s->assembling[0] == 0x7D && s->assembling[1] == 0x42 &&
            s->assembling[2] == 0x42 && !s->control_n) {
            uint32_t i;
            for (i = 0; i < s->pos; i++) s->control[i] = s->assembling[i];
            RING_PUBLISH();
            s->control_n = s->pos;
        }
        s->pos = s->collecting = 0;
    } else if (b >= 128u || s->pos >= sizeof s->assembling) {
        s->pos = s->collecting = 0;
    } else s->assembling[s->pos++] = b;
}
static int bb_ble_io_sysex(bb_ble_io_t *s, uint32_t pkt)
{
    uint32_t cin = pkt & 15u, i, n;
    if (cin < 4u || cin > 7u) return 0;
    n = cin == 4u || cin == 7u ? 3u : cin == 6u ? 2u : 1u;
    for (i = 0; i < n; i++) bb_ble_io_byte(s, (uint8_t)(pkt >> (8u * (i + 1u))));
    return 1;
}
/* Caller masks BLE IRQs; publication is atomic for the entire reply. */
static int bb_ble_io_reply(bb_ble_io_t *s, const uint8_t *p, uint32_t n)
{
    uint32_t i = 0, w = s->tw, packets = (n + 2u) / 3u;
    if (!s->ready || !n || n > 192u) return 0;
    if (w - s->tr + packets > BB_BLE_QUEUE) {
        s->drops++; s->fault = 1; s->lost = 1;
        return 0;
    }
    while (i < n) {
        uint32_t k = n - i >= 3u ? 3u : n - i;
        uint32_t cin = i + k < n ? 4u : 4u + k;
        s->tx[w++ % BB_BLE_QUEUE] = cin | (uint32_t)p[i] << 8 |
            (k > 1u ? (uint32_t)p[i + 1u] << 16 : 0u) | (k > 2u ? (uint32_t)p[i + 2u] << 24 : 0u);
        i += k;
    }
    RING_PUBLISH();
    s->tw = w;
    return 1;
}

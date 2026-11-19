/* SPDX-License-Identifier: GPL-3.0-only */
/* SDK VM record format documented by Optimist and Pocket-Onyx. Read-only.
 * The caller supplies exactly one bounded VM sector, never an FM-1 address. */
#pragma once
#include <stdint.h>

typedef struct {
    uint8_t x106[2], x107[7], x108[20], x187[68];
} bb_ble_calibration_t;

static uint16_t bb_ble_crc16(const uint8_t *p, uint32_t n)
{
    uint32_t i, k;
    uint16_t c = 0;
    for (i = 0; i < n; i++) {
        c ^= (uint16_t)p[i] << 8;
        for (k = 0; k < 8u; k++) c = (uint16_t)(c & 0x8000u ? ((uint32_t)c << 1) ^ 0x1021u : (uint32_t)c << 1);
    }
    return c;
}

/* Last valid record wins. A corrupt/truncated tail is not silently accepted. */
static uint32_t bb_ble_calibration_inspect(const uint8_t *p, uint32_t n, bb_ble_calibration_t *out,
                                          uint32_t diag[7])
{
    bb_ble_calibration_t t = {{0}, {0}, {0}, {0}};
    uint32_t at = 4, found = 0, k;
    /* error, offset, ID, length, expected CRC, returned CRC, found mask.
     * Keep the parser fail-closed; diagnostics must not relax validation. */
    for (k = 0; k < 7u; k++) diag[k] = 0;
    diag[0] = 1;
    if (!p || !out || n < 4u || p[0] != 0x55 || p[1] != 0xAA || p[2] != 0xAA || p[3] != 0x55) return 0;
    while (at + 4u <= n) {
        uint32_t id, len, i, expected_len = 0;
        uint8_t *dst = 0;
        if (p[at] == 255u && p[at + 1u] == 255u && p[at + 2u] == 255u && p[at + 3u] == 255u) break;
        id = p[at + 1u] | (uint32_t)(p[at + 2u] & 15u) << 8;
        len = (p[at + 2u] >> 4) | (uint32_t)p[at + 3u] << 4;
        diag[1] = at; diag[2] = id; diag[3] = len; diag[6] = found;
        diag[0] = 2;
        if (!len || len > n - at - 4u) return 0;
        diag[0] = 3;
        diag[4] = (uint8_t)bb_ble_crc16(p + at + 4u, len); diag[5] = p[at];
        if (diag[4] != diag[5]) return 0;
        if (id == 106u) { expected_len = 2; dst = t.x106; }
        if (id == 107u) { expected_len = 7; dst = t.x107; }
        if (id == 108u) { expected_len = 20; dst = t.x108; }
        if (id == 187u) { expected_len = 68; dst = t.x187; }
        diag[0] = 4;
        if (dst && len != expected_len) return 0;
        if (id == 187u) {
            uint16_t crc;
            crc = bb_ble_crc16(p + at + 4u, 64u);
            diag[0] = 5; diag[4] = crc;
            diag[5] = p[at + 68u] | (uint32_t)p[at + 69u] << 8 |
                      (uint32_t)p[at + 70u] << 16 | (uint32_t)p[at + 71u] << 24;
            if (p[at + 68u] != (uint8_t)crc || p[at + 69u] != (uint8_t)(crc >> 8) ||
                 p[at + 70u] || p[at + 71u]) return 0;
        }
        if (id == 106u) found |= 1u;
        if (id == 107u) found |= 2u;
        if (id == 108u) found |= 4u;
        if (id == 187u) found |= 8u;
        if (dst) for (i = 0; i < len; i++) dst[i] = p[at + 4u + i];
        at += 4u + len;
    }
    diag[0] = found == 15u ? 0u : 6u;
    diag[1] = at; diag[6] = found;
    if (found == 15u) *out = t;
    return found;
}

static uint32_t bb_ble_calibration_parse(const uint8_t *p, uint32_t n, bb_ble_calibration_t *out)
{
    uint32_t diag[7];
    return bb_ble_calibration_inspect(p, n, out, diag);
}

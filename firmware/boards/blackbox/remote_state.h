/* SPDX-License-Identifier: GPL-3.0-only */
/* Small remote panel state; no emulator and no work in the audio interrupt. */
#pragma once
#include <stdint.h>
#define BB_SCREEN_W 120u
#define BB_SCREEN_H 120u
static uint16_t bb_screen[BB_SCREEN_W * BB_SCREEN_H] __attribute__((section(".pool")));
static uint8_t bb_screen_frozen, bb_remote_token, bb_master_owned;
static uint16_t bb_remote_master;
static uint32_t bb_remote_last;

static void bb_capture_fill(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint16_t color)
{
    uint32_t xx, yy;
    if (bb_screen_frozen) return;
    for (yy = (y + 1u) & ~1u; yy < y + h && yy < 240u; yy += 2u)
        for (xx = (x + 1u) & ~1u; xx < x + w && xx < 240u; xx += 2u)
            bb_screen[(yy / 2u) * BB_SCREEN_W + xx / 2u] = color;
}

/* LCD buffers contain wire-order RGB565 (big-endian bytes). */
static void bb_capture_blit(uint32_t x, uint32_t y, uint32_t w, uint32_t h, const uint16_t *pixels)
{
    uint32_t xx, yy;
    const uint8_t *p = (const uint8_t *)pixels;
    if (bb_screen_frozen) return;
    for (yy = (y + 1u) & ~1u; yy < y + h && yy < 240u; yy += 2u)
        for (xx = (x + 1u) & ~1u; xx < x + w && xx < 240u; xx += 2u) {
            uint32_t n = 2u * ((yy - y) * w + xx - x);
            bb_screen[(yy / 2u) * BB_SCREEN_W + xx / 2u] = (uint16_t)((uint16_t)p[n] << 8 | p[n + 1u]);
        }
}

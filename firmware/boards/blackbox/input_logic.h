/* SPDX-License-Identifier: GPL-3.0-only */
/* Portable, deterministic input logic. No register access. */
#pragma once
#include <stdint.h>

enum { BB_HOME, BB_FX, BB_AMP, BB_MOD, BB_DLY, BB_REV, BB_CAB, BB_LEFT, BB_RIGHT, BB_PUSH, BB_NKEY };
typedef struct {
    uint16_t stable, candidate, count[BB_NKEY];
    uint16_t home_ticks;
    uint8_t home_used, home_menu, role, enc_prev;
    int8_t enc_sub;
    uint16_t pulse;
    uint32_t held;
} bb_input_t;

/* A single ADC ladder: report at most one key. Simultaneous ladder keys are unsupported. */
static uint16_t bb_ladder(int32_t v)
{
    if (v < 0 || v < 450 || v >= 905) return 0;
    return (uint16_t)(1u << (v < 661 ? BB_CAB : v < 746 ? BB_DLY : BB_REV));
}

/* Called at 1 kHz, 10 agreeing samples per physical key. FM-1 matrix IDs are the ABI. */
static uint32_t bb_input_update(bb_input_t *s, uint16_t raw)
{
    static const uint8_t normal[BB_NKEY] = {8, 2, 6, 3, 11, 13, 9, 12, 13, 0};
    static const uint8_t shifted[BB_NKEY] = {8, 5, 4, 10, 7, 13, 9, 0, 1, 0};
    uint32_t k, out = 0;
    uint16_t old = s->stable, changed, up;
    s->pulse = 0;
    for (k = 0; k < BB_NKEY; k++) {
        uint16_t bit = (uint16_t)(1u << k);
        if ((raw & bit) != (s->candidate & bit)) {
            s->candidate ^= bit;
            s->count[k] = 0;
        } else if (s->count[k] < 10u && ++s->count[k] == 10u) {
            s->stable = (uint16_t)((s->stable & ~bit) | (raw & bit));
        }
    }
    changed = (uint16_t)(s->stable ^ old);
    up = (uint16_t)(changed & old);
    if (s->stable & (1u << BB_HOME)) {
        if (s->home_ticks < 60000u) s->home_ticks++;
        if (s->stable & ~(1u << BB_HOME)) s->home_used = 1;
        /* A lone hold opens Felucca's own HOME-held menu. */
        if (!s->home_used && s->home_ticks >= 600u) s->home_menu = 1;
        if (s->home_menu) out |= 1u << 8;
    } else if (up & (1u << BB_HOME)) {
        if (!s->home_used && !s->home_menu) s->pulse |= 1u << 8;
        s->home_ticks = 0;
        s->home_used = s->home_menu = 0;
    }
    if ((changed & s->stable) & (1u << BB_PUSH)) {
        s->role = (uint8_t)((s->role + 1u) % 7u);
        if (s->stable & 1u) s->home_used = 1;
    }
    for (k = 1; k < BB_PUSH; k++)
        if ((changed & s->stable) & (1u << k)) {
            uint32_t id = (s->stable & 1u) ? shifted[k] : normal[k];
            /* Latch the action at press time: releasing Shift must not change a held action. */
            s->held = (s->held & ~(15u << (4u * (k - 1u)))) | (id << (4u * (k - 1u)));
        }
    for (k = 1; k < BB_PUSH; k++)
        if (s->stable & (1u << k))
            out |= 1u << ((s->held >> (4u * (k - 1u))) & 15u);
    return out | s->pulse;
}

static int32_t bb_encoder(bb_input_t *s, uint8_t state)
{
    /* PC0 is bit 0, PC1 bit 1; clockwise has PC0 leading. */
    static const int8_t delta[16] = {0,1,-1,0, -1,0,0,1, 1,0,0,-1, 0,-1,1,0};
    int32_t step = 0;
    state &= 3u;
    if ((state ^ s->enc_prev) == 3u) {
        s->enc_sub = 0; /* an ambiguous jump must not invent a detent */
        s->enc_prev = state;
        return 0;
    }
    s->enc_sub += delta[(s->enc_prev << 2) | state];
    s->enc_prev = state;
    if (s->enc_sub >= 4) { step = 1; s->enc_sub -= 4; }
    if (s->enc_sub <= -4) { step = -1; s->enc_sub += 4; }
    return step;
}

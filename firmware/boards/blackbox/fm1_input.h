/* SPDX-License-Identifier: GPL-3.0-only */
/* Reuse Felucca's logical panel ABI, never drive its FM-1 matrix wiring. */
#pragma once
#include "fm1_adc.h"
#define fm1_input_init fm1_unused_matrix_init
#define fm1_input_tick fm1_unused_matrix_tick
#define fm1_input_scan fm1_unused_matrix_scan
#define fm1__led_lines fm1_unused_matrix_led_lines
#define fm1_led_anim_start fm1_unused_anim_start
#define fm1_led_idle_start fm1_unused_idle_start
#define fm1_led_levels_start fm1_unused_levels_start
#define fm1_led_anim_on fm1_unused_anim_on
#define fm1_led_idle_on fm1_unused_idle_on
#include "../../bsp/boards/fm1/fm1_input.h"
#undef fm1_input_init
#undef fm1_input_tick
#undef fm1_input_scan
#undef fm1__led_lines
#undef fm1_led_anim_start
#undef fm1_led_idle_start
#undef fm1_led_levels_start
#undef fm1_led_anim_on
#undef fm1_led_idle_on
#include "input_logic.h"

static bb_input_t bb_inputs;
static uint32_t bb_physical_buttons, bb_remote_buttons, bb_remote_notes;
static uint32_t bb_ladder_raw;
static void bb_board_early(void) { fm1_p33_write(0x94u, 0); } /* Disable stock Blackbox's long-press reset. */
static void fm1__led_lines(uint32_t m) { (void)m; } /* Physical LED driver deferred; logical LEDs retained. */
static void fm1_led_anim_start(uint32_t g) { (void)g; }
static void fm1_led_idle_start(uint32_t g) { (void)g; }
static void fm1_led_levels_start(void) {}
static int fm1_led_anim_on(void) { return 0; }
static int fm1_led_idle_on(void) { return 0; }

static void bb_digital_pins(uint32_t p, uint32_t m)
{
    FM1_PR(p, FM1_DIR) |= m;
    FM1_PR(p, FM1_DIE) |= m;
    FM1_PR(p, FM1_PD) &= ~m;
    FM1_PR(p, FM1_PU) |= m;
}
static void fm1_input_init(void)
{
    bb_digital_pins(FM1_PA, 15u);
    bb_digital_pins(FM1_PH, (1u << 6) | (1u << 8) | (1u << 9));
    bb_digital_pins(FM1_PC, 3u);
    bb_inputs.enc_prev = (uint8_t)(FM1_PR(FM1_PC, FM1_IN) & 3u);
    bb_inputs.role = 2; /* virtual KNOB 1; push cycles 2,3,4,5,6,0,1 */
}

/* Called from the main loop, not the timer ISR: the shared ADC is never
 * blocked while the audio is preempted. */
static void bb_inputs_poll(void)
{
    int32_t a = fm1_adc_read(BB_ADC_KEYS);
    if (a >= 0) bb_ladder_raw = bb_ladder(a);
}
static void bb_merge_inputs(void)
{
    uint32_t buttons = bb_physical_buttons | bb_remote_buttons;
    fm1_in.pressed |= buttons & ~fm1_in.buttons;
    fm1_in.released |= fm1_in.buttons & ~buttons;
    fm1_in.buttons = buttons;
    fm1_in.notes_pressed |= bb_remote_notes & ~fm1_in.notes;
    fm1_in.notes = bb_remote_notes;
}
static void fm1_input_tick(void)
{
    static uint32_t sub;
    uint32_t a, h;
    int32_t step;
    step = bb_encoder(&bb_inputs, (uint8_t)(FM1_PR(FM1_PC, FM1_IN) & 3u));
    if (step) {
        int32_t n = fm1_in.enc_steps[bb_inputs.role] + step;
        if (n > -32768 && n < 32768) fm1_in.enc_steps[bb_inputs.role] = (int16_t)n;
    }
    if (++sub < 10u) return; /* 1 kHz debounce, encoder still sampled at 10 kHz */
    sub = 0;
    a = ~FM1_PR(FM1_PA, FM1_IN);
    h = ~FM1_PR(FM1_PH, FM1_IN);
    bb_physical_buttons = bb_input_update(&bb_inputs, (uint16_t)(
        ((a >> 1) & 1u) | ((a & 1u) << BB_FX) |
        (((h >> 9) & 1u) << BB_AMP) | (((h >> 8) & 1u) << BB_MOD) |
        (((a >> 3) & 1u) << BB_LEFT) | (((a >> 2) & 1u) << BB_RIGHT) |
        (((h >> 6) & 1u) << BB_PUSH) | bb_ladder_raw));
    bb_merge_inputs();
}
static void fm1_input_scan(void) { fm1_input_tick(); }

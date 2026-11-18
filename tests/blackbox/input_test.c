/* SPDX-License-Identifier: GPL-3.0-only */
#include <assert.h>
#include "../../firmware/boards/blackbox/input_logic.h"
#include "../../firmware/boards/blackbox/remote_state.h"

static uint32_t scan(bb_input_t *s, uint16_t raw, unsigned n)
{
    uint32_t result = 0;
    while (n--) result = bb_input_update(s, raw);
    return result;
}
int main(void)
{
    bb_input_t s = {0};
    uint16_t pixels[4] = {0x00F8, 0xE007, 0x1F00, 0xFFFF};
    uint32_t n;
    assert(bb_ladder(-1) == 0 && bb_ladder(1023) == 0 && bb_ladder(0) == 0);
    assert(bb_ladder(616) == (1u << BB_CAB));
    assert(bb_ladder(706) == (1u << BB_DLY));
    assert(bb_ladder(787) == (1u << BB_REV));
    assert(scan(&s, 1u << BB_FX, 9) == 0);
    assert(scan(&s, 1u << BB_FX, 2) == (1u << 2));
    assert(scan(&s, 0, 11) == 0);
    scan(&s, (1u << BB_HOME), 11);
    assert(scan(&s, (1u << BB_HOME) | (1u << BB_FX), 11) == (1u << 5));
    assert(scan(&s, (1u << BB_FX), 11) == (1u << 5)); /* action latched until release */
    scan(&s, 0, 11);
    assert(scan(&s, 1u << BB_PUSH, 11) == 0 && s.role == 1);
    scan(&s, 0, 11);
    scan(&s, 1u << BB_HOME, 620);
    assert(s.home_menu && scan(&s, 1u << BB_HOME, 1) == (1u << 8));
    scan(&s, 0, 11);
    s.enc_prev = 0;
    n = 0;
    n += bb_encoder(&s, 1);
    n += bb_encoder(&s, 3);
    n += bb_encoder(&s, 2);
    n += bb_encoder(&s, 0);
    assert(n == 1);
    assert(bb_encoder(&s, 0) == 0);
    assert(bb_encoder(&s, 3) == 0 && s.enc_sub == 0);
    bb_capture_fill(0, 0, 240, 240, 0x1234);
    assert(bb_screen[0] == 0x1234 && bb_screen[14399] == 0x1234);
    bb_capture_blit(0, 0, 2, 2, pixels);
    assert(bb_screen[0] == 0xF800); /* big-endian LCD stream -> numeric RGB565 */
    bb_screen_frozen = 1;
    bb_capture_fill(0, 0, 240, 240, 0);
    assert(bb_screen[0] == 0xF800);
    return 0;
}

/* SPDX-License-Identifier: GPL-3.0-only */
/* Experimental remote panel, SysEx F0 7D 42 42 cmd args F7.
 * Main-loop only. One host session, 2s lease, logical screen capture at half
 * resolution. Does not claim that the physical LCD/codec works. */
static void bb_remote_clear(void)
{
    uint32_t f = fm1__lock();
    bb_remote_buttons = bb_remote_notes = 0;
    bb_master_owned = 0;
    bb_screen_frozen = 0;
    bb_remote_token = 0;
    bb_merge_inputs();
    fm1__unlock(f);
    ui.force = 1;
}
static uint32_t bb_get21(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 7 | (uint32_t)p[2] << 14; }
static void bb_put32(uint32_t v)
{
    uint32_t k;
    for (k = 0; k < 5u; k++) { ed_b(v); v >>= 7; }
}
static void bb_reply_begin(uint8_t cmd, uint8_t rc)
{
    ed_begin(cmd);
    ed_out[2] = ed_out[3] = 0x42;
    ed_b(rc);
}
static void bb_remote_service(void)
{
    const uint8_t *p;
    uint32_t n, cmd, rc = 0, k, f;
    if (bb_remote_token && fm1_ms - bb_remote_last > 2000u) bb_remote_clear();
    if (!ota_frame_get(&p, &n) || n < 4u || p[0] != 0x7D || p[1] != 0x42 || p[2] != 0x42)
        return;
    cmd = p[3];
    if (cmd == 1u) { /* HELLO token */
        if (n != 5u || !p[4]) rc = 1;
        else { bb_remote_clear(); bb_remote_token = p[4]; }
    } else if (!bb_remote_token || n < 5u || p[4] != bb_remote_token) rc = 2;
    else if (cmd == 2u) { /* KEY token, logical matrix ID, down */
        if (n != 7u || p[5] >= 41u || p[6] > 1u) rc = 1;
        else {
            uint32_t bit = 1u << (p[5] < 14u ? p[5] : p[5] - 14u);
            volatile uint32_t *mask = p[5] < 14u ? &bb_remote_buttons : &bb_remote_notes;
            f = fm1__lock();
            if (p[6]) {
                *mask |= bit;
                if (p[5] >= 14u) fm1_in.note_t0[p[5] - 14u] = fm1_ticks();
            } else *mask &= ~bit;
            bb_merge_inputs();
            fm1__unlock(f);
        }
    } else if (cmd == 3u) { /* ENC token, raw encoder ID, delta+64 */
        if (n != 7u || p[5] >= 7u || p[6] == 0u) rc = 1;
        else {
            int32_t value;
            f = fm1__lock();
            value = fm1_in.enc_steps[p[5]] + (int32_t)p[6] - 64;
            fm1_in.enc_steps[p[5]] = (int16_t)clamp(value, -32767, 32767);
            fm1__unlock(f);
        }
    } else if (cmd == 9u) { /* MASTER token, own(0/1), value14 */
        if (n != 8u || p[5] > 1u || (p[6] | (uint32_t)p[7] << 7) > 1023u) rc = 1;
        else { bb_master_owned = p[5]; bb_remote_master = (uint16_t)(p[6] | p[7] << 7); }
    } else if (cmd == 7u) { /* SCREEN token, op: 0 freeze, 1 read(offset21), 2 release */
        if (n < 6u || p[5] > 2u || (p[5] == 1u ? n != 9u : n != 6u)) rc = 1;
        else if (p[5] == 0u) bb_screen_frozen = 1;
        else if (p[5] == 2u) { bb_screen_frozen = 0; ui.force = 1; }
        else if (!bb_screen_frozen || bb_get21(p + 6) >= sizeof bb_screen) rc = 3;
    } else if (cmd == 4u || cmd == 5u || cmd == 6u || cmd == 8u) {
        if (n != 5u) rc = 1;
        else if (cmd == 6u) bb_remote_clear();
    } else rc = 4;
    bb_reply_begin((uint8_t)cmd, (uint8_t)rc);
    if (!rc) {
        bb_remote_last = fm1_ms;
        if (cmd == 1u) {
            ed_b(1); ed_b(bb_remote_token); ed_b(BB_SCREEN_W); ed_b(BB_SCREEN_H);
            ed_b(7); ed_b(14); ed_b(27);
            bb_put32(BB_APP_LO); bb_put32(BB_APP_HI);
            ed_str(FELUCCA_ID, 20);
            ed_str(BB_SOURCE_SHA, 64);
        } else if (cmd == 4u) {
            bb_put32(fm1_ms); bb_put32(felucca_dbg.boots); bb_put32(audio_halves);
            bb_put32(felucca_dbg.late); bb_put32(felucca_dbg.ui_frames);
            bb_put32(fm1_lcd_timeouts); bb_put32(song.cpu_q8);
            bb_put32(fm1_boot.p3_rst); bb_put32(flash_ok);
        } else if (cmd == 7u && p[5] == 1u) {
            uint32_t offset = bb_get21(p + 6), count = sizeof bb_screen - offset;
            const uint8_t *data = (const uint8_t *)bb_screen + offset;
            if (count > 256u) count = 256u;
            ed_b(count); ed_b(count >> 7);
            for (k = 0; k < count; k += 7u) {
                uint32_t j, m = 0, lim = count - k > 7u ? 7u : count - k;
                for (j = 0; j < lim; j++) m |= (uint32_t)(data[k + j] >> 7) << j;
                ed_b(m);
                for (j = 0; j < lim; j++) ed_b(data[k + j]);
            }
        } else if (cmd == 8u) {
            for (k = 0; k < 41u; k++) {
                uint32_t c, r, v = 0;
                for (c = 0; c < FM1_NCOL; c++)
                    for (r = 1; r < 5u; r++)
                        if (FM1_KEYMAP[r][c] == (int32_t)k) {
                            uint32_t bit = 1u << r;
                            v = fm1_led[c] & bit ? 127u : fm1_led_breath[c] & bit ? 64u :
                                fm1_led_mid[c] & bit ? 32u : fm1_led_dim[c] & bit ? 8u : 0u;
                        }
                ed_b(v);
            }
        }
    }
    ed_send();
    ota_frame_done();
}

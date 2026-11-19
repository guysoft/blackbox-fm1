/* SPDX-License-Identifier: GPL-3.0-only */
/* Execute the actual firmware remote handler with a host wire and logical inputs. */
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define BB_APP_LO 0x6000u
#define BB_APP_HI 0x9F000u
#define BB_SOURCE_SHA "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
#define FELUCCA_ID "BlackBox_950"
#define FM1_NCOL 11
#include "../../firmware/boards/blackbox/remote_state.h"
static struct { uint32_t notes, buttons, pressed, released, notes_pressed, note_t0[27]; int16_t enc_steps[7]; } fm1_in;
static struct { uint32_t boots, late, ui_frames; } felucca_dbg;
static struct { uint32_t p3_rst; } fm1_boot;
static struct { uint32_t cpu_q8; } song;
static struct { uint32_t force; } ui;
static uint32_t bb_remote_buttons, bb_remote_notes, bb_physical_buttons;
static uint32_t fm1_ms, audio_halves, fm1_lcd_timeouts, flash_ok = 1;
static uint8_t fm1_led[11], fm1_led_dim[11], fm1_led_breath[11], fm1_led_mid[11];
static const int8_t FM1_KEYMAP[6][11] = {{0}};
static uint8_t wire[664], ed_out[664], input[640];
static uint32_t ed_n, wire_n, input_n;
static int ready;
static uint32_t fm1__lock(void) { return 0; }
static void fm1__unlock(uint32_t f) { (void)f; }
static uint32_t fm1_ticks(void) { return fm1_ms * 24000u; }
static int32_t clamp(int32_t a, int32_t lo, int32_t hi) { return a < lo ? lo : a > hi ? hi : a; }
static void bb_merge_inputs(void)
{
    uint32_t b = bb_remote_buttons | bb_physical_buttons;
    fm1_in.pressed |= b & ~fm1_in.buttons;
    fm1_in.released |= fm1_in.buttons & ~b;
    fm1_in.buttons = b;
    fm1_in.notes_pressed |= bb_remote_notes & ~fm1_in.notes;
    fm1_in.notes = bb_remote_notes;
}
static int ota_frame_get(const uint8_t **p, uint32_t *n)
{
    *p = input; *n = input_n; return ready;
}
static void ota_frame_done(void) { ready = 0; }
static void ed_begin(uint32_t cmd)
{
    ed_out[0] = 0xF0; ed_out[1] = 0x7D; ed_out[2] = 0x46;
    ed_out[3] = 0x4C; ed_out[4] = (uint8_t)cmd; ed_n = 5;
}
static void ed_b(uint32_t v) { assert(ed_n < sizeof ed_out - 1u); ed_out[ed_n++] = v & 127u; }
static void ed_str(const char *s, uint32_t n)
{
    uint32_t k;
    for (k = 0; k < n && s[k]; k++) ed_b((uint8_t)s[k]);
    ed_b(0);
}
static void ed_send(void)
{
    assert(!ready); /* A host may send its next request as soon as F7 is visible. */
    ed_out[ed_n++] = 0xF7; memcpy(wire, ed_out, ed_n); wire_n = ed_n;
}
#if BLACKBOX_BLE
#define RING_PUBLISH() __asm__ volatile("" ::: "memory")
#include "../../firmware/boards/blackbox/ble_io.h"
static bb_ble_io_t bb_ble_io;
static uint32_t bb_ble_status[16];
static uint32_t bb_ble_cal_diag[32];
static uint32_t bb_ble_rf_diag[20];
static uint8_t ble_wire[664];
static uint32_t ble_wire_n;
static void bb_ble_update_status(void) {}
static void bb_ble_send(const uint8_t *p, uint32_t n)
{
    assert(n <= sizeof ble_wire);
    memcpy(ble_wire, p, n); ble_wire_n = n;
}
#endif
#include "../../firmware/src/blackbox_remote.c"
#if BB_TEST_EDITOR_DISPATCH
static uint32_t editor_calls;
static struct { uint32_t last_ms; } ed_w;
static void ed_sync(void) {}
static void ed_handle(const uint8_t *p, uint32_t n) { (void)p; (void)n; editor_calls++; }
#define ED_HDR0 0x7D
#define ED_HDR1 0x46
#define ED_HDR2 0x4C
#define ED_SMP_BEGIN 32u
#include "editor_dispatch.inc"
#endif

static void send(uint8_t cmd, const uint8_t *p, uint32_t n)
{
    input[0] = 0x7D; input[1] = input[2] = 0x42; input[3] = cmd;
    memcpy(input + 4, p, n); input_n = n + 4; ready = 1; wire_n = 0;
    bb_remote_service();
    assert(!ready && wire_n >= 7 && wire[4] == cmd && wire[wire_n - 1u] == 0xF7);
}
int main(void)
{
    uint8_t a[8] = {17};
    uint32_t seed = 1, k;
    fm1_ms = 10;
    send(1, a, 1);
    assert(wire[5] == 0 && wire[6] == 1 && wire[7] == 17);
    a[1] = 40; a[2] = 1;
    send(2, a, 3);
    assert(wire[5] == 0 && fm1_in.notes == (1u << 26));
    a[1] = 41;
    send(2, a, 3);
    assert(wire[5] == 1 && fm1_in.notes == (1u << 26));
    a[1] = 8;
    bb_physical_buttons = 1u << 8;
    send(2, a, 3);
    a[2] = 0;
    send(2, a, 3);
    assert(fm1_in.buttons == (1u << 8)); /* remote release never releases physical hold */
    a[1] = 6; a[2] = 65;
    send(3, a, 3);
    assert(wire[5] == 0 && fm1_in.enc_steps[6] == 1);
    a[1] = 7;
    send(3, a, 3);
    assert(wire[5] == 1);
    a[1] = 1; a[2] = 127; a[3] = 7;
    send(9, a, 4);
    assert(bb_master_owned && bb_remote_master == 1023);
    bb_capture_fill(0, 0, 240, 240, 0xF81F);
    a[1] = 0;
    send(7, a, 2);
    assert(bb_screen_frozen);
    a[1] = 1; a[2] = a[3] = a[4] = 0;
    send(7, a, 5);
    assert(wire[5] == 0 && (wire[6] | wire[7] << 7) == 256);
    fm1_ms += 2001;
    bb_remote_service();
    assert(!bb_remote_token && !bb_remote_notes && !bb_master_owned && !bb_screen_frozen);
    assert(fm1_in.buttons == bb_physical_buttons);
#if BB_TEST_EDITOR_DISPATCH
    {
        /* Poll sees nothing; remote request then arrives during UI work.
         * The later editor/OTA dispatch must not consume it as unknown OTA. */
        uint32_t ota_calls = 0;
        assert(!bb_remote_service());
        input[0] = 0x7D; input[1] = input[2] = 0x42; input[3] = 1; input[4] = 17;
        input_n = 5; ready = 1; wire_n = 0;
        if (ed_service()) { ota_calls++; ota_frame_done(); }
        assert(!ready && wire_n && wire[4] == 1 && !wire[5]);
        assert(!ota_calls && !editor_calls);
        input[0] = ED_HDR0; input[1] = ED_HDR1; input[2] = ED_HDR2; input[3] = 1;
        input_n = 4; ready = 1;
        assert(!ed_service() && !ready && editor_calls == 1);
        input[0] = 0; ready = 1;
        assert(ed_service() && ready); /* Real OTA namespace remains held. */
        ota_frame_done();
        a[0] = 17; send(6, a, 1);
    }
#endif
#if BLACKBOX_BLE
    {
        uint8_t hello[] = {0x7D, 0x42, 0x42, 1, 17};
        uint8_t key[] = {0x7D, 0x42, 0x42, 2, 17, 14, 1};
        uint8_t screen[] = {0x7D, 0x42, 0x42, 7, 17, 0};
        a[0] = 17;
        send(1, a, 1);
        bb_remote_handle(hello, sizeof hello, 3);
        assert(ble_wire[5] == 5 && bb_remote_source == 1); /* Cannot steal USB. */
        send(6, a, 1);
        bb_remote_handle(hello, sizeof hello, 3);
        assert(ble_wire[5] == 0 && bb_remote_source == 3);
        assert(ble_wire_n == 102); /* Full HELLO, not a truncated BLE response. */
        bb_remote_handle(key, sizeof key, 3);
        assert(fm1_in.notes == 1);
        {
            uint8_t heartbeat[] = {0x7D, 0x42, 0x42, 5, 17};
            uint32_t repeat;
            bb_master_owned = 1;
            for (repeat = 0; repeat < 4; repeat++) {
                fm1_ms++;
                bb_remote_handle(hello, sizeof hello, 3);
                assert(ble_wire[5] == 0 && !bb_ble_io.lost);
                assert(bb_remote_token == 17 && bb_remote_source == 3);
                assert(fm1_in.notes == 1 && bb_master_owned);
                assert(bb_remote_last == fm1_ms);
                bb_ble_remote_service(); /* Later main-loop work must keep the new session. */
                bb_remote_handle(heartbeat, sizeof heartbeat, 3);
                assert(ble_wire[5] == 0);
            }
        }
        a[0] = 0;
        send(4, a, 1);
        assert(wire[5] == 0 && bb_remote_source == 3 && fm1_in.notes == 1);
        send(10, a, 1);
        assert(wire[5] == 0 && bb_remote_source == 3);
        bb_ble_cal_diag[0] = 2;
        send(11, a, 1);
        assert(wire_n == 167 && wire[5] == 0 && wire[6] == 2 && bb_remote_source == 3);
        bb_ble_rf_diag[0] = 1;
        send(12, a, 1);
        assert(wire_n == 107 && wire[5] == 0 && wire[6] == 1 && bb_remote_source == 3);
        {
            uint8_t diagnostic[] = {0x7D, 0x42, 0x42, 11, 17};
            bb_remote_handle(diagnostic, sizeof diagnostic, 3);
            assert(ble_wire[5] == 3 && bb_remote_source == 3);
            diagnostic[3] = 12;
            bb_remote_handle(diagnostic, sizeof diagnostic, 3);
            assert(ble_wire[5] == 3 && bb_remote_source == 3);
        }
        a[0] = 17;
        a[1] = 14; a[2] = 0;
        send(2, a, 3);
        assert(wire[5] == 2 && fm1_in.notes == 1);
        bb_remote_handle(screen, sizeof screen, 3);
        assert(ble_wire[5] == 3 && !bb_screen_frozen);
        bb_ble_io.release_panel = 1;
        bb_ble_remote_service();
        assert(!bb_remote_source && !bb_remote_token && !fm1_in.notes);
        assert(fm1_in.buttons == bb_physical_buttons);
        {
            /* A new token on the same link resets panel holds, not the link.
             * Old-token requests fail, and real RELEASE still clears MIDI. */
            uint8_t next[] = {0x7D, 0x42, 0x42, 1, 19};
            uint8_t heartbeat[] = {0x7D, 0x42, 0x42, 5, 19};
            uint8_t release[] = {0x7D, 0x42, 0x42, 6, 19};
            bb_ble_io.lost = 0;
            bb_remote_handle(hello, sizeof hello, 3);
            bb_remote_handle(key, sizeof key, 3);
            assert(fm1_in.notes == 1);
            bb_remote_handle(next, sizeof next, 3);
            assert(ble_wire[5] == 0 && !bb_ble_io.lost && !fm1_in.notes);
            assert(bb_remote_token == 19 && bb_remote_source == 3);
            bb_remote_handle(key, sizeof key, 3);
            assert(ble_wire[5] == 2 && !fm1_in.notes);
            bb_ble_remote_service();
            bb_remote_handle(heartbeat, sizeof heartbeat, 3);
            assert(ble_wire[5] == 0);
            bb_remote_handle(release, sizeof release, 3);
            assert(ble_wire[5] == 0 && bb_ble_io.lost && !bb_remote_token);
        }
        send(1, a, 1);
        send(10, a, 1);
        assert(wire_n == 87 && wire[5] == 0);
        send(6, a, 1);
    }
#endif
    /* Random malformed requests run through the real bounds checks under ASan/UBSan. */
    for (k = 0; k < 20000u; k++) {
        uint32_t j, n;
        seed = seed * 1664525u + 1013904223u;
        n = (seed >> 24) % 8u;
        for (j = 0; j < n; j++) {
            seed = seed * 1664525u + 1013904223u; a[j] = (uint8_t)(seed >> 25);
        }
        send((uint8_t)((seed >> 16) % 13u), a, n);
    }
    return 0;
}

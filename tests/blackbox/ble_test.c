/* SPDX-License-Identifier: GPL-3.0-only */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define RING_PUBLISH() __asm__ volatile("" ::: "memory")
#include "../../firmware/boards/blackbox/ble_calibration.h"
#include "../../firmware/boards/blackbox/ble_io.h"
#define BLE_API static
#include "../../firmware/third_party/optimist_ble/src/ble_midi.c"

static uint32_t add_record(uint8_t *p, uint32_t at, uint32_t id, const uint8_t *data, uint32_t n)
{
    p[at] = (uint8_t)bb_ble_crc16(data, n);
    p[at + 1] = (uint8_t)id;
    p[at + 2] = (uint8_t)((id >> 8) | (n & 15u) << 4);
    p[at + 3] = (uint8_t)(n >> 4);
    memcpy(p + at + 4, data, n);
    return at + 4u + n;
}
static void calibration(void)
{
    uint8_t sector[4096], x187[68] = {0}, small[20] = {1, 2, 3};
    uint32_t at = 4, i;
    uint16_t crc = bb_ble_crc16(x187, 64);
    bb_ble_calibration_t out, previous;
    memset(sector, 255, sizeof sector);
    memcpy(sector, "\x55\xaa\xaa\x55", 4);
    x187[64] = (uint8_t)crc; x187[65] = (uint8_t)(crc >> 8);
    at = add_record(sector, at, 106, small, 2);
    at = add_record(sector, at, 107, small, 7);
    at = add_record(sector, at, 108, small, 20);
    at = add_record(sector, at, 187, x187, 68);
    assert(bb_ble_calibration_parse(sector, sizeof sector, &out) == 15);
    previous = out;
    sector[at] = 1; /* Corrupt tail must refuse the entire set. */
    assert(!bb_ble_calibration_parse(sector, sizeof sector, &out));
    assert(!memcmp(&out, &previous, sizeof out));
    sector[at] = 255;
    sector[at - 4] ^= 1;
    assert(!bb_ble_calibration_parse(sector, sizeof sector, &out));
    assert(!bb_ble_calibration_parse(0, 0, &out));
    assert(!bb_ble_calibration_parse(sector, sizeof sector, 0));
    for (i = 0; i < at; i++) assert(bb_ble_calibration_parse(sector, i, &out) != 15);
}
static uint32_t packet(uint32_t cin, uint32_t a, uint32_t b, uint32_t c)
{
    return cin | a << 8 | b << 16 | c << 24;
}
static void framing(void)
{
    bb_ble_io_t io = {0};
    uint32_t i, pkt;
    const uint8_t hello[] = {0xF0, 0x7D, 0x42, 0x42, 1, 42, 0xF7};
    bb_ble_io_push(&io, 0x123);
    assert(!bb_ble_io_pop(&io, &pkt));
    io.ready = 1;
    for (i = 0; i < BB_BLE_QUEUE; i++) bb_ble_io_push(&io, i);
    for (i = 0; i < BB_BLE_QUEUE; i++) { assert(bb_ble_io_pop(&io, &pkt)); assert(pkt == i); }
    assert(!bb_ble_io_pop(&io, &pkt));
    assert(bb_ble_io_reply(&io, hello, sizeof hello));
    for (i = io.tr; i < io.tw; i++) assert(bb_ble_io_sysex(&io, io.tx[i % BB_BLE_QUEUE]));
    assert(io.control_n == 5 && !memcmp(io.control, hello + 1, 5));
    io.control_n = 0;
    /* Stock OTA and ROM-entry SysEx are not delivered to the remote handler. */
    bb_ble_io_sysex(&io, packet(4, 0xF0, 0x22, 0x24));
    bb_ble_io_sysex(&io, packet(7, 0x35, 0x7F, 0xF7));
    assert(!io.control_n);
    bb_ble_io_byte(&io, 0xF0);
    for (i = 0; i < 100; i++) bb_ble_io_byte(&io, 1);
    bb_ble_io_byte(&io, 0xF7);
    assert(!io.control_n);
    bb_ble_io_sysex(&io, packet(4, 0xF0, 0x7D, 0x42));
    bb_ble_io_byte(&io, 0x90); /* Status aborts an incomplete SysEx. */
    bb_ble_io_byte(&io, 0xF7);
    assert(!io.control_n);
    bb_ble_io_lost(&io);
    assert(io.lost && !io.ready && io.tr == io.tw);
    bb_ble_io_reset_rx(&io);
    assert(!io.pos && !io.control_n && io.rr == io.rw);
    memset(&io, 0, sizeof io);
    io.ready = 1;
    io.rw = io.rr = 0xFFFFFFF0u;
    for (i = 0; i <= BB_BLE_QUEUE; i++) bb_ble_io_push(&io, i);
    assert(io.fault && io.lost && io.drops == 1);
    io.tr = 0; io.tw = 63; io.fault = io.lost = 0;
    assert(!bb_ble_io_reply(&io, hello, sizeof hello));
    assert(io.tw == 63 && io.fault); /* Never publish half a reply. */
}
struct roundtrip {
    bb_ble_io_t io;
    uint8_t bytes[192];
    uint32_t n;
};
static void collect(void *ctx, uint32_t pkt, uint16_t ts)
{
    struct roundtrip *r = ctx;
    uint32_t i, count = BM_CIN_LEN[pkt & 15u];
    (void)ts;
    assert(r->n + count <= sizeof r->bytes);
    for (i = 0; i < count; i++) r->bytes[r->n++] = (uint8_t)(pkt >> (8u * (i + 1u)));
    bb_ble_io_sysex(&r->io, pkt);
}
static void midi_roundtrip(void)
{
    uint8_t msg[105], buffer[20];
    struct ble_midi_enc enc = {0};
    struct ble_midi_dec dec = {0};
    bb_ble_io_t io = {0};
    struct roundtrip received = {0};
    uint32_t i;
    msg[0] = 0xF0; msg[1] = 0x7D; msg[2] = msg[3] = 0x42; msg[4] = 1;
    for (i = 5; i < sizeof msg - 1u; i++) msg[i] = (uint8_t)(i & 127u);
    msg[sizeof msg - 1u] = 0xF7;
    io.ready = 1;
    assert(bb_ble_io_reply(&io, msg, sizeof msg));
    ble_midi_dec_reset(&dec);
    ble_midi_enc_reset(&enc);
    /* Minimum MTU 23 -> 20-byte notifications, including multi-packet SysEx. */
    while (io.tr != io.tw) {
        ble_midi_enc_begin(&enc, buffer, sizeof buffer);
        while (io.tr != io.tw && ble_midi_enc_add(&enc, io.tx[io.tr % BB_BLE_QUEUE], 8191) == 1) io.tr++;
        assert(ble_midi_enc_len(&enc) > 0);
        assert(ble_midi_dec(&dec, buffer, ble_midi_enc_len(&enc), collect, &received));
    }
    assert(received.n == sizeof msg && !memcmp(received.bytes, msg, sizeof msg));
    assert(!received.io.control_n); /* Oversized remote request is bounded/discarded. */
    memset(&received, 0, sizeof received);
    ble_midi_dec_reset(&dec);
    ble_midi_enc_begin(&enc, buffer, sizeof buffer);
    for (i = 0; i < 3; i++) assert(ble_midi_enc_add(&enc, packet(9, 0x90, 60 + i, 96), 8191 + i) == 1);
    assert(ble_midi_dec(&dec, buffer, ble_midi_enc_len(&enc), collect, &received));
    assert(received.n == 9);
    for (i = 0; i < 3; i++) {
        assert(received.bytes[i * 3] == 0x90 && received.bytes[i * 3 + 1] == 60 + i);
        assert(received.bytes[i * 3 + 2] == 96);
    }
}
int main(int argc, char **argv)
{
    uint32_t i, seed = 42;
    calibration();
    framing();
    midi_roundtrip();
    if (argc == 2) {
        uint8_t sector[4096];
        bb_ble_calibration_t cal;
        FILE *f = fopen(argv[1], "rb");
        assert(f && !fseek(f, 0xA3000, SEEK_SET));
        assert(fread(sector, 1, sizeof sector, f) == sizeof sector);
        fclose(f);
        assert(bb_ble_calibration_parse(sector, sizeof sector, &cal) == 15);
    }
    for (i = 0; i < 20000u; i++) {
        bb_ble_io_t io = {0};
        bb_ble_calibration_t cal;
        uint8_t bytes[256];
        uint32_t j;
        for (j = 0; j < sizeof bytes; j++) { seed = seed * 1664525u + 1013904223u; bytes[j] = (uint8_t)(seed >> 24); }
        bb_ble_calibration_parse(bytes, i % sizeof bytes, &cal);
        for (j = 0; j < sizeof bytes; j++) bb_ble_io_byte(&io, bytes[j]);
        assert(io.control_n <= sizeof io.control);
    }
    puts("BLE calibration, bounded queues, namespace isolation and MIDI framing passed");
    return 0;
}

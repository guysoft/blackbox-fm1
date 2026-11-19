/* SPDX-License-Identifier: GPL-3.0-only */
/* Real synth/input sources, stub hardware. Not RF or physical audio evidence. */
#define BLACKBOX_BLE 1
#define RING_PUBLISH() __asm__ volatile("" ::: "memory")
#include "../../firmware/boards/blackbox/ble_io.h"
static bb_ble_io_t bb_ble_io;
static volatile uint32_t bb_ble_discard_until;
static volatile uint8_t bb_ble_discarding;
#define UI_TEST_NO_MAIN 1
#include "../ui_test.c"
#include <assert.h>

static void note(uint32_t source, uint32_t pitch, uint32_t down)
{
    assert(midi_enqueue((down ? 9u : 8u) | (down ? 0x90u : 0x80u) << 8 |
                        pitch << 16 | (down ? 96u : 0u) << 24, source));
    events_block(CTL);
}
static int gate(uint32_t pitch)
{
    uint32_t i;
    for (i = 0; i < NVOICE; i++)
        if (trk[0].v[i].active && trk[0].v[i].gate && trk[0].v[i].note == pitch) return 1;
    return 0;
}
int main(void)
{
    ui_power_on();
    song.g[G_ROUTE] = 0;
    events_block(CTL);
    note(1, 60, 1);
    note(3, 60, 1);
    assert(midi_notes[0][60] && midi_notes[16][60] && midi_owners[0] == 2);
    assert(midi_enqueue(0xBu | 0xB0u << 8 | 64u << 16 | 127u << 24, 3));
    events_block(CTL);
    note(3, 64, 1);
    note(3, 64, 0);
    assert((midi_notes[16][64] & MIDI_PEDAL_NOTE) && gate(64));
    bb_ble_io.release_audio = 1;
    bb_ble_discard_until = mi_w;
    bb_ble_discarding = 1;
    events_block(CTL);
    assert(midi_notes[0][60] && !midi_notes[16][60] && midi_owners[0] == 1 && gate(60));
    assert(!midi_notes[16][64] && !gate(64) && !midi_ch[16].pedal);
    /* Old BLE note-on already in shared queue at loss must not reappear after
     * cleanup. New connection traffic after the cutoff and USB are retained. */
    assert(midi_enqueue(9u | 0x90u << 8 | 65u << 16 | 96u << 24, 3));
    assert(midi_enqueue(9u | 0x90u << 8 | 67u << 16 | 96u << 24, 1));
    bb_ble_discard_until = mi_w;
    bb_ble_discarding = 1;
    bb_ble_io.release_audio = 1;
    assert(midi_enqueue(9u | 0x90u << 8 | 69u << 16 | 96u << 24, 3));
    events_block(CTL);
    assert(!gate(65) && !midi_notes[16][65]);
    assert(midi_notes[0][67] && midi_notes[16][69] && gate(69));
    assert(!bb_ble_discarding);
    fm1_in.notes = 1u;
    events_block(CTL);
    {
        uint32_t local = kb_note[0];
        note(3, local, 1);
        bb_ble_io.release_audio = 1;
        events_block(CTL);
        assert(gate(local)); /* Physical panel ownership survives. */
        fm1_in.notes = 0;
        events_block(CTL);
        assert(!gate(local));
    }
    puts("BLE sustain/USB overlap, physical holds and stale-queue cleanup passed");
    return 0;
}

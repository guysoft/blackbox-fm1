/* SPDX-License-Identifier: GPL-3.0-only */
/* Blackbox TX bring-up from the V20 hardware mapping documented by Juice-Box.
 * Synth output only: ADC/guitar input is deliberately not enabled yet. */
#pragma once
#include <stdint.h>
#include "fm1_cc.h"
#include "fm1_gpio.h"
#include "fm1_time.h"
#include "fm1_irq.h"
#define BB_AU16(off) (*(volatile uint16_t *)(0x12E00u + (off)))
#define BB_AU8(off) (*(volatile uint8_t *)(0x12E00u + (off)))
#define BB_AU32(off) (*(volatile uint32_t *)(0x12E00u + (off)))
#define FM1_AUDIO_HALF 0x10u
static uint32_t bb_audio_half;
static uint32_t bb_audio_next;
static void bb_audio_pin(uint32_t pin, int on)
{
    uint32_t m = 1u << pin;
    FM1_PR(FM1_PA, FM1_DIE) |= m;
    if (on) FM1_PR(FM1_PA, FM1_OUT) |= m;
    else FM1_PR(FM1_PA, FM1_OUT) &= ~m;
    FM1_PR(FM1_PA, FM1_DIR) &= ~m;
}
static void fm1_audio_init(int32_t *buf, uint32_t half_words, void (*isr)(void), uint32_t prio)
{
    bb_audio_pin(9, 0);
    fm1_delay_ms(5);
    BB_AU16(0) = BB_AU16(4) = 0;
    BB_AU8(8) = BB_AU8(12) = 0;
    *(volatile uint32_t *)0x51030u = (*(volatile uint32_t *)0x51030u & ~0xC0u) | 0x40u;
    BB_AU8(12) = 0x83u;
    bb_audio_pin(4, 1);
    bb_audio_pin(5, 1);
    bb_audio_pin(6, 1);
    bb_audio_pin(7, 1);
    BB_AU16(0) = 0x180u;
    BB_AU16(0x20) = (uint16_t)half_words;
    *(volatile uint32_t *)0x10014u &= 0xFFFFF0FFu;
    BB_AU32(0x10) = (uint32_t)(uintptr_t)buf;
    BB_AU16(4) = 5u; /* channel 0 TX, 24-bit RJ */
    BB_AU8(8) = 15u;
    bb_audio_half = 0;
    bb_audio_next = 0;
    fm1_irq_attach(FM1_IRQ_ALNK0, isr, prio);
    BB_AU16(0) |= 0x800u;
    fm1_delay_ms(5);
    bb_audio_pin(9, 1);
}
FM1_INLINE uint8_t fm1_audio_pending(void)
{
    uint8_t p = BB_AU8(8);
    if (p & FM1_AUDIO_HALF) {
        bb_audio_half = bb_audio_next;
        bb_audio_next ^= 1u;
        BB_AU8(8) = 1u; /* Ack before rendering so a new pending bit measures a missed deadline. */
    }
    return p;
}
FM1_INLINE void fm1_audio_ack_aux(uint8_t p) { (void)p; }
FM1_INLINE uint32_t fm1_audio_free_half(void) { return bb_audio_half; }
FM1_INLINE void fm1_audio_ack_half(void) {}
FM1_INLINE int bb_audio_late(void) { return (BB_AU8(8) & FM1_AUDIO_HALF) != 0; }
FM1_INLINE void fm1_audio_stop(void) { BB_AU16(0) &= ~0x800u; bb_audio_pin(9, 0); }

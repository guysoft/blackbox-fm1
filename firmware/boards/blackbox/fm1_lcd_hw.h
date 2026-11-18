/* SPDX-License-Identifier: MPL-2.0 */
/* Derived from felucca-bsp's FM-1 LCD transport, Copyright (C) 2026 Leo Kuroshita.
 * Blackbox wiring from OpenPocket / Juice-Box. PC7 is LED enable, NOT backlight. */
#pragma once
#include <stdint.h>
#include "fm1_cc.h"
#include "fm1_gpio.h"
#define BB_SPI(off) (*(volatile uint32_t *)(0x11D00u + (off)))
static uint32_t fm1_lcd_timeouts;
static void fm1_lcd_hw_init(void)
{
    uint32_t mask = (1u << 1) | (1u << 5) | (1u << 6) | (1u << 7);
    FM1_PR(FM1_PB, FM1_DIR) &= ~mask;
    FM1_PR(FM1_PB, FM1_DIE) |= mask;
    FM1_PR(FM1_PB, FM1_OUT) |= 1u << 1;
    *(volatile uint32_t *)0x51020u &= ~0x10u;
    BB_SPI(0) = 0x4021u;
    BB_SPI(4) = 4u;
}
static void fm1_lcd_backlight(uint32_t on) { (void)on; } /* Unknown physical backlight control. */
static void fm1_lcd_baud(uint32_t b) { BB_SPI(4) = b; }
static void fm1_lcd_wait(void)
{
    uint32_t n;
    for (n = 0; n < 4000000u && !(BB_SPI(0) & 0x8000u); n++) ;
    if (n == 4000000u) fm1_lcd_timeouts++;
    BB_SPI(0) |= 0x4000u;
}
static void fm1_lcd_deselect(void) { FM1_PR(FM1_PB, FM1_OUT) |= 1u << 1; }
static void fm1_lcd_send_cmd(uint8_t c)
{
    FM1_PR(FM1_PB, FM1_OUT) &= ~((1u << 1) | (1u << 5));
    BB_SPI(0) |= 0x4000u;
    BB_SPI(8) = c;
}
static void fm1_lcd_send_data(const void *p, uint32_t n)
{
    FM1_PR(FM1_PB, FM1_OUT) |= 1u << 5;
    FM1_PR(FM1_PB, FM1_OUT) &= ~(1u << 1);
    BB_SPI(0) |= 0x4000u;
    BB_SPI(12) = (uint32_t)(uintptr_t)p;
    BB_SPI(16) = n;
}

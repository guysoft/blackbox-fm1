/* SPDX-License-Identifier: MPL-2.0 */
/* ADC driver from felucca-bsp; Blackbox pins from Juice-Box's hardware mapping. */
#pragma once
#define fm1_adc_init fm1_unused_adc_init
#define FM1_ADC_BATT FM1_UNUSED_ADC_BATT
#define FM1_ADC_MASTER FM1_UNUSED_ADC_MASTER
#include "../../bsp/boards/fm1/fm1_adc.h"
#undef fm1_adc_init
#undef FM1_ADC_BATT
#undef FM1_ADC_MASTER
#define FM1_ADC_MASTER 2u
#define FM1_ADC_BATT 8u
#define BB_ADC_KEYS 9u

static void bb_analog_pin(uint32_t port, uint32_t pin)
{
    uint32_t m = 1u << pin;
    FM1_PR(port, FM1_DIE) &= ~m;
    FM1_PR(port, FM1_PU) &= ~m;
    FM1_PR(port, FM1_PD) &= ~m;
    FM1_PR(port, FM1_DIR) |= m;
}
static void fm1_adc_init(void)
{
    bb_analog_pin(FM1_PA, 10);
    bb_analog_pin(FM1_PC, 9);
    bb_analog_pin(FM1_PC, 10);
}

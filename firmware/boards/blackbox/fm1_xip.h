/* SPDX-License-Identifier: MPL-2.0 */
/* Derived from felucca-bsp, Copyright (C) 2026 Leo Kuroshita. */
#pragma once
#ifndef BB_XIP_DEFINED
#define BB_XIP_DEFINED
#include <stdint.h>
#include "fm1_cc.h"
#ifndef BB_APP_LO
#error "Select an inspected Blackbox flash profile"
#endif
#define FM1_XIP(off) (0x02000000u + (uint32_t)(off) - BB_APP_LO)
FM1_INLINE const uint8_t *fm1_xip_ptr(uint32_t off) { return (const uint8_t *)FM1_XIP(off); }
#endif

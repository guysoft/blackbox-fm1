/* SPDX-License-Identifier: GPL-3.0-only */
/* Exact 1 MiB IDs only. EB6014 was measured by the RAM reader on our V17 unit.
 * Recognition enables experimental OTA; it is not evidence of working writes.
 * Keep FM-1's allowlist and all stock Blackbox persistence regions unchanged. */
#pragma once
#include <stdint.h>

static int bb_flash_supported(uint32_t id)
{
    return id == 0x856014u || id == 0xB36014u || id == 0xEB6014u;
}

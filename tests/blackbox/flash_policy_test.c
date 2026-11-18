/* SPDX-License-Identifier: GPL-3.0-only */
#include <assert.h>
#include "../../firmware/boards/blackbox/flash_policy.h"

int main(void)
{
    assert(bb_flash_supported(0xEB6014u));
    assert(bb_flash_supported(0x856014u));
    assert(bb_flash_supported(0xB36014u));
    assert(!bb_flash_supported(0));
    assert(!bb_flash_supported(0xFFFFFFu));
    assert(!bb_flash_supported(0xEB6015u));
    assert(!bb_flash_supported(0xEB4014u));
    return 0;
}

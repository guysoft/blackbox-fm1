/* SPDX-License-Identifier: GPL-3.0-only */
/* Exercise the real loader against stock and our target package; never USB hardware. */
#define BLACKBOX 1
#define main fm1_loader_test_unused
#include "../ldr_test.c"
#undef main
#include <assert.h>

int main(int argc, char **argv)
{
    static uint8_t before[0x100000];
    uint8_t *old;
    uint32_t ofo, nfo, i;
    size_t olen;
    int rc;
    assert(argc == 3);
    old = load_logical(argv[1], &olen);
    logical = load_logical(argv[2], &logical_len);
    ofo = flash_off(old); nfo = flash_off(logical);
    for (i = 0; i < sizeof nor; i++) nor[i] = (uint8_t)(i * 13u);
    memcpy(nor, old + ofo, BB_APP_HI);
    memcpy(before, nor, sizeof nor);
    /* Whole-image corruption must be rejected before the first erase. */
    logical[nfo + BB_APP_LO + 512] ^= 1u;
    rc = ldr_session();
    assert(rc == -12 && erases == 0 && !memcmp(before, nor, sizeof nor));
    logical[nfo + BB_APP_LO + 512] ^= 1u;
    set_fl_size(logical, BB_APP_HI - 4096u);
    rc = ldr_session();
    assert(rc == -14 && erases == 0);
    set_fl_size(logical, BB_APP_HI);
    {
        uint8_t e[32];
        memcpy(e, nor + 96, 32);
        ota_jl_enc(e, 32);
        ota_wr32(e + 4, BB_APP_LO ^ 0x2000u);
        ota_wr16(e, ota_crc16(e + 2, 30, 0));
        ota_jl_enc(e, 32);
        memcpy(nor + 96, e, 32);
        assert(ldr_session() == -15 && erases == 0);
        memcpy(nor, before, BB_APP_LO);
    }
    flip_addr = nfo + BB_APP_LO + 0x10000u; flip_on = 2; flip_seen = 0;
    rc = ldr_session();
    assert(rc == 0 && flip_seen == 3 && f0_asked && record_cleared);
    assert(!memcmp(nor, before, BB_APP_LO));
    assert(!memcmp(nor + BB_APP_LO, logical + nfo + BB_APP_LO, BB_APP_HI - BB_APP_LO));
    assert(!memcmp(nor + BB_APP_HI, before + BB_APP_HI, sizeof nor - BB_APP_HI));
    assert(bad_range == 0);
    flip_addr = 0xFFFFFFFFu;
    erases = 0;
    assert(ldr_session() == 0 && erases == 0);
    printf("Blackbox loader: corruption, layout refusal, transfer retry, install, preserved head/data, repeat PASS\n");
    free(old); free(logical);
    return 0;
}

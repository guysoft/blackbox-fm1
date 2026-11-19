/* SPDX-License-Identifier: GPL-3.0-only */
/* Execute the actual boot reader; no flash, IRQ or radio access on the host. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../../firmware/boards/blackbox/ble_calibration.h"
#define BB_APP_LO 0x4000u
#define BB_APP_HI 0xA3000u
#define FL_FAR(fn) fn
#define SFC_CON 0x12345678u
static uint8_t flash[4096];
static int flash_ok = 1, fail_at = -1;
static uint32_t reads, feeds, starts, restored, controls;
static uint32_t bb_ble_status[16], bb_ble_cal_diag[32];
static uint8_t bb_ble_uid[16];
static int bad_uid;
static struct { uint32_t fault; } bb_ble_io;
static uint32_t irq_save(void) { return 42; }
static void irq_restore(uint32_t f) { assert(f == 42); restored++; }
static void fm1_wdt_feed(void) { feeds++; }
static void bb_ble_start(const bb_ble_calibration_t *cal) { (void)cal; starts++; }
static uint32_t fl_jedec_ram(void) { return 0xEB6014u; }
static int fl_uid_ram(uint8_t *dst)
{
    uint32_t i;
    for (i = 0; i < 16u; i++) dst[i] = bad_uid ? 255u : (uint8_t)i;
    return 0;
}
static int fl_read_ram(uint32_t off, uint8_t *dst, uint32_t n)
{
    if ((off == 0 || off == BB_APP_LO) && n == 32u) {
        memset(dst, off ? 0x42 : 0x24, n); controls++; return 0;
    }
    assert(off >= 0xA3000u && off + n <= 0xA4000u && n == 256u);
    reads++;
    if ((int)(off - 0xA3000u) == fail_at) return -2;
    memcpy(dst, flash + off - 0xA3000u, n);
    return 0;
}
#include "../../firmware/boards/blackbox/ble_storage.h"
static void reset(void)
{
    memset(bb_ble_status, 0, sizeof bb_ble_status);
    memset(bb_ble_cal_diag, 0, sizeof bb_ble_cal_diag);
    bb_ble_io.fault = 0;
    reads = feeds = starts = restored = controls = 0;
}
static uint32_t record(uint32_t at, uint32_t id, uint32_t n)
{
    memset(flash + at + 4, 0, n);
    flash[at] = 0; /* CRC16 of zeros, including the inner 187 CRC. */
    flash[at + 1] = (uint8_t)id;
    flash[at + 2] = (uint8_t)(n << 4);
    flash[at + 3] = (uint8_t)(n >> 4);
    return at + 4u + n;
}
int main(int argc, char **argv)
{
    uint32_t at = 4, i, hash = 2166136261u;
    flash_ok = 0;
    bb_ble_boot();
    assert(bb_ble_io.fault == 5 && bb_ble_cal_diag[2] == 1 && !reads && !starts);
    reset(); flash_ok = 1; fail_at = 256;
    bb_ble_boot();
    assert(bb_ble_io.fault == 5 && bb_ble_cal_diag[2] == 2 && !starts);
    assert((int32_t)bb_ble_cal_diag[3] == -2 && bb_ble_cal_diag[4] == 0xA3100u);
    assert(bb_ble_cal_diag[5] == 256 && reads == 2 && restored == 5 + BLACKBOX_BLE_SELFCAL && feeds == 1);
    reset(); fail_at = -1;
    memset(flash, 255, sizeof flash);
#if BLACKBOX_BLE_SELFCAL
    flash[0] = 0; /* A malformed nonblank log is never silently replaced. */
#endif
    bb_ble_boot();
    assert(bb_ble_io.fault == 5 && bb_ble_cal_diag[2] == 3 && !starts);
    assert(bb_ble_cal_diag[8] == 1);
    reset();
    memcpy(flash, "\x55\xaa\xaa\x55", 4);
    at = record(at, 106, 2); at = record(at, 107, 7);
    at = record(at, 108, 20); at = record(at, 187, 68);
    flash[at] = 1; /* A bad trailing record must still stop startup. */
    bb_ble_boot();
    assert(bb_ble_io.fault == 5 && bb_ble_cal_diag[8] == 2 && !starts);
    assert(bb_ble_cal_diag[9] == at && bb_ble_cal_diag[14] == 15);
    reset(); flash[at] = 255;
    if (argc == 2) {
        FILE *f = fopen(argv[1], "rb");
        assert(f && !fseek(f, 0xA3000, SEEK_SET));
        assert(fread(flash, 1, sizeof flash, f) == sizeof flash);
        fclose(f);
    }
    for (i = 0; i < sizeof flash; i++) { hash ^= flash[i]; hash *= 16777619u; }
    bb_ble_boot();
    assert(!bb_ble_io.fault && bb_ble_status[1] == 15 && bb_ble_cal_diag[2] == 4 + BLACKBOX_BLE_SELFCAL);
    assert(bb_ble_cal_diag[1] == BLACKBOX_BLE_DIAGNOSTIC);
    assert(bb_ble_cal_diag[5] == 4096 && bb_ble_cal_diag[6] == 0x55AAAA55u);
    assert(bb_ble_cal_diag[7] == hash && !bb_ble_cal_diag[8]);
    assert(reads == 16 && feeds == 16 && restored == 19 + BLACKBOX_BLE_SELFCAL && controls == 2);
    assert(bb_ble_cal_diag[0] == 2 && bb_ble_cal_diag[28] == 0xEB6014u);
    assert(!bb_ble_cal_diag[16] && bb_ble_cal_diag[18] == 0x24242424u);
    assert(!bb_ble_cal_diag[22] && bb_ble_cal_diag[24] == 0x42424242u);
    assert(starts == !BLACKBOX_BLE_DIAGNOSTIC);
#if BLACKBOX_BLE_SELFCAL
    reset(); memset(flash, 255, sizeof flash);
    bb_ble_boot();
    assert(!bb_ble_io.fault && !bb_ble_status[1] && bb_ble_cal_diag[2] == 5);
    assert(bb_ble_cal_diag[29] == 1 && bb_ble_cal_diag[31] == 1);
    assert(starts == !BLACKBOX_BLE_DIAGNOSTIC);
    reset(); bad_uid = 1;
    bb_ble_boot();
    assert(bb_ble_io.fault == 7 && bb_ble_cal_diag[2] == 6 && !reads && !starts);
#endif
    printf("Boot reader passed; sector FNV1a=%08x, diagnostic=%d\n", hash, BLACKBOX_BLE_DIAGNOSTIC);
    return 0;
}

/* SPDX-License-Identifier: GPL-3.0-only */
/* V17 VM sector found in this unit's two matching full dumps. Read-only and
 * separate from st_read: never expose stock contents as Felucca settings. */
#pragma once
#if BB_APP_LO != 0x4000u || BB_APP_HI != 0xA3000u
#error "BLE calibration reader is qualified for the inspected V17 layout only"
#endif
static void bb_ble_flash_control(uint32_t off, uint32_t slot)
{
    uint8_t bytes[32];
    uint32_t i, hash = 2166136261u, f = irq_save();
    int rc = FL_FAR(fl_read_ram)(off, bytes, sizeof bytes);
    irq_restore(f);
    bb_ble_cal_diag[slot] = (uint32_t)rc;
    if (rc) return;
    for (i = 0; i < sizeof bytes; i++) { hash ^= bytes[i]; hash *= 16777619u; }
    bb_ble_cal_diag[slot + 1u] = hash;
    for (i = 0; i < 4u; i++)
        bb_ble_cal_diag[slot + 2u + i] = bytes[4u * i] | (uint32_t)bytes[4u * i + 1u] << 8 |
                                        (uint32_t)bytes[4u * i + 2u] << 16 |
                                        (uint32_t)bytes[4u * i + 3u] << 24;
}
static void bb_ble_boot(void)
{
    uint8_t sector[4096];
    bb_ble_calibration_t cal;
    uint32_t at, hash = 2166136261u;
    bb_ble_cal_diag[0] = 2; /* schema 2 adds raw boot/app control reads */
    bb_ble_cal_diag[1] = BLACKBOX_BLE_DIAGNOSTIC;
    bb_ble_status[15] = 0xA3000u;
    bb_ble_cal_diag[2] = 1; /* flash probe unavailable */
    if (!flash_ok) { bb_ble_io.fault = 5; return; }
    bb_ble_flash_control(0, 16);
    bb_ble_flash_control(BB_APP_LO, 22);
    {
        uint32_t f = irq_save();
        bb_ble_cal_diag[28] = FL_FAR(fl_jedec_ram)();
        irq_restore(f);
    }
#if BLACKBOX_BLE_SELFCAL
    {
        uint32_t i, f = irq_save(), uid_hash = 2166136261u;
        int rc = FL_FAR(fl_uid_ram)(bb_ble_uid);
        irq_restore(f);
        for (i = 1; i < sizeof bb_ble_uid && bb_ble_uid[i] == bb_ble_uid[0]; i++) ;
        if (rc || i == sizeof bb_ble_uid) {
            bb_ble_cal_diag[2] = 6; bb_ble_io.fault = 7; return;
        }
        for (i = 0; i < sizeof bb_ble_uid; i++) { uid_hash ^= bb_ble_uid[i]; uid_hash *= 16777619u; }
        bb_ble_cal_diag[29] = 1; bb_ble_cal_diag[30] = uid_hash;
    }
#endif
    for (at = 0; at < sizeof sector; at += 256u) {
        uint32_t i, f = irq_save();
        int rc;
        bb_ble_cal_diag[15] = SFC_CON;
        rc = FL_FAR(fl_read_ram)(0xA3000u + at, sector + at, 256u);
        irq_restore(f);
        bb_ble_cal_diag[2] = 2; /* raw read failed */
        bb_ble_cal_diag[3] = (uint32_t)rc;
        bb_ble_cal_diag[4] = 0xA3000u + at;
        if (rc) { bb_ble_io.fault = 5; return; }
        for (i = 0; i < 256u; i++) { hash ^= sector[at + i]; hash *= 16777619u; }
        bb_ble_cal_diag[5] = at + 256u;
        bb_ble_cal_diag[7] = hash;
        if (!at)
            bb_ble_cal_diag[6] = sector[0] | (uint32_t)sector[1] << 8 |
                                (uint32_t)sector[2] << 16 | (uint32_t)sector[3] << 24;
        fm1_wdt_feed();
    }
    bb_ble_cal_diag[2] = 3; /* parsing failed */
    bb_ble_status[1] = bb_ble_calibration_inspect(sector, sizeof sector, &cal, bb_ble_cal_diag + 8);
    if (bb_ble_status[1] != 15u) {
#if BLACKBOX_BLE_SELFCAL
        /* An explicit experimental build, not an automatic failure fallback.
         * SDK board constants match this V17 unit's original backup. Only a
         * completely erased VM qualifies; malformed nonblank logs still stop. */
        static const bb_ble_calibration_t defaults = {{11, 11}, {1, 7, 4, 7, 11, 1, 7}, {0}, {0}};
        for (at = 0; at < sizeof sector && sector[at] == 255u; at++) ;
        if (at != sizeof sector || bb_ble_cal_diag[16] || bb_ble_cal_diag[22]) {
            bb_ble_io.fault = 5; return;
        }
        cal = defaults;
#else
        bb_ble_io.fault = 5; return;
#endif
    }
    bb_ble_cal_diag[2] = 4; /* complete validated set */
#if BLACKBOX_BLE_SELFCAL
    bb_ble_cal_diag[2] = 5; /* measuring 187, not claiming stored calibration */
    bb_ble_cal_diag[31] = 1;
#endif
#if !BLACKBOX_BLE_DIAGNOSTIC
    bb_ble_start(&cal);
#endif
}

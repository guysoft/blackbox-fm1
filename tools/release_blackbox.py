#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Assemble public release files from a clean, tested build. Does not publish."""
import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

from blackbox import validate_artifacts
from source_fingerprint import LOCK, fingerprint, snapshot

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {"usb-only": "blackbox-v17", "ble-selfcal": "blackbox-v17-ble-selfcal"}


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root)


def add_bytes(archive, name, data, epoch):
    member = tarfile.TarInfo(name)
    member.size, member.mode, member.mtime = len(data), 0o644, epoch
    archive.addfile(member, io.BytesIO(data))


def copy_git_archive(archive, root, prefix, epoch, paths=()):
    raw = git("archive", "--format=tar", "HEAD", *paths, root=root)
    with tarfile.open(fileobj=io.BytesIO(raw)) as source:
        for entry in source:
            member = copy.copy(entry)
            member.name = f"{prefix}/{entry.name}"
            member.uid = member.gid = 0
            member.uname = member.gname = ""
            member.mtime = epoch
            archive.addfile(member, source.extractfile(entry) if entry.isfile() else None)


def source_archive(path, root, prefix, record, epoch):
    with path.open("xb") as output, gzip.GzipFile(fileobj=output, mode="wb", mtime=epoch, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            copy_git_archive(archive, root, prefix, epoch)
            for name in sorted(record["modules"]):
                copy_git_archive(archive, root / name, f"{prefix}/{name}", epoch)
            add_bytes(archive, f"{prefix}/{LOCK}",
                      (json.dumps(record, sort_keys=True, indent=2) + "\n").encode(), epoch)


def notes(version, manifest):
    return f"""# blackbox-fm1 {version} — experimental V17 + community BLE

Independent Felucca fork for the M-VAVE ANN Blackbox. Not an upstream-supported target.

## Hardware evidence and limitations

- First V17-profile installation on one Blackbox booted successfully. The user
  confirmed the physical UI, PARA role selection and audible output.
- Full unpaced screen captures and supervised software-only updates passed.
- Community BLE self-calibration, Linux advertising/GATT/panel MIDI, a one-minute
  chord/sustain traffic test, and reconnect passed. Android HELLO/heartbeats and
  rotation passed; the user reported working control.
- Fixed capture dispatch/RX-release races and premature interrupt-vector locking.
- Same-token HELLO is now idempotent; token rollover resets panel holds without
  invalidating the new session. This latest fix is host-tested, not yet hardware-tested.
- The exact CI-built assets below have **not** been flashed: the hardware pilot
  used earlier source fingerprints. Do not confuse build tests with hardware tests.
- **Automatic repeat flashing is disarmed.** Cold boot, long-duration/range/
  temperature behavior and formal BLE note-to-audio latency remain unqualified.
- Some cumulative deadline misses appeared during unobserved update/boot intervals;
  no new misses were observed during the documented traffic tests.
- Project/settings/sample persistence is disabled; edits do not survive power-off.
- OTA staging overwrites stock sound-bank bytes at `[0xE0000,0xE5000)`.
- Back up the entire device before installation. A stock `.fwsc` is not a full backup.
- Full stock flash restore remains untested. Prompt link-loss voice cleanup is
  inconclusive: observed disconnect exceeded the two-second panel lease.
- V20/V23 are build-tested only and are **not** covered by this V17 release.

## Files

- `*-v17-usb-only.fwsc`: V17 with radio disabled.
- `*-v17-ble-selfcal.fwsc`: explicitly selected experimental community BLE-MIDI,
  with startup measurements held in RAM and no calibration flash writes.
  Both identify as `{manifest['product']}`; use their variant manifests/checksums.
  Never install it on an FM-1 or assume compatibility with another Blackbox revision.
- `*-app.bin`, `*-loader.bin`: raw components, **not** standalone installation files.
- `*-source.tar.gz`: complete corresponding source, including the pinned BSP and
  engine submodules and a source-fingerprint lock for rebuilding without Git.
- `*-licenses.tar.gz`: licence texts, notices and sample attribution.
- `*-manifest.json` and `SHA256SUMS`: provenance and integrity.
- `blackbox-controls.png`: button cheat sheet.
- Android companion APK/source/releases are separate:
  https://github.com/guysoft/blackbox-companion-app

Source is GPL-3.0-only, with third-party licences retained. The Blackbox `.fwsc`
also retains donor boot/configuration material; upstream Felucca's “no vendor
material” claim does not apply to it. GPL does not relicense those retained bytes.
See LICENSING.md and CREDITS.md in the complete source.

Build on Linux x86-64: unpack the complete source, run `make setup`, then
`make build BOARD=blackbox-v17` and `make test`. For the BLE variant additionally
build with `BLE=1 BLE_SELFCAL=1`. Setup downloads pinned inputs;
it never installs system packages. This release does not include the stock donor
download or any per-device dump, preset export, identifiers or private IR files.

Source fingerprint: `{manifest['source_sha256']}`.
"""

def collect_variants(root, source_sha256):
    """Validate every input before creating any release output."""
    variants = {}
    for name, directory in VARIANTS.items():
        folder = root / "build" / directory
        manifest = json.loads((folder / "manifest.json").read_text())
        package = validate_artifacts(folder / "blackbox-fm1-950.fwsc", manifest, "blackbox-v17")
        if manifest["source_sha256"] != source_sha256:
            raise ValueError(f"{name}: source changed since build")
        if manifest.get("ble_diagnostic", False):
            raise ValueError(f"{name}: diagnostic image cannot be released")
        if name == "usb-only":
            if manifest.get("ble", False):
                raise ValueError("usb-only: radio unexpectedly present")
        elif not (manifest.get("ble") is True and manifest.get("ble_selfcal") is True and
                  manifest.get("ble_radio_enabled") is True and manifest.get("cpu2") is False):
            raise ValueError("ble-selfcal: expected community radio build flags")
        for file, key in (("felucca.bin", "firmware_sha256"), ("loader/ota.bin", "loader_sha256")):
            if hashlib.sha256((folder / file).read_bytes()).hexdigest() != manifest[key]:
                raise ValueError(f"{name}: {file} differs from manifest")
        variants[name] = (folder, manifest, package)
    return variants


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", required=True, help="vX.Y.Z[-prerelease]")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", a.version):
        ap.error("invalid version tag")
    if git("status", "--porcelain").strip():
        ap.error("release packaging requires a clean committed tree")
    record = snapshot(ROOT)
    variants = collect_variants(ROOT, fingerprint(record))
    a.output.mkdir(parents=True, exist_ok=False)
    version = a.version.removeprefix("v")
    prefix = f"blackbox-fm1-{version}"
    epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    manifest = {"release": a.version, "source_commit": git("rev-parse", "HEAD").decode().strip(),
                "source_sha256": fingerprint(record), "product": variants["usb-only"][1]["product"],
                "companion": "https://github.com/guysoft/blackbox-companion-app", "variants": {}}
    for name, (folder, entry, package) in variants.items():
        variant_prefix = f"{prefix}-v17-{name}"
        (a.output / f"{variant_prefix}.fwsc").write_bytes(package.raw)
        shutil.copyfile(folder / "felucca.bin", a.output / f"{variant_prefix}-app.bin")
        shutil.copyfile(folder / "loader/ota.bin", a.output / f"{variant_prefix}-loader.bin")
        entry.update(release=a.version, source_commit=manifest["source_commit"], variant=name,
                     exact_release_package_hardware_tested=False)
        (a.output / f"{variant_prefix}-manifest.json").write_text(json.dumps(entry, indent=2) + "\n")
        manifest["variants"][name] = entry
    (a.output / f"{prefix}-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    source_archive(a.output / f"{prefix}-source.tar.gz", ROOT, prefix, record, epoch)
    license_path = a.output / f"{prefix}-licenses.tar.gz"
    with license_path.open("xb") as output, gzip.GzipFile(fileobj=output, mode="wb", mtime=epoch, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            copy_git_archive(archive, ROOT, prefix, epoch,
                              ("LICENSE", "LICENSING.md", "LICENSES", "CREDITS.md",
                               "assets/samples-cc0/ATTRIBUTION.txt",
                               *[p for p in record["files"] if p.startswith("firmware/third_party/") and
                                 (Path(p).name.upper().startswith(("LICENSE", "NOTICE")) or "/LICENSES/" in p)]))
            add_bytes(archive, f"{prefix}/NOTICE-felucca-bsp.txt",
                      (ROOT / "firmware/bsp/NOTICE").read_bytes(), epoch)
    shutil.copyfile(ROOT / "docs/blackbox-controls.png", a.output / "blackbox-controls.png")
    (a.output / "RELEASE-NOTES.md").write_text(notes(a.version, manifest))
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                   for p in sorted(a.output.iterdir()) if p.is_file())
    (a.output / "SHA256SUMS").write_text(sums)
    print(a.output)


if __name__ == "__main__":
    main()

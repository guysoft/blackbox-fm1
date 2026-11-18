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
    return f"""# blackbox-fm1 {version} — experimental V17 bring-up

Independent Felucca fork for the M-VAVE ANN Blackbox. Not an upstream-supported target.

## Hardware evidence and limitations

- First V17-profile installation on one Blackbox booted successfully. The user
  confirmed the physical UI, PARA role selection and audible output.
- Runtime counters advanced with no observed missed audio deadlines or LCD timeouts.
- The exact CI-built assets below have **not** been flashed: the hardware pilot
  preceded the publication/CI changes. Do not confuse build tests with hardware tests.
- **Screen capture currently fails. Automatic repeat flashing is disarmed.**
- Project/settings/sample persistence is disabled; edits do not survive power-off.
- OTA staging overwrites stock sound-bank bytes at `[0xE0000,0xE5000)`.
- Back up the entire device before installation. A stock `.fwsc` is not a full backup.
- Full stock flash restore and a second software-only update remain untested.
- V20/V23 are build-tested only and are **not** covered by this V17 release.

## Files

- `*-v17.fwsc`: installable V17-profile package; identity `{manifest['product']}`.
  Never install it on an FM-1 or assume compatibility with another Blackbox revision.
- `*-app.bin`, `*-loader.bin`: raw components, **not** standalone installation files.
- `*-source.tar.gz`: complete corresponding source, including the pinned BSP and
  engine submodules and a source-fingerprint lock for rebuilding without Git.
- `*-licenses.tar.gz`: licence texts, notices and sample attribution.
- `*-manifest.json` and `SHA256SUMS`: provenance and integrity.
- `blackbox-controls.png`: button cheat sheet.

Source is GPL-3.0-only, with third-party licences retained. The Blackbox `.fwsc`
also retains donor boot/configuration material; upstream Felucca's “no vendor
material” claim does not apply to it. GPL does not relicense those retained bytes.
See LICENSING.md and CREDITS.md in the complete source.

Build on Linux x86-64: unpack the complete source, run `make setup`, then
`make build BOARD=blackbox-v17` and `make test`. Setup downloads pinned inputs;
it never installs system packages. This release does not include the stock donor
download or any per-device dump, preset export, identifiers or private IR files.

Source fingerprint: `{manifest['source_sha256']}`.
"""


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
    folder = ROOT / "build/blackbox-v17"
    manifest = json.loads((folder / "manifest.json").read_text())
    p = validate_artifacts(folder / "blackbox-fm1-950.fwsc", manifest, "blackbox-v17")
    if fingerprint(record) != manifest["source_sha256"]:
        ap.error("source changed since build")
    a.output.mkdir(parents=True, exist_ok=False)
    version = a.version.removeprefix("v")
    prefix = f"blackbox-fm1-{version}"
    epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    (a.output / f"{prefix}-v17.fwsc").write_bytes(p.raw)
    shutil.copyfile(folder / "felucca.bin", a.output / f"{prefix}-app.bin")
    shutil.copyfile(folder / "loader/ota.bin", a.output / f"{prefix}-loader.bin")
    for name, key in (("app", "firmware_sha256"), ("loader", "loader_sha256")):
        data = (a.output / f"{prefix}-{name}.bin").read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest[key]:
            raise ValueError(f"{name} binary does not match build manifest")
    manifest.update(release=a.version, source_commit=git("rev-parse", "HEAD").decode().strip(),
                    exact_release_package_hardware_tested=False)
    (a.output / f"{prefix}-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    source_archive(a.output / f"{prefix}-source.tar.gz", ROOT, prefix, record, epoch)
    license_path = a.output / f"{prefix}-licenses.tar.gz"
    with license_path.open("xb") as output, gzip.GzipFile(fileobj=output, mode="wb", mtime=epoch, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            copy_git_archive(archive, ROOT, prefix, epoch,
                             ("LICENSE", "LICENSING.md", "LICENSES", "CREDITS.md",
                              "assets/samples-cc0/ATTRIBUTION.txt"))
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

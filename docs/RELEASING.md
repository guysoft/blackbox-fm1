# Experimental releases

The public repository is `guysoft/blackbox-fm1`. Source stays GPL-3.0-only;
third-party licences and the distinction between our code and retained donor
material are described in LICENSING.md.

## Continuous integration

`.github/workflows/firmware.yml` runs on the `blackbox-fm1` branch, pull requests,
manual dispatch and `v*` tags. It uses SHA-pinned GitHub Actions and the existing
checksum-pinned compiler/SDK/donor downloads, with `uv sync --frozen`.
No system package installation or hardware flashing occurs.

The build job:

1. Checks out both pinned source submodules and an offline ROM-reader test peer.
2. Builds V17/V20/V23 and compares two V17 packages byte-for-byte.
3. Runs pytest and the V17 simulated update/monitor loop.
4. Creates release assets using `tools/release_blackbox.py`.

The tag-only publish job has `contents: write` permission and cannot run unless
the build job passes. It always creates a **pre-release**, never a stable release.
Branch/PR builds retain the same asset layout as Actions artifacts for review.

## Next candidate: v0.2.0-alpha.1

The companion now lives at https://github.com/guysoft/blackbox-companion-app.
Its source, screenshot, Android CI and development APKs are released separately.
Firmware CI does not fetch or bundle an APK and does not need Android tooling.

## Assets

- Two explicitly named V17 variants: `*-v17-usb-only.fwsc` (radio disabled) and
  `*-v17-ble-selfcal.fwsc` (community BLE with measured startup trims).
  Each has its own raw app/loader and provenance manifest. Diagnostic images
  and the older non-self-calibrating BLE variant are never release assets.
- Complete source `.tar.gz`, including BSP/engine submodules, licences and
  `.source-fingerprint.json`. The lock verifies extracted source files and
  reproduces the build fingerprint without requiring `.git`.
- Licence/attribution archive, control cheat sheet, release notes and SHA256SUMS.
- Summary manifest links the companion repo and lists both firmware variants.

Only tracked source files and explicitly selected output files are packaged.
Device dumps, serials, user presets/IRs, downloaded stock files, toolchain caches
and reference checkouts are excluded. Source archives use fixed commit timestamps
and deterministic gzip headers. GitHub's automatic source archives omit submodule
contents; use our `*-source.tar.gz` for complete corresponding source.

## Cutting a release

1. Review hardware evidence and known failures in PROGRESS.md. Do not mark
   untested features passed or equate a successful CI run with a hardware test.
2. Commit the complete source/docs and verify the tree is clean.
3. Push the branch; review its Actions result.
4. Tag that verified commit, e.g. `v0.1.0-alpha.1`, and push only that tag.
5. The tag workflow rebuilds/tests and publishes the pre-release assets.
6. Check the release manifest, complete-source contents and asset checksums.

The build identity remains `BlackBox_950`; the semantic release tag is recorded
separately in manifests. Both variants must match the clean source fingerprint.
CI rebuilds each V17 variant twice and compares bytes. Source/manifest/component
hash mismatches, unexpected BLE flags or diagnostic images refuse packaging.

Screen capture, software updates and Linux/Android BLE control have hardware
evidence on earlier builds. The HELLO idempotence fix is host-tested but not yet
installed. Do not label an exact release candidate hardware-tested until that
exact package has a separately authorized supervised trial. Cold boot, stock
restore, long-duration RF and formal audio latency remain unqualified.
Persistence stays disabled; OTA still overwrites `[0xE0000,0xE5000)`.

Tagging triggers public pre-release publication automatically: do not push a tag
until the user authorizes cutting the release. The old alpha's GitHub metadata
currently says non-prerelease despite its name; do not silently change it.

To assemble the same asset set locally after a build:

```sh
.venv/bin/python tools/release_blackbox.py --version v0.2.0-alpha.1 \
  --output artifacts/releases/v0.2.0-alpha.1
```

The assembler refuses a dirty tree, stale source fingerprint, wrong board,
changed component hashes or an existing output directory.
First build both inputs: `make build BOARD=blackbox-v17` and
`make build BOARD=blackbox-v17 BLE=1 BLE_SELFCAL=1`.

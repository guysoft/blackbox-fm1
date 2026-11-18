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

## Assets

- V17 `.fwsc`, raw app and loader binaries, provenance manifest.
- Complete source `.tar.gz`, including BSP/engine submodules, licences and
  `.source-fingerprint.json`. The lock verifies extracted source files and
  reproduces the build fingerprint without requiring `.git`.
- Licence/attribution archive, control cheat sheet, release notes and SHA256SUMS.

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

The build identity is currently `BlackBox_950`; the semantic release tag is
recorded separately in the release manifest. The initial hardware pilot used an
earlier source fingerprint; publication/CI changes make these exact release
bytes a new build. Release notes must state that the exact CI package has not
been flashed and that screen capture/repeat-flash qualification remain incomplete.

To assemble the same asset set locally after a build:

```sh
.venv/bin/python tools/release_blackbox.py --version v0.1.0-alpha.1 \
  --output artifacts/releases/v0.1.0-alpha.1
```

The assembler refuses a dirty tree, stale source fingerprint, wrong board,
changed component hashes or an existing output directory.

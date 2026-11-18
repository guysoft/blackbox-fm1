# SPDX-License-Identifier: GPL-3.0-only
import hashlib

import pytest

from bootstrap import obtain, verify


def test_verify_preserves_bad_file(tmp_path):
    p = tmp_path / "config"
    p.write_bytes(b"user data")
    with pytest.raises(ValueError, match="preserved"):
        verify(p, "0" * 64)
    assert p.read_bytes() == b"user data"


def test_offline_by_default(tmp_path):
    with pytest.raises(FileNotFoundError):
        obtain({"file": "a", "sha256": "0" * 64, "url": "https://invalid.example"}, tmp_path)


def test_existing_checked(tmp_path):
    p = tmp_path / "a"
    p.write_bytes(b"a")
    item = {"file": "a", "sha256": hashlib.sha256(b"a").hexdigest()}
    assert obtain(item, tmp_path) == p

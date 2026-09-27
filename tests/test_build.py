"""dev/build.py --check: exits non-zero when a committed template drifts."""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest
from conftest import KIROCREW_SRC
from conftest import ROOT as REPO

pytestmark = pytest.mark.skipif(KIROCREW_SRC is None, reason="KIROCREW_SRC is not set")


def _build(tree, *flags):
    return subprocess.run(
        [sys.executable, str(tree / "dev" / "build.py"), *flags, str(KIROCREW_SRC)],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_check_passes_after_build_and_fails_on_drift(tmp_path):
    # A copy of the tree, so the check does not depend on whether the committed
    # templates match today's KiroCrew main (the scheduled drift job covers that).
    tree = tmp_path / "repo"
    shutil.copytree(REPO / "dev", tree / "dev", ignore=shutil.ignore_patterns("out", "__pycache__"))
    shutil.copytree(REPO / "xiaoya" / "templates", tree / "xiaoya" / "templates")

    assert _build(tree).returncode == 0
    assert _build(tree, "--check").returncode == 0

    fallback = tree / "xiaoya" / "templates" / "fallback.html"
    fallback.write_text(fallback.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    result = _build(tree, "--check")
    assert result.returncode == 1
    assert "fallback.html" in result.stderr

    fallback.unlink()
    assert _build(tree, "--check").returncode == 1

"""Load xiaoya/hooks.py by file path, with stub kiro_crew modules when it is absent.

xiaoya/ is not a package, and CI has no Kiro Crew checkout. The hooks tests only
need ``override_templates_dir`` and ``atomic_write``; each test points the first
at tmp_path, so nothing here ever touches ~/.kiro/crew.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOKS_PATH = ROOT / "xiaoya" / "hooks.py"
TEMPLATE_PATH = ROOT / "xiaoya" / "templates" / "xiaoya.html"


def _kiro_crew_available() -> bool:
    try:
        return importlib.util.find_spec("kiro_crew") is not None
    except (ImportError, ValueError):
        return False


def _install_stubs() -> None:
    pkg = types.ModuleType("kiro_crew")
    pkg.__path__ = []  # mark as a package

    panel = types.ModuleType("kiro_crew.agent_panel")

    def override_templates_dir() -> Path:
        raise RuntimeError("stub: tests must monkeypatch override_templates_dir")

    panel.override_templates_dir = override_templates_dir

    aw = types.ModuleType("kiro_crew.atomic_write")

    def atomic_write(path, text, *args, **kwargs) -> None:
        Path(path).write_text(text, encoding="utf-8")

    aw.atomic_write = atomic_write

    pkg.agent_panel = panel
    pkg.atomic_write = aw
    sys.modules["kiro_crew"] = pkg
    sys.modules["kiro_crew.agent_panel"] = panel
    sys.modules["kiro_crew.atomic_write"] = aw


KIRO_CREW_REAL = _kiro_crew_available()
if not KIRO_CREW_REAL:
    _install_stubs()


def load_hooks():
    """A fresh module object for xiaoya/hooks.py."""
    spec = importlib.util.spec_from_file_location("xiaoya_hooks_under_test", HOOKS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hooks(tmp_path, monkeypatch):
    """hooks.py with its target directory redirected to tmp_path."""
    module = load_hooks()
    target_dir = tmp_path / "panel-templates"
    monkeypatch.setattr(module, "override_templates_dir", lambda: target_dir)
    return module

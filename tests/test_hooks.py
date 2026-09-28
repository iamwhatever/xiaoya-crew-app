"""install / on_startup / on_shutdown against a tmp template directory."""

from __future__ import annotations

import importlib.util
import logging
import shutil

import pytest
from conftest import FALLBACK_PATH, HOOKS_PATH, TEMPLATE_PATH


class FakeHealth:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def mark_degraded(self, issue: str) -> None:
        self.calls.append(issue)


class FakeCtx:
    def __init__(self) -> None:
        self.health = FakeHealth()


def _target(hooks):
    return hooks.override_templates_dir() / "xiaoya.html"


def test_install_writes_file_with_marker(hooks):
    assert hooks.install() == "installed"
    dst = _target(hooks)
    assert dst.read_text(encoding="utf-8").splitlines()[0] == hooks.MARKER


def test_second_install_is_unchanged(hooks):
    assert hooks.install() == "installed"
    assert hooks.install() == "unchanged"


def test_install_refreshes_a_stale_file_of_ours(hooks):
    dst = _target(hooks)
    dst.parent.mkdir(parents=True)
    dst.write_text(hooks.MARKER + "\nold body\n", encoding="utf-8")
    assert hooks.install() == "installed"
    assert "old body" not in dst.read_text(encoding="utf-8")


def test_operator_file_is_kept_untouched(hooks):
    dst = _target(hooks)
    dst.parent.mkdir(parents=True)
    dst.write_text("<p>operator</p>", encoding="utf-8")
    assert hooks.install() == "kept-operator-file"
    assert dst.read_text(encoding="utf-8") == "<p>operator</p>"


def test_on_startup_marks_degraded_only_for_operator_file(hooks):
    ctx = FakeCtx()
    hooks.on_startup(ctx)
    assert ctx.health.calls == []

    dst = _target(hooks)
    dst.write_text("<p>operator</p>", encoding="utf-8")
    ctx = FakeCtx()
    hooks.on_startup(ctx)
    assert len(ctx.health.calls) == 1
    assert dst.read_text(encoding="utf-8") == "<p>operator</p>"


def test_on_startup_tolerates_ctx_without_health(hooks):
    dst = _target(hooks)
    dst.parent.mkdir(parents=True)
    dst.write_text("<p>operator</p>", encoding="utf-8")
    hooks.on_startup(object())


def test_on_shutdown_swaps_in_fallback_and_startup_swaps_back(hooks):
    dst = _target(hooks)
    hooks.on_startup(FakeCtx())
    hooks.on_shutdown(FakeCtx())
    assert dst.read_text(encoding="utf-8") == FALLBACK_PATH.read_text(encoding="utf-8")
    hooks.on_startup(FakeCtx())
    assert dst.read_text(encoding="utf-8") == TEMPLATE_PATH.read_text(encoding="utf-8")


def test_on_shutdown_after_app_files_are_deleted_still_writes_fallback(tmp_path, monkeypatch):
    # Uninstall deletes the app directory, then the gateway runs on_shutdown of
    # the module it already loaded.
    app = tmp_path / "apps" / "xiaoya"
    shutil.copytree(HOOKS_PATH.parent, app, ignore=shutil.ignore_patterns("__pycache__"))
    spec = importlib.util.spec_from_file_location("xiaoya_hooks_copy", app / "hooks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target_dir = tmp_path / "panel-templates"
    monkeypatch.setattr(module, "override_templates_dir", lambda: target_dir)

    module.on_startup(FakeCtx())
    shutil.rmtree(app)
    module.on_shutdown(FakeCtx())
    assert (target_dir / "xiaoya.html").read_text(encoding="utf-8") == FALLBACK_PATH.read_text(
        encoding="utf-8"
    )


def test_install_refuses_a_body_without_marker(hooks):
    with pytest.raises(RuntimeError, match="marker"):
        hooks.install("<p>no marker</p>\n")
    assert not _target(hooks).exists()


def test_on_shutdown_keeps_operator_file(hooks):
    dst = _target(hooks)
    dst.parent.mkdir(parents=True)
    dst.write_text("<p>operator</p>", encoding="utf-8")
    hooks.on_shutdown(FakeCtx())
    assert dst.read_text(encoding="utf-8") == "<p>operator</p>"


def test_on_shutdown_with_no_file_writes_fallback(hooks):
    hooks.on_shutdown(FakeCtx())
    assert _target(hooks).read_text(encoding="utf-8").splitlines()[0] == hooks.MARKER


def test_result_lines_log_at_warning(hooks, caplog):
    # The gateway log keeps only WARNING and up; an INFO result line is invisible.
    caplog.set_level(logging.WARNING)
    hooks.on_startup(FakeCtx())
    hooks.on_shutdown(FakeCtx())
    lines = [(r.levelno, r.getMessage()) for r in caplog.records]
    assert (logging.WARNING, "[xiaoya] template installed") in lines
    assert (logging.WARNING, "[xiaoya] fallback installed") in lines

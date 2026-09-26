"""install / on_startup / on_shutdown against a tmp template directory."""

from __future__ import annotations


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


def test_on_shutdown_keeps_our_file(hooks):
    hooks.on_startup(FakeCtx())
    dst = _target(hooks)
    body = dst.read_text(encoding="utf-8")
    hooks.on_shutdown(FakeCtx())
    assert dst.read_text(encoding="utf-8") == body


def test_on_shutdown_keeps_operator_file(hooks):
    dst = _target(hooks)
    dst.parent.mkdir(parents=True)
    dst.write_text("<p>operator</p>", encoding="utf-8")
    hooks.on_shutdown(FakeCtx())
    assert dst.read_text(encoding="utf-8") == "<p>operator</p>"


def test_on_shutdown_with_no_file_is_a_no_op(hooks):
    hooks.on_shutdown(FakeCtx())
    assert not _target(hooks).exists()

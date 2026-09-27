"""The bundled template: ownership marker, and composition through real kiro_crew."""

from __future__ import annotations

import json
import re

import pytest

from conftest import KIRO_CREW_REAL, TEMPLATE_PATH, load_hooks

HOSTILE = "<img src=x onerror=alert(1)>"
DATA = {
    "xiaoya": {"state": "working", "mood": "busy", "line": HOSTILE},
    "other": ["a"],
}


def test_template_first_line_is_marker():
    hooks = load_hooks()
    first = TEMPLATE_PATH.read_text(encoding="utf-8").splitlines()[0]
    assert first == hooks.MARKER


def test_generic_walk_skips_the_xiaoya_key():
    # The drawer renders data client-side; the generic walk filters its keys here,
    # so data.xiaoya drives the character and never becomes a generic data row.
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "k !== 'title' && k !== 'subtitle' && k !== 'xiaoya'" in body


def test_line_is_set_as_text_not_markup():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "innerHTML" not in body


@pytest.fixture
def real_panel(tmp_path, monkeypatch):
    if not KIRO_CREW_REAL:  # conftest stubs kiro_crew, so importorskip would pass
        pytest.skip("kiro_crew is not installed")
    pytest.importorskip("kiro_crew.agent_panel")
    import kiro_crew.agent_panel as ap

    monkeypatch.setattr(ap, "data_home", lambda: tmp_path)
    assert ap.override_templates_dir() == tmp_path / "panel-templates"
    return ap


def test_compose_with_real_kiro_crew(real_panel):
    ap = real_panel
    hooks = load_hooks()
    assert hooks.install() == "installed"
    assert (ap.override_templates_dir() / "xiaoya.html").exists()

    ap.publish("demo-crew", template="xiaoya", crew="demo-crew", data=DATA)
    html = ap.render_record(ap.read("demo-crew"))
    assert html is not None

    # The hostile line never reaches the HTML parser as a tag.
    assert "<img src=x onerror" not in html
    assert not re.search(r"<img\b[^>]*onerror", html, re.IGNORECASE)

    # It lands, escaped, inside the inert JSON island, and parses back intact.
    island = re.search(
        r'<script type="application/json" id="[^"]+">(.*?)</script>', html, re.DOTALL
    )
    assert island is not None
    assert "\\u003cimg" in island.group(1)
    parsed = json.loads(island.group(1))
    assert parsed["xiaoya"]["line"] == HOSTILE
    assert parsed["other"] == ["a"]

    # One island, so data.xiaoya exists once in the document.
    assert html.count('type="application/json"') == 1


def test_template_survives_on_shutdown(real_panel):
    ap = real_panel
    hooks = load_hooks()
    hooks.on_startup(object())
    ap.publish("demo-crew", template="xiaoya", crew="demo-crew", data=DATA)
    before = ap.render_record(ap.read("demo-crew"))
    hooks.on_shutdown(object())
    assert ap.render_record(ap.read("demo-crew")) == before

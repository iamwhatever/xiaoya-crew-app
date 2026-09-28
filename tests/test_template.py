"""The bundled templates: ownership marker, composition through real kiro_crew,
and how the stage script treats data.xiaoya."""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

from conftest import FALLBACK_PATH, KIRO_CREW_REAL, STAGE_SCRIPT, TEMPLATE_PATH, load_hooks

HOSTILE = "<img src=x onerror=alert(1)>"
DATA = {
    "xiaoya": {"state": "working", "mood": "busy", "line": HOSTILE},
    "other": ["a"],
}


@pytest.mark.parametrize("path", [TEMPLATE_PATH, FALLBACK_PATH], ids=["xiaoya", "fallback"])
def test_template_first_line_is_marker(path):
    hooks = load_hooks()
    assert path.read_text(encoding="utf-8").splitlines()[0] == hooks.MARKER


def test_fallback_is_the_plain_default_view():
    body = FALLBACK_PATH.read_text(encoding="utf-8")
    assert "k !== 'xiaoya'" not in body
    assert "xy-stage" not in body


def test_generic_walk_skips_the_xiaoya_key():
    # The drawer renders data client-side; the generic walk filters its keys here,
    # so data.xiaoya drives the character and never becomes a generic data row.
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "k !== 'title' && k !== 'subtitle' && k !== 'xiaoya'" in body


def test_line_is_set_as_text_not_markup():
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "innerHTML" not in body
    src = STAGE_SCRIPT.read_text(encoding="utf-8")
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
        assert sink not in src, sink
    assert "textContent" in src


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


def test_published_panel_still_renders_after_shutdown(real_panel):
    ap = real_panel
    hooks = load_hooks()
    hooks.on_startup(object())
    ap.publish("demo-crew", template="xiaoya", crew="demo-crew", data=DATA)
    assert 'id="xy-stage"' in ap.render_record(ap.read("demo-crew"))
    hooks.on_shutdown(object())
    html = ap.render_record(ap.read("demo-crew"))
    assert 'id="xy-stage"' not in html
    assert "\\u003cimg" in html


# A tiny fake DOM: enough for stage.script.html to run under node.
_HARNESS = r"""
const fs = require('fs');
const [script, dataJson, view] = [fs.readFileSync(0, 'utf8'), process.argv[1], process.argv[2]];
const nodes = {};
function el(extra) {
  const n = {
    style: {}, attrs: {}, className: '', textContent: '', hidden: true, title: '', children: [],
    setAttribute(k, v) { this.attrs[k] = String(v); },
    addEventListener() {},
    appendChild(c) { this.children.push(c); this.textContent += c.textContent; return c; },
    classes: [],
    ...extra,
  };
  n.classList = { toggle() { return true; }, add(c) { n.classes.push(c); } };
  return n;
}
function node(id) {
  if (!nodes[id]) nodes[id] = el({ id });
  return nodes[id];
}
node('kirocrew-panel-data').textContent = dataJson;
const body = el({ id: 'body' });
global.document = {
  getElementById: node,
  body,
  // The dashboard prepends <meta name="kirocrew-view" content="docked"> to the
  // docked copy only.
  querySelector(sel) {
    return view === 'docked' && sel === 'meta[name="kirocrew-view"][content="docked"]' ? {} : null;
  },
  createElement() { return el({}); },
  createTextNode(t) { return { textContent: String(t) }; },
};
eval(script.replace(/^\s*<\/?script>\s*$/gm, ''));
const out = { body: { classes: body.classes } };
for (const [id, n] of Object.entries(nodes)) out[id] = {
  attrs: n.attrs, text: n.textContent, display: n.style.display, hidden: n.hidden, title: n.title };
console.log(JSON.stringify(out));
"""


def _run_stage(data, view="expanded"):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    proc = subprocess.run(
        [node, "-e", _HARNESS, json.dumps(data), view],
        input=STAGE_SCRIPT.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(proc.stdout)


def test_unknown_mood_and_state_fall_back_to_neutral_idle():
    out = _run_stage({"xiaoya": {"state": "dancing", "mood": "<img>", "line": "hi"}})
    stage = out["xy-stage"]["attrs"]
    assert stage["data-state"] == "idle"
    assert stage["data-mood"] == "neutral"
    assert out["xy-stage"]["hidden"] is False


def test_known_mood_and_state_are_kept():
    out = _run_stage({"xiaoya": {"state": "error", "mood": "worried", "line": "red"}})
    assert out["xy-stage"]["attrs"]["data-state"] == "error"
    assert out["xy-stage"]["attrs"]["data-mood"] == "worried"


def test_line_is_set_as_text_verbatim():
    line = "<b onclick=x>bold</b>"
    out = _run_stage({"xiaoya": {"line": line}})
    assert out["xy-line"]["text"] == line


def test_no_xiaoya_key_leaves_stage_hidden():
    out = _run_stage({"other": 1})
    assert out["xy-stage"]["hidden"] is True


def test_stage_ids_exist_in_template():
    # Every id the script looks up is present, so the fake DOM above matches the
    # real one.
    ids = set(re.findall(r"getElementById\('([\w-]+)'\)", STAGE_SCRIPT.read_text(encoding="utf-8")))
    body = TEMPLATE_PATH.read_text(encoding="utf-8")
    missing = {i for i in ids if f'id="{i}"' not in body} - {"kirocrew-panel-data"}
    assert not missing


def test_template_opts_into_the_docked_card():
    # Line 2, right under the ownership marker: Kiro Crew reads the opt-in
    # from the template's leading comments.
    assert TEMPLATE_PATH.read_text(encoding="utf-8").splitlines()[1] == "<!--kirocrew:docked height=150-->"


def test_fallback_does_not_opt_into_the_docked_card():
    assert "kirocrew:docked" not in FALLBACK_PATH.read_text(encoding="utf-8")


def test_real_kiro_crew_reads_the_docked_height(real_panel):
    if not hasattr(real_panel, "docked_height"):
        pytest.skip("this Kiro Crew has no docked card")
    assert real_panel.docked_height(TEMPLATE_PATH.read_text(encoding="utf-8")) == 150


def test_expanded_view_stays_full_and_hides_the_wait_line():
    out = _run_stage({"xiaoya": {"state": "idle"}, "waiting_on_you": ["merge #1"]})
    assert out["body"]["classes"] == []
    assert out.get("xy-wait", {"hidden": True})["hidden"] is True


def test_docked_view_goes_compact_and_shows_the_first_wait_as_text():
    out = _run_stage(
        {"xiaoya": {"state": "working"}, "waiting_on_you": [HOSTILE, "  ", "reply on Slack", 7]},
        view="docked",
    )
    assert out["body"]["classes"] == ["xy-docked"]
    wait = out["xy-wait"]
    assert wait["hidden"] is False
    assert wait["text"] == "等你：" + HOSTILE + "（另 1 项）"
    assert wait["title"] == HOSTILE + "\nreply on Slack"


def test_docked_view_without_waits_keeps_the_line_hidden():
    out = _run_stage({"xiaoya": {"state": "idle"}, "waiting_on_you": "not a list"}, view="docked")
    assert out["body"]["classes"] == ["xy-docked"]
    assert out.get("xy-wait", {"hidden": True})["hidden"] is True

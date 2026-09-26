"""Rebuild xiaoya/templates/xiaoya.html from KiroCrew's default template.

    python3 dev/build.py /path/to/KiroCrew/src

The template is KiroCrew's generic ``default.html`` with a character stage on
top, so it is rebuilt from a KiroCrew checkout rather than copied by hand. The
result is checked through the real ``agent_panel.compose()``.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "xiaoya" / "templates" / "xiaoya.html"
SRC = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(SRC))
from kiro_crew.agent_panel import DATA_MARKER, compose  # noqa: E402

MARKER = "<!-- installed-by-app: xiaoya -->"  # must match xiaoya/hooks.py

base = (SRC / "kiro_crew" / "agent_panel_templates" / "default.html").read_text(encoding="utf-8")
stage = (HERE / "stage.fragment.html").read_text(encoding="utf-8")
script = (HERE / "stage.script.html").read_text(encoding="utf-8")

ROOT = '<div class="kp" id="kp-root"></div>'
FILTER_OLD = "return k !== 'title' && k !== 'subtitle';"
FILTER_NEW = "return k !== 'title' && k !== 'subtitle' && k !== 'xiaoya';"
for needle in (ROOT, DATA_MARKER, FILTER_OLD):
    assert base.count(needle) == 1, f"default.html changed shape: {needle!r}"

head = (
    MARKER + "\n"
    "<!--\n  Xiaoya panel template.\n\n"
    "  KiroCrew's generic default template (Apache-2.0) with a character stage\n"
    "  on top. The crew publishes data.xiaoya = {state, mood, line}; every other\n"
    "  key renders exactly as the default template renders it.\n\n"
    "  state: idle | thinking | working | error\n"
    "  mood:  neutral | happy | curious | busy | sleepy | scared | worried | proud\n"
    "  line:  one short sentence, shown in the speech bubble (textContent only)\n-->\n"
)
out = base.replace(ROOT, stage + "\n" + ROOT, 1)
out = out.replace(DATA_MARKER, DATA_MARKER + "\n" + script, 1)
out = out.replace(FILTER_OLD, FILTER_NEW, 1)
out = head + out
assert out.count(DATA_MARKER) == 1
compose(out, json.dumps({"xiaoya": {"state": "idle", "mood": "neutral", "line": "ok"}}))
OUT.write_text(out, encoding="utf-8")
print("wrote", OUT, len(out), "bytes")

"""Rebuild the bundled templates from KiroCrew's default template.

    python3 dev/build.py /path/to/KiroCrew/src          # rewrite them
    python3 dev/build.py --check /path/to/KiroCrew/src  # exit 1 if they differ

``xiaoya/templates/xiaoya.html`` is KiroCrew's generic ``default.html`` with a
character stage on top. ``xiaoya/templates/fallback.html`` is ``default.html``
alone; the app swaps it in on shutdown so published panels keep rendering. Both are rebuilt from a KiroCrew checkout rather than copied by hand,
and both are checked through the real ``agent_panel.compose()``.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "xiaoya" / "templates"
OUT = TEMPLATES / "xiaoya.html"
FALLBACK_OUT = TEMPLATES / "fallback.html"

MARKER = "<!-- installed-by-app: xiaoya -->"  # must match xiaoya/hooks.py

ROOT = '<div class="kp" id="kp-root"></div>'
FILTER_OLD = "return k !== 'title' && k !== 'subtitle';"
FILTER_NEW = "return k !== 'title' && k !== 'subtitle' && k !== 'xiaoya';"

HEAD = (
    MARKER + "\n"
    "<!--\n  Xiaoya panel template.\n\n"
    "  KiroCrew's generic default template (Apache-2.0) with a character stage\n"
    "  on top. The crew publishes data.xiaoya = {state, mood, line}; every other\n"
    "  key renders exactly as the default template renders it.\n\n"
    "  state: idle | thinking | working | error\n"
    "  mood:  neutral | happy | curious | busy | sleepy | scared | worried | proud\n"
    "  line:  one short sentence, shown in the speech bubble (textContent only)\n-->\n"
)
FALLBACK_HEAD = (
    MARKER + "\n"
    "<!--\n  Xiaoya fallback, installed while the Xiaoya app is disabled.\n\n"
    "  KiroCrew's generic default template (Apache-2.0), unchanged, so panels\n"
    "  published with template \"xiaoya\" still render: data.xiaoya shows as a\n"
    "  plain group of fields. The next app start swaps the full template back.\n-->\n"
)


def build(src: Path) -> dict[Path, str]:
    """Return ``{output path: content}`` for every bundled template."""
    sys.path.insert(0, str(src))
    from kiro_crew.agent_panel import DATA_MARKER, compose

    base = (src / "kiro_crew" / "agent_panel_templates" / "default.html").read_text(encoding="utf-8")
    stage = (HERE / "stage.fragment.html").read_text(encoding="utf-8")
    script = (HERE / "stage.script.html").read_text(encoding="utf-8")

    for needle in (ROOT, DATA_MARKER, FILTER_OLD):
        assert base.count(needle) == 1, f"default.html changed shape: {needle!r}"

    out = base.replace(ROOT, stage + "\n" + ROOT, 1)
    out = out.replace(DATA_MARKER, DATA_MARKER + "\n" + script, 1)
    out = out.replace(FILTER_OLD, FILTER_NEW, 1)
    out = HEAD + out
    fallback = FALLBACK_HEAD + base

    sample = json.dumps({"xiaoya": {"state": "idle", "mood": "neutral", "line": "ok"}})
    for body in (out, fallback):
        assert body.count(DATA_MARKER) == 1
        compose(body, sample)
    return {OUT: out, FALLBACK_OUT: fallback}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path, help="KiroCrew's src/ directory")
    parser.add_argument("--check", action="store_true", help="compare only; exit 1 on drift")
    args = parser.parse_args(argv)

    stale = []
    for path, body in build(args.src.resolve()).items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if args.check:
            if current != body:
                stale.append(path)
        else:
            path.write_text(body, encoding="utf-8")
            print("wrote", path, len(body), "bytes")
    for path in stale:
        print(f"drift: {path} differs from a rebuild; run dev/build.py", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

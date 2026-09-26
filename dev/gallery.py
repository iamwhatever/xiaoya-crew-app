"""Render every mood through the real compose() and lay them out in one page.

The theme block stands in for the variables the dashboard's srcdoc injects, so
the preview shows both a dark and a light dashboard.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[1])
from kiro_crew.agent_panel import compose  # noqa: E402

tpl = (HERE.parent / "xiaoya" / "templates" / "xiaoya.html").read_text(encoding="utf-8")
THEMES = {
    "dark": ":root{--text:#e8e8ea;--text-strong:#fff;--muted:#9a9aa3;--bg:#18181c;"
            "--bg-elevated:#22222a;--border:#35353d;--accent:#8e48ff}body{background:#18181c}",
    "light": ":root{--text:#1f1f24;--text-strong:#000;--muted:#6b6b75;--bg:#ffffff;"
             "--bg-elevated:#f4f3f8;--border:#dcdbe3;--accent:#6b2bd9}body{background:#ffffff}",
}
CASES = [
    ("neutral", "idle", "早上好，今天先看 PR 巡检"),
    ("curious", "thinking", "这个 review 说的对吗？我查查代码"),
    ("busy", "working", "在跑 vitest，等我一下"),
    ("worried", "error", "Windows 分片红了"),
    ("happy", "idle", "测试都过了"),
    ("proud", "idle", "全绿啦，等你来合"),
    ("sleepy", "idle", "没有新情况"),
    ("scared", "error", "gateway 连不上了"),
]
out_dir = HERE / "out" / "gallery"
out_dir.mkdir(parents=True, exist_ok=True)
cells = []
for theme, css in THEMES.items():
    for mood, state, line in CASES:
        data = {"xiaoya": {"state": state, "mood": mood, "line": line}}
        html = "<meta charset=utf-8><style>" + css + "</style>" + compose(tpl, json.dumps(data, ensure_ascii=False))
        name = f"{theme}-{mood}.html"
        (out_dir / name).write_text(html, encoding="utf-8")
        cells.append(f'<figure><iframe src="gallery/{name}"></iframe>'
                     f"<figcaption>{theme} · {mood} · {state}</figcaption></figure>")
page = (
    "<!doctype html><meta charset=utf-8><style>"
    "body{margin:0;padding:16px;background:#0e0e11;font:12px sans-serif;color:#aaa}"
    ".g{display:grid;grid-template-columns:repeat(4,330px);gap:12px}"
    "figure{margin:0}iframe{width:330px;height:200px;border:1px solid #333;border-radius:8px}"
    "figcaption{padding:4px 2px}</style><div class=g>" + "".join(cells) + "</div>"
)
(HERE / "out" / "gallery.html").write_text(page, encoding="utf-8")
print(len(cells), "cells")

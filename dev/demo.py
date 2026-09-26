"""A scripted Crew-page demo: chat on the left, the member's drawer on the right.

The drawer's document is the REAL xiaoya.html composed by the REAL
agent_panel.compose(); only the page chrome around it is a mock of the Crew page.
One HTML page per step, so a headless browser can screenshot each and ffmpeg can
stitch them into a clip.
"""

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, sys.argv[1])
from kiro_crew.agent_panel import compose  # noqa: E402

TPL = (HERE.parent / "xiaoya" / "templates" / "xiaoya.html").read_text(encoding="utf-8")
THEME = (":root{--text:#e8e8ea;--text-strong:#fff;--muted:#9a9aa3;--bg:#18181c;"
         "--bg-elevated:#22222a;--border:#35353d;--accent:#8e48ff}body{background:#18181c}")

# (who, chat text, panel data). who: "user" | "bot" | "tool"
STEPS = [
    ("user", "帮我看看 PR #14267 的 CI", {
        "title": "PR #14267 巡检",
        "xiaoya": {"state": "thinking", "mood": "curious", "line": "好，我先看看 CI"},
    }),
    ("tool", "gh pr checks 14267  →  30/47 完成", {
        "title": "PR #14267 巡检",
        "xiaoya": {"state": "working", "mood": "busy", "line": "还在跑，等我一下"},
        "checks_green": "30/47", "waiting_on_you": "无",
    }),
    ("bot", "Windows 3 分片红了：platformdirs.pytest_plugin", {
        "title": "PR #14267 巡检",
        "xiaoya": {"state": "error", "mood": "worried", "line": "Windows 分片红了"},
        "checks_green": "44/47",
        "reds": [{"check": "Windows 3", "cause": "platformdirs"}],
    }),
    ("tool", "git worktree add origin/main  →  main 上也红", {
        "title": "PR #14267 巡检",
        "xiaoya": {"state": "thinking", "mood": "curious", "line": "main 上也红，不是我们的锅"},
        "checks_green": "44/47",
        "reds": [{"check": "Windows 3", "cause": "main 本来就红"}],
    }),
    ("tool", "gh run rerun 1843…  →  47/47", {
        "title": "PR #14267 巡检",
        "xiaoya": {"state": "idle", "mood": "happy", "line": "重跑过了"},
        "checks_green": "47/47",
    }),
    ("bot", "全部通过。要合并吗？", {
        "title": "PR #14267 巡检",
        "xiaoya": {"state": "idle", "mood": "proud", "line": "全绿啦，等你来合"},
        "waiting_on_you": ["合并 PR #14267"],
        "checks_green": "47/47",
    }),
]

PAGE_CSS = """
*{box-sizing:border-box}body{margin:0;height:100vh;display:flex;background:#111114;color:#e8e8ea;
font:13px -apple-system,'Segoe UI','PingFang SC','Noto Sans CJK SC',sans-serif}
.nav{width:56px;background:#0c0c0f;border-right:1px solid #26262c}
.roster{width:210px;border-right:1px solid #26262c;padding:14px 10px}
.roster h1{font-size:13px;color:#9a9aa3;margin:0 0 10px 6px;font-weight:600}
.m{display:flex;gap:8px;align-items:center;padding:8px;border-radius:8px;color:#bdbdc6}
.m.on{background:#22222a;color:#fff}.dot{width:26px;height:26px;border-radius:50%;background:#3a2d57;
display:flex;align-items:center;justify-content:center;font-size:12px}
.chat{flex:1;display:flex;flex-direction:column;min-width:0}
.hd{padding:12px 18px;border-bottom:1px solid #26262c;font-weight:600}
.log{flex:1;padding:16px 18px;display:flex;flex-direction:column;gap:10px;overflow:hidden}
.u{align-self:flex-end;background:#3b2a66;padding:8px 12px;border-radius:12px;max-width:70%}
.b{align-self:flex-start;background:#1d1d23;border:1px solid #2c2c33;padding:8px 12px;border-radius:12px;max-width:80%}
.t{align-self:flex-start;font:12px ui-monospace,monospace;color:#9a9aa3;padding:4px 10px;
border-left:2px solid #35353d}
.new{outline:2px solid #8e48ff55}
.box{margin:0 18px 16px;padding:10px 12px;border:1px solid #2c2c33;border-radius:10px;color:#6b6b75}
.drawer{width:430px;border-left:1px solid #26262c;display:flex;flex-direction:column;background:#141418}
.dh{padding:12px 14px;border-bottom:1px solid #26262c;display:flex;justify-content:space-between}
.dh b{font-size:13px}.dh span{color:#9a9aa3;font-size:12px}
.bar{margin:10px 14px 0;padding:6px 10px;border-radius:8px;background:#1b1b21;color:#9a9aa3;font-size:11px}
.bar b{color:#7ad19b;font-weight:600;margin-right:6px}
iframe{flex:1;margin:10px 14px 14px;border:1px solid #26262c;border-radius:10px;background:#18181c}
.step{position:fixed;left:66px;bottom:10px;font-size:11px;color:#6b6b75}
"""

out = HERE / "out" / "demo"
out.mkdir(parents=True, exist_ok=True)
for i in range(len(STEPS)):
    who, _, data = STEPS[i]
    panel = "<meta charset=utf-8><style>" + THEME + "</style>" + compose(TPL, json.dumps(data, ensure_ascii=False))
    (out / f"panel-{i}.html").write_text(panel, encoding="utf-8")
    bubbles = []
    for j, (w, text, _) in enumerate(STEPS[: i + 1]):
        cls = {"user": "u", "bot": "b", "tool": "t"}[w]
        prefix = "▸ " if w == "tool" else ""
        bubbles.append(f'<div class="{cls}{" new" if j == i else ""}">{prefix}{html.escape(text)}</div>')
    page = f"""<!doctype html><meta charset=utf-8><title>demo {i}</title><style>{PAGE_CSS}</style>
<div class=nav></div>
<div class=roster><h1>团队成员</h1>
<div class="m on"><div class=dot>雅</div>default</div>
<div class=m><div class=dot>C</div>kirocrew-conductor</div>
<div class=m><div class=dot>W</div>kirocrew-worker</div></div>
<div class=chat><div class=hd>default</div><div class=log>{''.join(bubbles)}</div>
<div class=box>给 default 发消息…</div></div>
<div class=drawer><div class=dh><b>{html.escape(data.get('title', ''))}</b><span>刚刚发布</span></div>
<div class=bar><b>已隔离</b>由此队友填写，与本页面隔离，且数据发送被阻止</div>
<iframe sandbox="allow-scripts" src="panel-{i}.html" title="由 default 填写的仪表板"></iframe></div>
<div class=step>模拟 · 第 {i + 1}/{len(STEPS)} 步 · 右侧是真实模板</div>
"""
    (out / f"step-{i}.html").write_text(page, encoding="utf-8")
print(len(STEPS), "steps")

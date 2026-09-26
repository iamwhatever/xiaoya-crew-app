"""Install the Xiaoya panel template when the app starts. Never remove it.

No core change: this uses the operator template directory the Crew webview
already reads (``agent_panel.override_templates_dir()``). Agents cannot write
there; this hook runs in the gateway process, which can.

Only a file carrying ``MARKER`` on its first line is treated as ours. An
operator's own ``xiaoya.html`` is never overwritten or deleted.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from kiro_crew.agent_panel import override_templates_dir
from kiro_crew.atomic_write import atomic_write

logger = logging.getLogger(__name__)

TEMPLATE_ID = "xiaoya"
MARKER = "<!-- installed-by-app: xiaoya -->"
_SOURCE = Path(__file__).resolve().parent / "templates" / f"{TEMPLATE_ID}.html"


def _target() -> Path:
    return override_templates_dir() / f"{TEMPLATE_ID}.html"


def _is_ours(path: Path) -> bool:
    try:
        with path.open(encoding="utf-8") as fh:
            return fh.readline().strip() == MARKER
    except OSError:
        return False


def install() -> str:
    """Write the template. Returns what happened, for logs and tests."""
    body = _SOURCE.read_text(encoding="utf-8")
    if not body.startswith(MARKER):
        raise RuntimeError("bundled template is missing its ownership marker")
    dst = _target()
    if dst.exists() and not _is_ours(dst):
        logger.warning("[xiaoya] %s exists and is not ours; leaving it alone", dst)
        return "kept-operator-file"
    if dst.exists() and dst.read_text(encoding="utf-8") == body:
        return "unchanged"
    dst.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(dst, body)
    return "installed"


def on_startup(ctx: Any) -> None:
    result = install()
    logger.info("[xiaoya] template %s", result)
    if result == "kept-operator-file":
        health = getattr(ctx, "health", None)
        if health is not None:
            health.mark_degraded("an operator-authored xiaoya.html already exists")


def on_shutdown(ctx: Any) -> None:
    """Leave the template in place.

    Kiro Crew composes a panel from its stored template id on every drawer read
    (``agent_panel.render_record``). An id with no file raises ``unknown_template``
    and the drawer gets a 503 ``panel_render_failed``. So deleting the file here
    broke every panel a crew had already published with it.

    This hook cannot tell a disable from a gateway stop or an uninstall: all three
    call it with the same ``AppContext``, and App Kit has no in-process uninstall
    hook (``setup.onUninstall`` is a sandboxed script; the sandbox seals that
    directory read-only).
    Keeping the file is right for all three: it is inert markup that only renders
    data a crew chose to publish with it, and the next ``install()`` refreshes it.
    """
    dst = _target()
    state = "kept" if dst.exists() and _is_ours(dst) else "not ours or absent"
    logger.info("[xiaoya] template %s at %s", state, dst)

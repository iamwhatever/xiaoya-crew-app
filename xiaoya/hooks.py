"""Install the Xiaoya panel template while the app is enabled, remove it after.

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


def remove() -> str:
    dst = _target()
    if not dst.exists():
        return "absent"
    if not _is_ours(dst):
        return "kept-operator-file"
    dst.unlink()
    return "removed"


def on_startup(ctx: Any) -> None:
    result = install()
    logger.info("[xiaoya] template %s", result)
    if result == "kept-operator-file":
        health = getattr(ctx, "health", None)
        if health is not None:
            health.mark_degraded("an operator-authored xiaoya.html already exists")


def on_shutdown(ctx: Any) -> None:
    # Runs on disable AND on gateway stop. Removing on stop is harmless: the next
    # start re-installs before any drawer can read it.
    logger.info("[xiaoya] template %s", remove())

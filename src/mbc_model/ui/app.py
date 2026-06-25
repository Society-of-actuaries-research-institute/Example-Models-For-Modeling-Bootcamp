"""pywebview launcher for the desktop UI."""

from __future__ import annotations

from pathlib import Path

from mbc_model.ui.bridge import DesktopBridge


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> None:
    """Open the HTML desktop UI in a native pywebview window."""
    try:
        import webview  # type: ignore[import-not-found, unused-ignore]
    except ImportError as exc:  # pragma: no cover - depends on optional GUI install
        raise SystemExit(
            "pywebview is required for the desktop UI. "
            "Install the project dependencies, then run python -m mbc_model.ui again."
        ) from exc

    html_path = Path(__file__).parent / "app.html"
    if not html_path.exists():
        raise SystemExit(f"Desktop UI file not found: {html_path}")

    bridge = DesktopBridge(project_root=_project_root())
    window = webview.create_window(
        "SOA Modeling Bootcamp production model example",
        html_path.resolve().as_uri(),
        js_api=bridge,
        width=1240,
        height=860,
        min_size=(980, 720),
    )
    bridge.attach_window(window)
    webview.start()

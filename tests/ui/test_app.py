"""Tests for the pywebview app launcher without opening a real window."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from mbc_model.ui import app


def test_project_root_points_to_repo() -> None:
    assert (app._project_root() / "pyproject.toml").exists()


def test_main_creates_window_with_bridge(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def create_window(title, url, js_api, **kwargs):
        calls["title"] = title
        calls["url"] = url
        calls["js_api"] = js_api
        calls["kwargs"] = kwargs
        return object()

    def start():
        calls["started"] = True

    fake_webview = SimpleNamespace(create_window=create_window, start=start)
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    app.main()

    assert calls["title"] == "SOA Modeling Bootcamp production model example"
    assert str(calls["url"]).endswith("app.html")
    assert calls["kwargs"] == {"width": 1240, "height": 860, "min_size": (980, 720)}
    assert calls["started"] is True

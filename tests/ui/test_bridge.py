"""Tests for the pywebview JavaScript bridge without launching a GUI."""

from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import openpyxl
import pytest
from webview.util import parse_file_type

from mbc_model.runner import run_with_results
from mbc_model.ui.bridge import DesktopBridge, EXCEL_OPEN_FILE_FILTER, EXCEL_SAVE_FILE_FILTER

_ROOT = Path(__file__).parent.parent.parent
_SMALL_SEED = _ROOT / "inputs" / "Input 10 pol 25 scen seed.xlsx"
_SMALL_TABLE = _ROOT / "inputs" / "Input 10 pol 25 scen table.xlsx"


def test_bridge_file_dialog_filters_are_valid_for_pywebview() -> None:
    assert parse_file_type(EXCEL_OPEN_FILE_FILTER) == (
        "Excel workbooks",
        "*.xlsx",
    )
    assert parse_file_type(EXCEL_SAVE_FILE_FILTER) == (
        "Excel workbook",
        "*.xlsx",
    )


def test_bridge_browse_input_file_requires_window(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    response = bridge.browse_input_file()

    assert not response["ok"]
    assert "not ready" in response["error"]


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_browse_input_file_handles_cancel_and_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selections: list[object] = [[], [str(_SMALL_SEED)]]

    class FakeWindow:
        def create_file_dialog(self, *_args: object, **_kwargs: object) -> object:
            return selections.pop(0)

    fake_webview = SimpleNamespace(OPEN_DIALOG="open")
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")
    bridge.attach_window(FakeWindow())

    cancelled = bridge.browse_input_file()
    selected = bridge.browse_input_file()

    assert cancelled == {"ok": False, "cancelled": True}
    assert selected["ok"]
    assert selected["preview"]["file_name"] == _SMALL_SEED.name


def test_bridge_get_input_preview_reports_missing_file(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    response = bridge.get_input_preview(str(tmp_path / "missing.xlsx"))

    assert not response["ok"]
    assert "not found" in response["error"]


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_get_input_preview_reports_parser_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")
    monkeypatch.setattr(
        "mbc_model.ui.bridge.build_input_preview",
        lambda _path: (_ for _ in ()).throw(ValueError("bad workbook")),
    )

    response = bridge.get_input_preview(str(_SMALL_SEED))

    assert not response["ok"]
    assert "bad workbook" in response["error"]


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_get_input_preview_returns_payload(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")
    bridge._state["output_path"] = "old-output.xlsx"
    bridge._state["output"] = {"stale": True}

    response = bridge.get_input_preview(str(_SMALL_SEED))

    assert response["ok"]
    assert response["preview"]["policy_count"] == 10
    assert response["status"]["input_path"] == str(_SMALL_SEED.resolve())
    assert response["status"]["output_path"] == ""
    assert response["status"]["output"] is None
    assert response["status"]["log"][0]["user"]


def test_bridge_start_run_rejects_missing_or_duplicate_run(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    missing = bridge.start_run(str(tmp_path / "missing.xlsx"))
    assert not missing["ok"]
    assert "not found" in missing["error"]

    input_path = tmp_path / "input.xlsx"
    input_path.write_text("placeholder", encoding="utf-8")
    bridge._state["running"] = True
    duplicate = bridge.start_run(str(input_path))
    assert not duplicate["ok"]
    assert "already in progress" in duplicate["error"]


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_start_run_updates_status_with_output(tmp_path: Path) -> None:
    output_path, results = run_with_results(_SMALL_SEED, output_dir=tmp_path, verbose=False)
    bridge = DesktopBridge(
        project_root=_ROOT,
        runner=lambda _path: (output_path, results),
        run_log_path=tmp_path / "run_log.csv",
    )

    response = bridge.start_run(str(_SMALL_SEED))
    assert response["ok"]

    deadline = time.time() + 5
    status = bridge.get_run_status()
    while status["running"] and time.time() < deadline:
        time.sleep(0.05)
        status = bridge.get_run_status()

    assert status["status"] == "Complete"
    assert status["output_path"] == str(output_path)
    assert status["output"]["dashboard"]["available"]
    assert status["output"]["dashboard"]["chart"]["available"]
    assert status["output"]["scenario"]["chart"]["available"]
    assert status["log"][0]["status"] == "Complete"


def test_bridge_open_output_file_uses_platform_opener(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "results.xlsx"
    output_path.write_text("placeholder", encoding="utf-8")
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    calls: list[str] = []
    if os.name == "nt":
        monkeypatch.setattr(os, "startfile", lambda path: calls.append(str(path)), raising=False)
    else:
        monkeypatch.setattr(
            "mbc_model.ui.bridge.subprocess.Popen",
            lambda args: calls.append(str(args[-1])),
        )

    response = bridge.open_output_file(str(output_path))

    assert response["ok"]
    assert calls == [str(output_path.resolve())]


def test_bridge_open_output_file_reports_unavailable_and_missing(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    unavailable = bridge.open_output_file()
    missing = bridge.open_output_file(str(tmp_path / "missing.xlsx"))

    assert not unavailable["ok"]
    assert "No output file" in unavailable["error"]
    assert not missing["ok"]
    assert "not found" in missing["error"]


def test_bridge_open_output_file_uses_stored_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "results.xlsx"
    output_path.write_text("placeholder", encoding="utf-8")
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")
    bridge._state["output_path"] = str(output_path)
    calls: list[str] = []
    monkeypatch.setattr("mbc_model.ui.bridge._open_path", lambda path: calls.append(str(path)))

    response = bridge.open_output_file()

    assert response["ok"]
    assert calls == [str(output_path.resolve())]


def test_bridge_open_output_file_reports_opener_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "results.xlsx"
    output_path.write_text("placeholder", encoding="utf-8")
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")
    monkeypatch.setattr(
        "mbc_model.ui.bridge._open_path",
        lambda _path: (_ for _ in ()).throw(OSError("blocked")),
    )

    response = bridge.open_output_file(str(output_path))

    assert not response["ok"]
    assert "blocked" in response["error"]


def test_bridge_open_docs_handles_missing_success_and_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bridge = DesktopBridge(project_root=tmp_path, run_log_path=tmp_path / "run_log.csv")
    missing = bridge.open_docs()
    assert not missing["ok"]
    assert "Documentation not found" in missing["error"]

    docs_path = tmp_path / "site" / "index.html"
    docs_path.parent.mkdir()
    docs_path.write_text("<html></html>", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr("mbc_model.ui.bridge._open_path", lambda path: calls.append(str(path)))
    success = bridge.open_docs()
    assert success["ok"]
    assert calls == [str(docs_path)]

    monkeypatch.setattr(
        "mbc_model.ui.bridge._open_path",
        lambda _path: (_ for _ in ()).throw(OSError("no browser")),
    )
    error = bridge.open_docs()
    assert not error["ok"]
    assert "no browser" in error["error"]


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_run_log_persists_to_csv(tmp_path: Path) -> None:
    log_path = tmp_path / "run_log.csv"
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=log_path)

    response = bridge.get_input_preview(str(_SMALL_SEED))

    assert response["ok"]
    with log_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[-1]["status"] == "Ready"
    assert rows[-1]["input_file"] == str(_SMALL_SEED.resolve())

    reloaded = DesktopBridge(project_root=_ROOT, run_log_path=log_path)
    status = reloaded.get_run_status()
    assert status["log"][0]["action"].startswith("Loaded workbook")
    assert status["log"][0]["date"]


@pytest.mark.skipif(not _SMALL_TABLE.exists(), reason=f"Fixture workbook not found: {_SMALL_TABLE}")
def test_bridge_save_input_changes_validates_then_saves_copy(tmp_path: Path) -> None:
    source_path = _make_xlsx_fixture(tmp_path)
    output_path = tmp_path / "edited.xlsx"
    bridge = DesktopBridge(
        project_root=_ROOT,
        run_log_path=tmp_path / "run_log.csv",
        save_dialog=lambda _suggested: output_path,
    )

    response = bridge.save_input_changes(
        str(source_path),
        {
            "inforce": [{"policy_id": 1, "field": "YOB", "value": "1952"}],
            "parameters": {},
            "reporting": [],
        },
    )

    assert response["ok"]
    assert response["preview"]["path"] == str(output_path.resolve())
    assert response["status"]["input_path"] == str(output_path.resolve())
    assert response["status"]["log"][0]["status"] == "Saved"


@pytest.mark.skipif(not _SMALL_TABLE.exists(), reason=f"Fixture workbook not found: {_SMALL_TABLE}")
def test_bridge_save_input_changes_handles_missing_cancel_and_save_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = _make_xlsx_fixture(tmp_path)
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")
    missing = bridge.save_input_changes(str(tmp_path / "missing.xlsx"), {})
    assert not missing["ok"]
    assert "not found" in missing["error"]

    cancelled_bridge = DesktopBridge(
        project_root=_ROOT,
        run_log_path=tmp_path / "run_log.csv",
        save_dialog=lambda _suggested: None,
    )
    cancelled = cancelled_bridge.save_input_changes(str(source_path), {})
    assert cancelled == {"ok": False, "cancelled": True}

    error_bridge = DesktopBridge(
        project_root=_ROOT,
        run_log_path=tmp_path / "run_log.csv",
        save_dialog=lambda _suggested: tmp_path / "edited.xlsx",
    )
    monkeypatch.setattr(
        "mbc_model.ui.bridge.save_input_copy",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("disk full")),
    )
    error = error_bridge.save_input_changes(str(source_path), {})
    assert not error["ok"]
    assert "disk full" in error["error"]


@pytest.mark.skipif(not _SMALL_TABLE.exists(), reason=f"Fixture workbook not found: {_SMALL_TABLE}")
def test_bridge_save_input_changes_does_not_open_save_dialog_for_invalid_edits(
    tmp_path: Path,
) -> None:
    source_path = _make_xlsx_fixture(tmp_path)
    called = False

    def save_dialog(_suggested: Path) -> Path:
        nonlocal called
        called = True
        return tmp_path / "edited.xlsx"

    bridge = DesktopBridge(
        project_root=_ROOT,
        run_log_path=tmp_path / "run_log.csv",
        save_dialog=save_dialog,
    )

    response = bridge.save_input_changes(
        str(source_path),
        {"inforce": [{"policy_id": 1, "field": "YOB", "value": "1700"}]},
    )

    assert not response["ok"]
    assert response["validation_errors"]
    assert not called


def test_bridge_run_model_records_runner_errors(tmp_path: Path) -> None:
    input_path = tmp_path / "input.xlsx"
    input_path.write_text("placeholder", encoding="utf-8")
    bridge = DesktopBridge(
        project_root=_ROOT,
        runner=lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
        run_log_path=tmp_path / "run_log.csv",
    )
    bridge._started_at = time.perf_counter()
    bridge._state["running"] = True

    bridge._run_model(input_path)
    status = bridge.get_run_status()

    assert status["status"] == "Error"
    assert status["running"] is False
    assert status["error"] == "boom"
    assert status["log"][0]["status"] == "Error"


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_run_model_accepts_runner_returning_only_path(tmp_path: Path) -> None:
    output_path = run_with_results(_SMALL_SEED, output_dir=tmp_path, verbose=False)[0]
    bridge = DesktopBridge(
        project_root=_ROOT,
        runner=lambda _path: output_path,
        run_log_path=tmp_path / "run_log.csv",
    )
    bridge._started_at = time.perf_counter()
    bridge._state["running"] = True

    bridge._run_model(_SMALL_SEED)
    status = bridge.get_run_status()

    assert status["status"] == "Complete"
    assert status["output_path"] == str(output_path)
    assert (
        status["output"]["dashboard"]["chart"]["message"] == "Run the model to display this graph."
    )


def test_bridge_choose_save_path_requires_window(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    with pytest.raises(Exception, match="not ready"):
        bridge._choose_save_path(tmp_path / "source.xlsx")


def test_bridge_open_path_supports_non_windows_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr("mbc_model.ui.bridge.os.name", "posix")
    monkeypatch.setattr(
        "mbc_model.ui.bridge.subprocess.Popen",
        lambda args: calls.append(list(args)),
    )
    monkeypatch.setattr("mbc_model.ui.bridge.sys_platform", lambda: "darwin")

    from mbc_model.ui.bridge import _open_path

    _open_path(tmp_path / "file.xlsx")
    monkeypatch.setattr("mbc_model.ui.bridge.sys_platform", lambda: "linux")
    _open_path(tmp_path / "file.xlsx")

    assert calls[0][0] == "open"
    assert calls[1][0] == "xdg-open"


def _make_xlsx_fixture(tmp_path: Path) -> Path:
    output_path = tmp_path / "input.xlsx"
    workbook = openpyxl.load_workbook(_SMALL_TABLE)
    workbook.save(output_path)
    return output_path

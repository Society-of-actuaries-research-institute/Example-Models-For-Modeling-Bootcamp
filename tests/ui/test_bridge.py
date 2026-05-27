"""Tests for the pywebview JavaScript bridge without launching a GUI."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

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


def _make_xlsx_fixture(tmp_path: Path) -> Path:
    output_path = tmp_path / "input.xlsx"
    workbook = openpyxl.load_workbook(_SMALL_TABLE)
    workbook.save(output_path)
    return output_path

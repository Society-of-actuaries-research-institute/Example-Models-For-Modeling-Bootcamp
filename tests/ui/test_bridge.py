"""Tests for the pywebview JavaScript bridge without launching a GUI."""

from __future__ import annotations

import csv
import os
import time
from pathlib import Path

import pytest

from mbc_model.runner import run_with_results
from mbc_model.ui.bridge import DesktopBridge

_ROOT = Path(__file__).parent.parent.parent
_SMALL_SEED = _ROOT / "inputs" / "Input 10 pol 25 scen seed.xlsm"


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_bridge_get_input_preview_returns_payload(tmp_path: Path) -> None:
    bridge = DesktopBridge(project_root=_ROOT, run_log_path=tmp_path / "run_log.csv")

    response = bridge.get_input_preview(str(_SMALL_SEED))

    assert response["ok"]
    assert response["preview"]["policy_count"] == 10
    assert response["status"]["input_path"] == str(_SMALL_SEED.resolve())
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

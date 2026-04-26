"""End-to-end integration test: run() against the real workbook fixture."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from mbc_model.runner import run

_FIXTURE = Path(__file__).parent.parent.parent / "inputs" / "Interface_Example_v4.xlsm"
_SKIP = not _FIXTURE.exists()
_SKIP_REASON = f"Fixture workbook not found: {_FIXTURE}"


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_run_produces_output_file(tmp_path: Path) -> None:
    out = run(_FIXTURE, output_dir=tmp_path)
    assert out.exists()
    assert out.suffix == ".xlsx"


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_run_output_has_run_summary(tmp_path: Path) -> None:
    out = run(_FIXTURE, output_dir=tmp_path)
    wb = openpyxl.load_workbook(out)
    assert "Run Summary" in wb.sheetnames


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_run_runtime_recorded(tmp_path: Path) -> None:
    out = run(_FIXTURE, output_dir=tmp_path)
    wb = openpyxl.load_workbook(out)
    ws = wb["Run Summary"]
    runtime_row = next(
        (row for row in ws.iter_rows(values_only=True) if row[0] == "Runtime (seconds)"),
        None,
    )
    assert runtime_row is not None
    assert isinstance(runtime_row[1], float)
    assert runtime_row[1] > 0

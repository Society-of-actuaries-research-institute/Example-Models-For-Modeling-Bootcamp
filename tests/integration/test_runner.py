"""End-to-end integration test: run() against the real workbook fixture."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pytest

from mbc_model.runner import run

_FIXTURE = Path(__file__).parent.parent.parent / "inputs" / "Input 10 pol 25 scen table.xlsx"
_SKIP = not _FIXTURE.exists()
_SKIP_REASON = f"Fixture workbook not found: {_FIXTURE}"


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_run_produces_output_file(tmp_path: Path) -> None:
    out = run(_FIXTURE, output_dir=tmp_path)
    assert out.exists()
    assert out.suffix == ".xlsx"


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_run_no_run_summary_sheet(tmp_path: Path) -> None:
    out = run(_FIXTURE, output_dir=tmp_path)
    wb = openpyxl.load_workbook(out)
    assert "Run Summary" not in wb.sheetnames

"""Tests for UI workbook preview payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from mbc_model.runner import run
from mbc_model.ui.preview import PREVIEW_LIMIT, build_input_preview, build_output_preview

_ROOT = Path(__file__).parent.parent.parent
_SMALL_SEED = _ROOT / "inputs" / "Input 10 pol 25 scen seed.xlsm"
_LARGE_SEED = _ROOT / "inputs" / "Input 50k pol 10k scen seed.xlsm"


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_input_preview_small_seed_workbook_counts_actual_records() -> None:
    preview = build_input_preview(_SMALL_SEED)

    assert preview["policy_count"] == 10
    assert preview["scenario_count"] == 25
    assert preview["random_numbers"] == "Seed"
    assert preview["inforce"]["shown_rows"] == 10
    assert not preview["inforce"]["has_more_rows"]


@pytest.mark.skipif(not _LARGE_SEED.exists(), reason=f"Fixture workbook not found: {_LARGE_SEED}")
def test_input_preview_large_seed_workbook_is_capped() -> None:
    preview = build_input_preview(_LARGE_SEED)

    assert preview["policy_count"] == 50000
    assert preview["scenario_count"] == 10000
    assert preview["inforce"]["shown_rows"] == PREVIEW_LIMIT
    assert preview["inforce"]["has_more_rows"]
    assert preview["parameters"]["random_numbers"]["rows"][0] == [
        "Which Random Numbers?",
        "Seed",
    ]


@pytest.mark.skipif(not _SMALL_SEED.exists(), reason=f"Fixture workbook not found: {_SMALL_SEED}")
def test_output_preview_reads_small_run_results(tmp_path: Path) -> None:
    output_path = run(_SMALL_SEED, output_dir=tmp_path, verbose=False)
    preview = build_output_preview(output_path)

    assert preview["file_name"].startswith("results_")
    assert preview["dashboard"]["available"]
    assert preview["total"]["available"]
    assert preview["scenario"]["available"]
    assert preview["policy"]["available"]
    assert preview["dashboard"]["rows"][0] == ["Discount rate", "4.00%"]
    assert preview["total"]["cash_flow"]["shown_rows"] <= PREVIEW_LIMIT

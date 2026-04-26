"""Unit tests for ExcelLoader using the real Interface_Example_v4.xlsm fixture.

These tests exercise the full parsing path against the workbook shipped in the
inputs/ directory.  They are fast (< 2 s) because they only read from the file
and perform no projection calculations.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from mbc_model.data.loader import ExcelLoader
from mbc_model.data.models import ModelParameters, MortalityTable, PolicyRecord, ReportingConfig

_FIXTURE = Path(__file__).parent.parent.parent / "inputs" / "Interface_Example_v4.xlsm"
_SKIP = not _FIXTURE.exists()
_SKIP_REASON = f"Fixture workbook not found: {_FIXTURE}"


# ---------------------------------------------------------------------------
# load_inforce
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_inforce_returns_10_policies() -> None:
    loader = ExcelLoader(_FIXTURE)
    policies = loader.load_inforce()
    assert len(policies) == 10


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_inforce_policy_ids_sequential() -> None:
    loader = ExcelLoader(_FIXTURE)
    ids = [p.policy_id for p in loader.load_inforce()]
    assert ids == list(range(1, 11))


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_inforce_genders_valid() -> None:
    loader = ExcelLoader(_FIXTURE)
    genders = {p.gender for p in loader.load_inforce()}
    assert genders <= {"M", "F"}


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_inforce_benefits_positive() -> None:
    loader = ExcelLoader(_FIXTURE)
    for p in loader.load_inforce():
        assert p.annual_benefit > 0


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_inforce_yob_reasonable() -> None:
    loader = ExcelLoader(_FIXTURE)
    for p in loader.load_inforce():
        assert 1800 < p.yob < 2025


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_inforce_first_policy_matches_rnd() -> None:
    """First policy must match the RnD model's hardcoded values."""
    loader = ExcelLoader(_FIXTURE)
    p = loader.load_inforce()[0]
    assert p.policy_id == 1
    assert p.yob == 1951
    assert p.gender == "M"
    assert p.annual_benefit == pytest.approx(20000.0)


# ---------------------------------------------------------------------------
# load_parameters — scalars
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_valuation_date() -> None:
    loader = ExcelLoader(_FIXTURE)
    params, _, _ = loader.load_parameters()
    assert params.valuation_date == date(2024, 12, 31)


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_last_projection_year() -> None:
    loader = ExcelLoader(_FIXTURE)
    params, _, _ = loader.load_parameters()
    assert params.last_projection_year == 2085


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_random_seed_is_int() -> None:
    loader = ExcelLoader(_FIXTURE)
    params, _, _ = loader.load_parameters()
    assert isinstance(params.random_seed, int)


# ---------------------------------------------------------------------------
# load_parameters — mortality table
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_mortality_table_length() -> None:
    """Mortality and improvement arrays must have 122 entries (ages 0-121)."""
    loader = ExcelLoader(_FIXTURE)
    _, table, _ = loader.load_parameters()
    assert len(table.male_qx) == 122
    assert len(table.female_qx) == 122
    assert len(table.male_improvement) == 122
    assert len(table.female_improvement) == 122


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_terminal_qx_is_one() -> None:
    loader = ExcelLoader(_FIXTURE)
    _, table, _ = loader.load_parameters()
    assert table.male_qx[-1] == pytest.approx(1.0)
    assert table.female_qx[-1] == pytest.approx(1.0)


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_qx_in_unit_interval() -> None:
    loader = ExcelLoader(_FIXTURE)
    _, table, _ = loader.load_parameters()
    assert np.all(table.male_qx >= 0) and np.all(table.male_qx <= 1)
    assert np.all(table.female_qx >= 0) and np.all(table.female_qx <= 1)


# ---------------------------------------------------------------------------
# load_parameters — random table
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_random_table_shape() -> None:
    loader = ExcelLoader(_FIXTURE)
    _, _, random_table = loader.load_parameters()
    assert random_table is not None
    assert random_table.shape == (25, 10)


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_random_table_values_in_unit_interval() -> None:
    loader = ExcelLoader(_FIXTURE)
    _, _, random_table = loader.load_parameters()
    assert random_table is not None
    assert np.all(random_table >= 0) and np.all(random_table <= 1)


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_parameters_random_table_first_entry_matches_rnd() -> None:
    """First entry [0, 0] must match the RnD model's hardcoded random number."""
    loader = ExcelLoader(_FIXTURE)
    _, _, random_table = loader.load_parameters()
    assert random_table is not None
    assert random_table[0, 0] == pytest.approx(0.208694776842403, rel=1e-6)


# ---------------------------------------------------------------------------
# load_reporting
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_reporting_discount_rate() -> None:
    loader = ExcelLoader(_FIXTURE)
    cfg = loader.load_reporting()
    assert cfg.discount_rate == pytest.approx(0.04)


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_reporting_returns_reporting_config() -> None:
    loader = ExcelLoader(_FIXTURE)
    cfg = loader.load_reporting()
    assert isinstance(cfg, ReportingConfig)


@pytest.mark.skipif(_SKIP, reason=_SKIP_REASON)
def test_load_reporting_boolean_fields_are_bool() -> None:
    loader = ExcelLoader(_FIXTURE)
    cfg = loader.load_reporting()
    for field in (
        cfg.create_policy_results,
        cfg.create_scenario_results,
        cfg.create_scenario_graph,
        cfg.create_total_results,
        cfg.create_dashboard_results,
        cfg.create_dashboard_graph,
    ):
        assert isinstance(field, bool)

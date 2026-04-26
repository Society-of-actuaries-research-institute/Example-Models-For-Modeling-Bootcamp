"""Unit tests for MortalityEngine.compute_cum_survival."""

from __future__ import annotations

import numpy as np
import pytest

from mbc_model.data.models import MortalityTable, PolicyRecord
from mbc_model.engine.mortality import MortalityEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _constant_table(n_ages: int, qx_value: float, improvement_value: float) -> MortalityTable:
    """All ages share the same qx and improvement scale."""
    qx = np.full(n_ages, qx_value, dtype=np.float64)
    qx[-1] = 1.0  # terminal age
    imp = np.full(n_ages, improvement_value, dtype=np.float64)
    return MortalityTable(male_qx=qx, female_qx=qx, male_improvement=imp, female_improvement=imp)


def _policy(policy_id: int, yob: int, gender: str) -> PolicyRecord:
    return PolicyRecord(policy_id=policy_id, yob=yob, gender=gender, annual_benefit=1000.0)  # type: ignore[arg-type]


ENGINE = MortalityEngine()


# ---------------------------------------------------------------------------
# Shape and dtype
# ---------------------------------------------------------------------------


def test_output_shape_and_dtype() -> None:
    table = _constant_table(130, 0.01, 0.0)
    policies = [_policy(1, 1960, "M"), _policy(2, 1955, "F")]
    years = np.arange(2025, 2035, dtype=np.int64)
    result = ENGINE.compute_cum_survival(policies, table, years, 2024)
    assert result.shape == (2, 10)
    assert result.dtype == np.float64


# ---------------------------------------------------------------------------
# Zero improvement: tPx = (1-qx)^t
# ---------------------------------------------------------------------------


def test_zero_improvement_single_male() -> None:
    qx = 0.02
    table = _constant_table(130, qx, 0.0)
    policy = [_policy(1, 1960, "M")]
    years = np.arange(2025, 2030, dtype=np.int64)
    result = ENGINE.compute_cum_survival(policy, table, years, 2024)

    px = 1.0 - qx
    expected = px ** np.arange(1, 6)  # t = 1..5
    np.testing.assert_allclose(result[0], expected, rtol=1e-12)


def test_zero_improvement_single_female() -> None:
    qx = 0.03
    table = _constant_table(130, qx, 0.0)
    policy = [_policy(1, 1950, "F")]
    years = np.arange(2025, 2030, dtype=np.int64)
    result = ENGINE.compute_cum_survival(policy, table, years, 2024)

    px = 1.0 - qx
    expected = px ** np.arange(1, 6)
    np.testing.assert_allclose(result[0], expected, rtol=1e-12)


# ---------------------------------------------------------------------------
# Improvement: matches manual calculation
# ---------------------------------------------------------------------------


def test_improvement_applied_correctly() -> None:
    """Verify improved_qx = base_qx * (1 - scale) ** (year - BASE_YEAR)."""
    qx = 0.05
    scale = 0.01
    table = _constant_table(130, qx, scale)

    policy = [_policy(1, 1960, "M")]
    years = np.array([2025, 2026], dtype=np.int64)
    result = ENGINE.compute_cum_survival(policy, table, years, 2024)

    base_yr = MortalityTable.BASE_YEAR  # 2012
    # Year 2025: exponent = 2025 - 2012 = 13
    iqx_2025 = qx * (1 - scale) ** (2025 - base_yr)
    # Year 2026: exponent = 2026 - 2012 = 14
    iqx_2026 = qx * (1 - scale) ** (2026 - base_yr)

    px_2025 = 1.0 - iqx_2025
    px_2026 = 1.0 - iqx_2026
    expected = np.array([px_2025, px_2025 * px_2026])
    np.testing.assert_allclose(result[0], expected, rtol=1e-12)


# ---------------------------------------------------------------------------
# Terminal age / beyond-table behaviour
# ---------------------------------------------------------------------------


def test_terminal_age_is_certain_death() -> None:
    """A policy at the terminal age (n_ages - 1) gets px = 0, cum_survival = 0."""
    n_ages = 10
    table = _constant_table(n_ages, 0.01, 0.0)
    # YOB chosen so attained age in 2025 is exactly n_ages - 1 = 9
    yob = 2025 - (n_ages - 1)
    policy = [_policy(1, yob, "M")]
    years = np.array([2025, 2026], dtype=np.int64)
    result = ENGINE.compute_cum_survival(policy, table, years, 2024)
    # Year 2025: age = 9 → qx[9] = 1.0, px = 0, cum = 0
    assert result[0, 0] == pytest.approx(0.0)
    # Year 2026: age = 10 (clamped to 9) → also 0; cumprod keeps 0
    assert result[0, 1] == pytest.approx(0.0)


def test_beyond_terminal_age_zeroed() -> None:
    """Ages strictly beyond the table are forced to px = 0."""
    n_ages = 5
    table = _constant_table(n_ages, 0.01, 0.0)
    # First year attained age = n_ages (beyond table)
    yob = 2025 - n_ages
    policy = [_policy(1, yob, "M")]
    years = np.array([2025], dtype=np.int64)
    result = ENGINE.compute_cum_survival(policy, table, years, 2024)
    assert result[0, 0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Mixed gender batch
# ---------------------------------------------------------------------------


def test_mixed_gender_independence() -> None:
    """Male and female policies compute independently; neither contaminates the other."""
    male_qx = np.full(130, 0.04, dtype=np.float64)
    male_qx[-1] = 1.0
    female_qx = np.full(130, 0.02, dtype=np.float64)
    female_qx[-1] = 1.0
    imp = np.zeros(130, dtype=np.float64)
    table = MortalityTable(
        male_qx=male_qx,
        female_qx=female_qx,
        male_improvement=imp,
        female_improvement=imp,
    )

    policies = [_policy(1, 1960, "M"), _policy(2, 1960, "F")]
    years = np.arange(2025, 2028, dtype=np.int64)
    result = ENGINE.compute_cum_survival(policies, table, years, 2024)

    # Male row
    np.testing.assert_allclose(result[0], (0.96) ** np.arange(1, 4), rtol=1e-12)
    # Female row
    np.testing.assert_allclose(result[1], (0.98) ** np.arange(1, 4), rtol=1e-12)


# ---------------------------------------------------------------------------
# All-female / all-male batch (no mask.any() short-circuit regression)
# ---------------------------------------------------------------------------


def test_all_female_batch() -> None:
    table = _constant_table(130, 0.015, 0.0)
    policies = [_policy(i, 1960, "F") for i in range(1, 4)]
    years = np.arange(2025, 2028, dtype=np.int64)
    result = ENGINE.compute_cum_survival(policies, table, years, 2024)
    assert result.shape == (3, 3)
    expected = (0.985) ** np.arange(1, 4)
    for row in range(3):
        np.testing.assert_allclose(result[row], expected, rtol=1e-12)


def test_all_male_batch() -> None:
    table = _constant_table(130, 0.015, 0.0)
    policies = [_policy(i, 1960, "M") for i in range(1, 4)]
    years = np.arange(2025, 2028, dtype=np.int64)
    result = ENGINE.compute_cum_survival(policies, table, years, 2024)
    assert result.shape == (3, 3)
    expected = (0.985) ** np.arange(1, 4)
    for row in range(3):
        np.testing.assert_allclose(result[row], expected, rtol=1e-12)


# ---------------------------------------------------------------------------
# Single policy, single year
# ---------------------------------------------------------------------------


def test_single_policy_single_year() -> None:
    table = _constant_table(130, 0.10, 0.0)
    result = ENGINE.compute_cum_survival(
        [_policy(1, 1960, "M")], table, np.array([2025], dtype=np.int64), 2024
    )
    assert result.shape == (1, 1)
    np.testing.assert_allclose(result[0, 0], 0.90, rtol=1e-12)

"""Unit tests for ProjectionEngine."""

from __future__ import annotations

import tracemalloc

import numpy as np
import pytest

from mbc_model.data.models import MortalityTable, PolicyRecord
from mbc_model.engine.mortality import MortalityEngine
from mbc_model.engine.projection import ProjectionEngine

ENGINE = ProjectionEngine()
MORT = MortalityEngine()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _policy(policy_id: int, yob: int, gender: str, benefit: float = 1.0) -> PolicyRecord:
    return PolicyRecord(policy_id=policy_id, yob=yob, gender=gender, annual_benefit=benefit)  # type: ignore[arg-type]


def _flat_table(n_ages: int, qx: float) -> MortalityTable:
    qx_arr = np.full(n_ages, qx, dtype=np.float64)
    qx_arr[-1] = 1.0
    imp = np.zeros(n_ages, dtype=np.float64)
    return MortalityTable(
        male_mortality_rates=qx_arr, female_mortality_rates=qx_arr, male_projection_scale=imp, female_projection_scale=imp
    )


# ---------------------------------------------------------------------------
# project_from_table — basic shapes and types
# ---------------------------------------------------------------------------


def test_project_from_table_shape() -> None:
    policies = [_policy(1, 1960, "M"), _policy(2, 1955, "F")]
    cum_survival = np.ones((2, 5), dtype=np.float64) * 0.9
    random_table = np.zeros((3, 2), dtype=np.float64)  # always survive
    result = ENGINE.project_from_table(policies, cum_survival, random_table)
    assert result.shape == (3, 5)
    assert result.dtype == np.float64


def test_project_from_table_all_survive() -> None:
    """When random = 1.0 and cum_survival = 0.8, everyone survives every year.

    cum_death = 0.2 for all years; 1.0 > 0.2 is always True.
    """
    benefit = 5000.0
    policies = [_policy(1, 1960, "M", benefit), _policy(2, 1955, "F", benefit)]
    cum_survival = np.full((2, 4), 0.8, dtype=np.float64)
    random_table = np.ones((2, 2), dtype=np.float64)  # 1.0 > 0.2 → always alive
    result = ENGINE.project_from_table(policies, cum_survival, random_table)
    # 2 policies × 5000 benefit each → 10000 per year
    np.testing.assert_allclose(result, np.full((2, 4), 10000.0))


def test_project_from_table_all_dead() -> None:
    """When cum_survival = 0 every policy is dead by year 1."""
    benefit = 1.0
    policies = [_policy(1, 1960, "M", benefit)]
    cum_survival = np.zeros((1, 3), dtype=np.float64)
    random_table = np.array([[0.5]], dtype=np.float64)  # 0.5 > 1.0 is False
    result = ENGINE.project_from_table(policies, cum_survival, random_table)
    np.testing.assert_allclose(result, 0.0)


def test_project_from_table_threshold_boundary() -> None:
    """survive iff random > cum_death  (strict >).

    cum_death = 1 - cum_survival.  When random == cum_death the policy
    is dead (not >) so the cash flow is 0.
    """
    benefit = 1000.0
    policies = [_policy(1, 1960, "M", benefit)]
    cum_survival = np.array([[0.3]], dtype=np.float64)  # cum_death = 0.7
    random_equal = np.array([[0.7]], dtype=np.float64)  # equal → dead
    result_dead = ENGINE.project_from_table(policies, cum_survival, random_equal)
    assert result_dead[0, 0] == pytest.approx(0.0)

    random_above = np.array([[0.70001]], dtype=np.float64)  # just above → alive
    result_alive = ENGINE.project_from_table(policies, cum_survival, random_above)
    assert result_alive[0, 0] == pytest.approx(benefit)


# ---------------------------------------------------------------------------
# project_seeded — reproducibility and determinism
# ---------------------------------------------------------------------------


def test_project_seeded_shape() -> None:
    policies = [_policy(1, 1960, "M")]
    cum_survival = np.full((1, 5), 0.5, dtype=np.float64)
    result = ENGINE.project_seeded(policies, cum_survival, number_of_scenarios=10, seed=42)
    assert result.shape == (10, 5)
    assert result.dtype == np.float64


def test_project_seeded_reproducible() -> None:
    """Same seed → identical output."""
    policies = [_policy(i, 1950 + i, "M", float(1000 * i)) for i in range(1, 6)]
    cum_survival = np.random.default_rng(0).random((5, 20))
    r1 = ENGINE.project_seeded(policies, cum_survival, number_of_scenarios=15, seed=7)
    r2 = ENGINE.project_seeded(policies, cum_survival, number_of_scenarios=15, seed=7)
    np.testing.assert_array_equal(r1, r2)


def test_project_seeded_different_seeds_differ() -> None:
    policies = [_policy(1, 1960, "M")]
    cum_survival = np.full((1, 5), 0.5, dtype=np.float64)
    r1 = ENGINE.project_seeded(policies, cum_survival, number_of_scenarios=20, seed=1)
    r2 = ENGINE.project_seeded(policies, cum_survival, number_of_scenarios=20, seed=2)
    assert not np.array_equal(r1, r2), "Different seeds should produce different results"


# ---------------------------------------------------------------------------
# compute_pv
# ---------------------------------------------------------------------------


def test_compute_pv_single_year_single_scenario() -> None:
    """PV of 1 cash flow at t=1 with rate r = CF / (1+r)."""
    rate = 0.04
    cf = np.array([[1000.0]], dtype=np.float64)
    years = np.array([2025], dtype=np.int64)
    pv = ENGINE.compute_pv(cf, years, valuation_year=2024, discount_rate=rate)
    expected = 1000.0 / 1.04
    np.testing.assert_allclose(pv[0], expected, rtol=1e-10)


def test_compute_pv_zero_discount() -> None:
    """With rate=0, PV = sum of cash flows."""
    cf = np.array([[100.0, 200.0, 300.0]], dtype=np.float64)
    years = np.arange(2025, 2028, dtype=np.int64)
    pv = ENGINE.compute_pv(cf, years, valuation_year=2024, discount_rate=0.0)
    np.testing.assert_allclose(pv[0], 600.0, rtol=1e-10)


def test_compute_pv_shape() -> None:
    cf = np.random.default_rng(0).random((25, 61))
    years = np.arange(2025, 2086, dtype=np.int64)
    pv = ENGINE.compute_pv(cf, years, valuation_year=2024, discount_rate=0.04)
    assert pv.shape == (25,)


def test_compute_pv_matches_manual() -> None:
    """Match hand-computed PV for 3 years."""
    rate = 0.05
    cfs = [1000.0, 2000.0, 3000.0]
    expected = sum(cf / (1 + rate) ** t for t, cf in enumerate(cfs, start=1))
    cf_mat = np.array([cfs], dtype=np.float64)
    years = np.array([2025, 2026, 2027], dtype=np.int64)
    pv = ENGINE.compute_pv(cf_mat, years, valuation_year=2024, discount_rate=rate)
    np.testing.assert_allclose(pv[0], expected, rtol=1e-10)


# ---------------------------------------------------------------------------
# build_policy_detail
# ---------------------------------------------------------------------------


def _rnd_table_for_policy_detail() -> MortalityTable:
    """Simple 10-age table: qx = 0.1, improvement = 0."""
    return _flat_table(10, 0.1)


def test_build_policy_detail_shape() -> None:
    table = _rnd_table_for_policy_detail()
    policy = _policy(1, 1975, "M", 1000.0)
    years = np.arange(2025, 2030, dtype=np.int64)
    detail = ENGINE.build_policy_detail(policy, 1, table, years, random_number=0.0)
    for arr in (
        detail.projection_years,
        detail.attained_ages,
        detail.base_qx,
        detail.improvement_factor,
        detail.improved_qx,
        detail.px,
        detail.cumulative_probability_of_survival_tPx,
        detail.cumulative_probability_of_death_1_minus_tPx,
        detail.survive_1_dead_0,
        detail.total_cash_flow,
    ):
        assert arr.shape == (5,), f"Expected shape (5,), got {arr.shape}"


def test_build_policy_detail_survive_all_zeros() -> None:
    """random = 0 → policy is dead from year 1 (0 > cum_death is False for cum_death >= 0)."""
    table = _rnd_table_for_policy_detail()
    policy = _policy(1, 1975, "M", 500.0)
    years = np.arange(2025, 2028, dtype=np.int64)
    detail = ENGINE.build_policy_detail(policy, 1, table, years, random_number=0.0)
    np.testing.assert_allclose(detail.survive_1_dead_0, 0.0)
    np.testing.assert_allclose(detail.total_cash_flow, 0.0)


def test_build_policy_detail_survive_flag_consistent_with_cum_survival() -> None:
    """survive_flag[y] == 1 iff random > 1 - cum_survival[y]."""
    table = _flat_table(130, 0.05)
    policy = _policy(1, 1960, "M", 1000.0)
    years = np.arange(2025, 2040, dtype=np.int64)
    rng_val = 0.5
    detail = ENGINE.build_policy_detail(policy, 2, table, years, random_number=rng_val)
    expected_flags = (rng_val > detail.cumulative_probability_of_death_1_minus_tPx).astype(np.float64)
    np.testing.assert_array_equal(detail.survive_1_dead_0, expected_flags)


def test_build_policy_detail_ids_stored() -> None:
    table = _flat_table(130, 0.01)
    policy = _policy(7, 1955, "F", 2000.0)
    years = np.arange(2025, 2028, dtype=np.int64)
    detail = ENGINE.build_policy_detail(policy, 3, table, years, random_number=0.9)
    assert detail.policy_id == 7
    assert detail.scenario_id == 3


def test_build_policy_detail_beyond_table_forces_death() -> None:
    """Age >= table length → base_qx = 1.0, improvement = 1.0 → px = 0."""
    n_ages = 5
    table = _flat_table(n_ages, 0.01)
    # First projection year attained age = n_ages (beyond table)
    yob = 2025 - n_ages
    policy = _policy(1, yob, "M", 1.0)
    years = np.array([2025], dtype=np.int64)
    detail = ENGINE.build_policy_detail(policy, 1, table, years, random_number=0.99)
    assert detail.base_qx[0] == pytest.approx(1.0)
    assert detail.improvement_factor[0] == pytest.approx(1.0)
    assert detail.px[0] == pytest.approx(0.0)
    assert detail.cumulative_probability_of_survival_tPx[0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Memory regression: peak < 500 MB for 100k policies × 250 years
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_project_from_table_peak_memory() -> None:
    """Peak memory during projection must stay below 1 GB.

    This guards against accidental materialisation of a full float64
    (n_scenarios × n_policies × n_years) intermediate array.
    At 1000 × 100_000 × 250 that would be ~200 GB.
    """
    n_policies = 100_000
    n_years = 250
    n_scenarios = 1_000

    rng = np.random.default_rng(0)
    policies = [_policy(i, 1950, "M") for i in range(n_policies)]
    cum_survival = rng.random((n_policies, n_years)).astype(np.float64)
    random_table = rng.random((n_scenarios, n_policies)).astype(np.float64)

    tracemalloc.start()
    ENGINE.project_from_table(policies, cum_survival, random_table)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024**2)
    assert peak_mb < 1000, f"Peak memory {peak_mb:.1f} MB exceeded 1 GB limit"

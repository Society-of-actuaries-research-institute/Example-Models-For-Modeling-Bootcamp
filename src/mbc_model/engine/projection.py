"""Stochastic projection and present-value computation.

Two projection paths are available:

* ``project_from_table`` — uses a pre-computed random-number matrix from the
  workbook (Random Numbers sheet).  Gives exact numerical parity with the RnD
  model when the same random numbers are used.

* ``project_seeded`` — generates per-policy random numbers on the fly with
  ``np.random.default_rng(seed + policy_index)``.  Policy index is 0-based so
  policy 1 uses ``seed + 0``, policy 2 uses ``seed + 1``, etc.  Reproducible
  regardless of batch size or policy order.

Both paths produce identical ``scenario_cash_flows`` arrays given the same
underlying random numbers.
"""

from __future__ import annotations

import numpy as np

from mbc_model.data.models import MortalityTable, PolicyDetail, PolicyRecord


class ProjectionEngine:
    """Converts a cumulative-survival matrix into scenario cash-flow arrays."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def project_from_table(
        self,
        policies: list[PolicyRecord],
        cum_survival: np.ndarray,
        random_table: np.ndarray,
    ) -> np.ndarray:
        """Run stochastic projection using a pre-loaded random-number matrix.

        Args:
            policies: Ordered inforce list.
            cum_survival: float64, shape (n_policies, n_years).
            random_table: float64, shape (n_scenarios, n_policies).  Entry
                [s, p] is the single random number drawn for scenario *s* and
                policy *p*.  Must match the column order of ``policies``.

        Returns:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
        """
        return self._project(policies, cum_survival, random_table)

    def project_seeded(
        self,
        policies: list[PolicyRecord],
        cum_survival: np.ndarray,
        n_scenarios: int,
        seed: int,
    ) -> np.ndarray:
        """Run stochastic projection, generating random numbers from a seed.

        Each policy gets its own RNG stream: ``default_rng(seed + p_idx)``
        where ``p_idx`` is 0-based.  This guarantees per-policy reproducibility
        even if the inforce list is re-ordered.

        Args:
            policies: Ordered inforce list.
            cum_survival: float64, shape (n_policies, n_years).
            n_scenarios: Number of Monte-Carlo scenarios to generate.
            seed: Base seed from ModelParameters.random_seed.

        Returns:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
        """
        n_policies = len(policies)
        random_matrix = np.empty((n_scenarios, n_policies), dtype=np.float64)
        for p_idx in range(n_policies):
            rng = np.random.default_rng(seed + p_idx)
            random_matrix[:, p_idx] = rng.random(n_scenarios)
        return self._project(policies, cum_survival, random_matrix)

    def compute_pv(
        self,
        scenario_cash_flows: np.ndarray,
        projection_years: np.ndarray,
        valuation_year: int,
        discount_rate: float,
    ) -> np.ndarray:
        """Discount scenario cash flows to present value at the valuation date.

        Uses end-of-year discounting: the first projection year has t=1.

        Args:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
            projection_years: int array, shape (n_years,).
            valuation_year: Calendar year of the valuation date (e.g. 2024).
            discount_rate: Annual discount rate, e.g. 0.04 for 4 %.

        Returns:
            pv_by_scenario: float64, shape (n_scenarios,).
        """
        t = (projection_years - valuation_year).astype(np.float64)
        discount_factors = 1.0 / (1.0 + discount_rate) ** t
        return scenario_cash_flows @ discount_factors

    def build_policy_detail(  # pylint: disable=too-many-positional-arguments,too-many-locals
        self,
        policy: PolicyRecord,
        scenario_id: int,
        table: MortalityTable,
        projection_years: np.ndarray,
        random_number: float,
    ) -> PolicyDetail:
        """Build per-year detail for exactly one (policy, scenario) pair.

        Replicates the row-by-row logic of the RnD model so that every column
        in the Policy Results sheet is populated correctly.

        Args:
            policy: The single policy to project.
            scenario_id: 1-based scenario identifier (stored in PolicyDetail).
            table: Mortality rates and improvement scales.
            projection_years: Calendar years to project, shape (n_years,).
            random_number: The single random variate for this (policy, scenario)
                pair, drawn from ``random_table[scenario_id-1, policy_idx]`` or
                from the seeded RNG.

        Returns:
            PolicyDetail with all arrays populated, shape (n_years,) each.
        """
        if policy.gender == "M":
            base_qx_arr = table.male_qx
            improvement_arr = table.male_improvement
        else:
            base_qx_arr = table.female_qx
            improvement_arr = table.female_improvement

        n_ages = len(base_qx_arr)
        ages = (projection_years - policy.yob).astype(np.int64)
        age_idx = np.clip(ages, 0, n_ages - 1)
        beyond = ages >= n_ages

        exponent = (projection_years - MortalityTable.BASE_YEAR).astype(np.float64)
        improve_factor = (1.0 - improvement_arr[age_idx]) ** exponent

        base_qx = base_qx_arr[age_idx].copy()
        # Beyond terminal age: certain death (mirrors RnD model's if-branch)
        base_qx[beyond] = 1.0
        improve_factor[beyond] = 1.0

        improved_qx = base_qx * improve_factor
        px = 1.0 - improved_qx
        cum_survival = np.cumprod(px)
        cum_death = 1.0 - cum_survival
        survive_flag = (random_number > cum_death).astype(np.float64)
        annual_cf = policy.annual_benefit * survive_flag

        return PolicyDetail(
            policy_id=policy.policy_id,
            scenario_id=scenario_id,
            projection_years=projection_years,
            ages=ages,
            base_qx=base_qx,
            improvement=improve_factor,
            improved_qx=improved_qx,
            px=px,
            cum_survival=cum_survival,
            cum_death=cum_death,
            survive_flag=survive_flag,
            annual_cf=annual_cf,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _project(
        self,
        policies: list[PolicyRecord],
        cum_survival: np.ndarray,
        random_matrix: np.ndarray,
    ) -> np.ndarray:
        """Core vectorised projection shared by both public entry points.

        Args:
            policies: Ordered inforce list.
            cum_survival: float64, shape (n_policies, n_years).
            random_matrix: float64, shape (n_scenarios, n_policies).

        Returns:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
        """
        benefits = np.array([p.annual_benefit for p in policies], dtype=np.float64)
        cum_death = 1.0 - cum_survival  # (n_policies, n_years)

        # survive_flag[s, p, y] = 1 iff random[s,p] > cum_death[p,y]
        # Broadcast: random_matrix[:, :, None] vs cum_death[None, :, :]
        survive_flag = (
            random_matrix[:, :, np.newaxis] > cum_death[np.newaxis, :, :]
        ).astype(
            np.float64
        )  # (n_scenarios, n_policies, n_years)

        # Aggregate benefits: avoid (n_s × n_p × n_y) float64 intermediate copy
        # by using einsum which fuses multiply + sum into one pass.
        return np.einsum("spT,p->sT", survive_flag, benefits)

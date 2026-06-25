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
from typing import cast

from mbc_model.data.models import MortalityTable, PolicyDetail, PolicyRecord


class ProjectionEngine:
    """Converts a cumulative survival matrix into scenario cash-flow arrays.

    Core idea: each policy is assigned one random number per scenario. If that
    random number is greater than the cumulative probability of death at year t,
    the policy is alive in year t and pays its annual benefit. Summing across all
    policies gives the total cash flow for that scenario and year.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def project_from_table(
        self,
        policies: list[PolicyRecord],
        cumulative_survival_matrix: np.ndarray,
        random_number_table: np.ndarray,
        verbose: bool = False,
    ) -> np.ndarray:
        """Run stochastic projection using a pre-loaded random-number matrix.

        Use this path when "Which Random Numbers?" = "Table" in the workbook.
        Results are identical to the RnD model when the same random numbers
        are supplied.

        Args:
            policies: Ordered list of inforce policies.
            cumulative_survival_matrix: float64, shape (n_policies, n_years).
                Entry [p, t] = probability policy p is alive at end of year t (tPx).
            random_number_table: float64, shape (n_scenarios, n_policies).
                Entry [s, p] = single random number for scenario s and policy p.
                Column order must match the order of ``policies``.
            verbose: If True, print a progress percentage to the terminal.

        Returns:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
                Entry [s, t] = total cash flow across all policies in scenario s, year t.
        """
        return self._project(
            policies, cumulative_survival_matrix, random_number_table, verbose=verbose
        )

    def project_seeded(
        self,
        policies: list[PolicyRecord],
        cumulative_survival_matrix: np.ndarray,
        number_of_scenarios: int,
        seed: int,
        verbose: bool = False,
    ) -> np.ndarray:
        """Run stochastic projection, generating random numbers from a seed.

        Use this path when "Which Random Numbers?" = "Seed" in the workbook.
        Each policy gets its own independent random number stream:
            np.random.default_rng(seed + policy_index)
        where policy_index is 0-based (policy 1 uses seed+0, etc.).
        Results are reproducible even if the inforce list is re-ordered.

        Args:
            policies: Ordered list of inforce policies.
            cumulative_survival_matrix: float64, shape (n_policies, n_years).
            number_of_scenarios: Number of Monte-Carlo scenarios to generate.
            seed: Base random seed from ModelParameters.random_seed.
            verbose: If True, print a progress percentage to the terminal.

        Returns:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
        """
        number_of_policies: int = len(policies)

        # Build the random number matrix by drawing from per-policy RNG streams.
        # Each policy gets seed + policy_index so results are stable when policies
        # are added or removed from the inforce list.
        random_number_matrix: np.ndarray = np.empty(
            (number_of_scenarios, number_of_policies), dtype=np.float64
        )
        for policy_index in range(number_of_policies):
            # np.random.default_rng creates a reproducible random number generator
            # seeded uniquely for this policy
            random_number_generator = np.random.default_rng(seed + policy_index)
            # Draw one random number per scenario for this policy
            random_number_matrix[:, policy_index] = random_number_generator.random(
                number_of_scenarios
            )

        return self._project(
            policies, cumulative_survival_matrix, random_number_matrix, verbose=verbose
        )

    def compute_pv(
        self,
        scenario_cash_flows: np.ndarray,
        projection_years: np.ndarray,
        valuation_year: int,
        discount_rate: float,
    ) -> np.ndarray:
        """Discount scenario cash flows to present value at the valuation date.

        Uses end-of-year discounting: a cash flow in the first projection year
        (t = 1) is discounted by 1 / (1 + rate)^1.

        Args:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
            projection_years: int array, shape (n_years,).
            valuation_year: Calendar year of the valuation date (e.g. 2024).
            discount_rate: Annual discount rate, e.g. 0.04 for 4%.

        Returns:
            present_value_by_scenario: float64, shape (n_scenarios,).
        """
        # t = number of years from the valuation date to each projection year
        time_periods_from_valuation: np.ndarray = (projection_years - valuation_year).astype(
            np.float64
        )

        # Discount factor for each year: 1 / (1 + rate)^t
        discount_factors_by_year: np.ndarray = (
            1.0 / (1.0 + discount_rate) ** time_periods_from_valuation
        )

        # @ is matrix multiplication: (n_scenarios, n_years) @ (n_years,) → (n_scenarios,).
        # Each scenario's PV = dot product of its annual cash flows with the discount factors.
        return cast(np.ndarray, scenario_cash_flows @ discount_factors_by_year)

    def build_policy_detail(
        self,
        policy: PolicyRecord,
        scenario_id: int,
        mortality_table: MortalityTable,
        projection_years: np.ndarray,
        random_number: float,
    ) -> PolicyDetail:
        """Build per-year detail for exactly one (policy, scenario) pair.

        Replicates the row-by-row logic of RnD_Model_example.calculate_policy()
        so that every column in the Policy Results sheet matches the RnD model.

        Args:
            policy: The single policy to project.
            scenario_id: 1-based scenario identifier (stored in the returned PolicyDetail).
            mortality_table: Mortality rates and projection scales indexed by attained age.
            projection_years: Calendar years to project, shape (n_years,).
            random_number: The single random variate for this (policy, scenario) pair,
                drawn from random_number_table[scenario_id-1, policy_idx] or from
                the seeded RNG.

        Returns:
            PolicyDetail with all arrays populated, one entry per projection year.
        """
        # Select the correct mortality table columns based on the policy's gender,
        # matching the RnD model's base_qx_table / improvement_table selection
        if policy.gender == "M":
            base_mortality_rates_table: np.ndarray = mortality_table.male_mortality_rates
            projection_scale_table: np.ndarray = mortality_table.male_projection_scale
        else:
            base_mortality_rates_table = mortality_table.female_mortality_rates
            projection_scale_table = mortality_table.female_projection_scale

        number_of_ages_in_table: int = len(base_mortality_rates_table)

        # Compute attained age in each projection year: age = year - year_of_birth
        attained_ages: np.ndarray = (projection_years - policy.yob).astype(np.int64)

        # Clamp age indices to [0, n_ages - 1] to avoid index-out-of-bounds errors
        age_index_clamped: np.ndarray = np.clip(attained_ages, 0, number_of_ages_in_table - 1)

        # Flag years where the insured's actual age is beyond the mortality table
        beyond_terminal_age: np.ndarray = attained_ages >= number_of_ages_in_table

        # Compute improvement factor: (1 - scale) ** (year - BASE_YEAR)
        # Matches the RnD formula: improvement = (1 - improvement_table[age]) ** (year - 2012)
        years_since_base_year: np.ndarray = (projection_years - MortalityTable.BASE_YEAR).astype(
            np.float64
        )
        improvement_factor: np.ndarray = (
            1.0 - projection_scale_table[age_index_clamped]
        ) ** years_since_base_year

        # Copy base mortality rates so we can overwrite the terminal-age values
        base_qx: np.ndarray = base_mortality_rates_table[age_index_clamped].copy()

        # Beyond the terminal age: certain death in every year (matches the RnD if-branch)
        base_qx[beyond_terminal_age] = 1.0
        improvement_factor[beyond_terminal_age] = 1.0

        # Final mortality rate after applying the improvement scale
        improved_qx: np.ndarray = base_qx * improvement_factor

        # Probability of surviving one year
        px: np.ndarray = 1.0 - improved_qx

        # Cumulative survival probability: tPx[t] = px[0] * px[1] * ... * px[t]
        # np.cumprod computes the running product along the array.
        cumulative_probability_of_survival_tPx: np.ndarray = np.cumprod(px)

        # Cumulative probability of death by each year: 1 - tPx
        cumulative_probability_of_death_1_minus_tPx: np.ndarray = (
            1.0 - cumulative_probability_of_survival_tPx
        )

        # Survival test: the policy is alive (1) if the random number drawn for this
        # (policy, scenario) pair is greater than the cumulative death probability.
        # Matches RnD: survive_1_dead_0 = int(random_number > cum_death_probability)
        survive_1_dead_0: np.ndarray = (
            random_number > cumulative_probability_of_death_1_minus_tPx
        ).astype(np.float64)

        # Annual cash flow: benefit paid if alive (1), zero if dead (0)
        total_cash_flow: np.ndarray = policy.annual_benefit * survive_1_dead_0

        return PolicyDetail(
            policy_id=policy.policy_id,
            scenario_id=scenario_id,
            random_number=random_number,
            projection_years=projection_years,
            attained_ages=attained_ages,
            base_qx=base_qx,
            improvement_factor=improvement_factor,
            improved_qx=improved_qx,
            px=px,
            cumulative_probability_of_survival_tPx=cumulative_probability_of_survival_tPx,
            cumulative_probability_of_death_1_minus_tPx=cumulative_probability_of_death_1_minus_tPx,
            survive_1_dead_0=survive_1_dead_0,
            total_cash_flow=total_cash_flow,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _project(
        self,
        policies: list[PolicyRecord],
        cumulative_survival_matrix: np.ndarray,
        random_number_matrix: np.ndarray,
        verbose: bool = False,
    ) -> np.ndarray:
        """Core vectorised projection shared by project_from_table and project_seeded.

        Processes policies in small batches to keep peak memory under ~225 MB even
        for 100,000 policies x 1,000 scenarios. See inline comments for details.

        Args:
            policies: Ordered list of inforce policies.
            cumulative_survival_matrix: float64, shape (n_policies, n_years).
            random_number_matrix: float64, shape (n_scenarios, n_policies).
            verbose: If True, print batch-level progress to the terminal.

        Returns:
            scenario_cash_flows: float64, shape (n_scenarios, n_years).
        """
        number_of_policies: int = len(policies)
        number_of_scenarios: int = random_number_matrix.shape[0]
        number_of_projection_years: int = cumulative_survival_matrix.shape[1]

        # Annual benefit for each policy, in the same order as the policies list
        annual_benefits: np.ndarray = np.array(
            [p.annual_benefit for p in policies], dtype=np.float64
        )

        # Process policies in small batches to control peak memory usage.
        #
        # Two key memory-saving decisions:
        #
        # 1. .copy() on the random number slice: random_number_matrix[:, start:end]
        #    is a highly-strided (non-contiguous) view because rows are n_policies wide.
        #    Without .copy(), NumPy materialises a large temporary array during the
        #    broadcast comparison below, roughly doubling peak memory. Copying first
        #    makes the slice contiguous and avoids this hidden allocation.
        #
        # 2. Cumulative death probabilities computed per batch rather than in advance:
        #    Pre-computing the full (n_policies, n_years) death matrix uses ~200 MB
        #    for 100k policies x 250 years. Per-batch computation avoids this cost.
        #
        # At batch_size=100, n_scenarios=1,000, n_years=250: peak ~225 MB.
        _POLICY_BATCH_SIZE: int = 100

        # Accumulator: total cash flow per scenario per year, summed across all batches
        scenario_cash_flows_output: np.ndarray = np.zeros(
            (number_of_scenarios, number_of_projection_years), dtype=np.float64
        )

        number_of_batches: int = (number_of_policies + _POLICY_BATCH_SIZE - 1) // _POLICY_BATCH_SIZE
        last_printed_percentage: int = -1

        for batch_index, policy_batch_start in enumerate(
            range(0, number_of_policies, _POLICY_BATCH_SIZE)
        ):
            if verbose:
                progress_percentage: int = int(100 * (batch_index + 1) / number_of_batches)
                if progress_percentage != last_printed_percentage:
                    # \r moves the cursor to the start of the current line so the
                    # percentage updates in place rather than printing a new line each time.
                    # end="" suppresses the automatic newline; flush=True forces display.
                    print(f"\r  Progress: {progress_percentage:3d}%", end="", flush=True)
                    last_printed_percentage = progress_percentage

            policy_batch_end: int = min(policy_batch_start + _POLICY_BATCH_SIZE, number_of_policies)

            # Copy this batch's random numbers to a contiguous array (see note 1 above)
            random_numbers_for_batch: np.ndarray = random_number_matrix[
                :, policy_batch_start:policy_batch_end
            ].copy()  # shape (n_scenarios, batch_size)

            # Cumulative death probability for each policy in this batch (see note 2)
            cumulative_death_for_batch: np.ndarray = (
                1.0 - cumulative_survival_matrix[policy_batch_start:policy_batch_end, :]
            )  # shape (batch_size, n_years)

            # Survival test broadcast across all scenarios, years, and policies at once.
            # random_numbers_for_batch[:, np.newaxis, :] -> shape (n_scenarios, 1, batch_size)
            # cumulative_death_for_batch.T[np.newaxis, :, :] -> shape (1, n_years, batch_size)
            # Broadcasting compares all combinations -> shape (n_scenarios, n_years, batch_size).
            # True (1.0) = policy is alive that year; False (0.0) = policy is dead.
            policy_survival_flags: np.ndarray = (
                random_numbers_for_batch[:, np.newaxis, :]
                > cumulative_death_for_batch.T[np.newaxis, :, :]
            ).astype(
                np.float64
            )  # shape (n_scenarios, n_years, batch_size)

            # Multiply survival flags by annual benefits and sum across all policies
            # in this batch. @ is matrix multiplication:
            # (n_scenarios, n_years, batch_size) @ (batch_size,) -> (n_scenarios, n_years)
            scenario_cash_flows_output += (
                policy_survival_flags @ annual_benefits[policy_batch_start:policy_batch_end]
            )

        if verbose:
            # Print a newline after the in-place progress line so subsequent
            # output appears on a fresh line
            print()

        return scenario_cash_flows_output

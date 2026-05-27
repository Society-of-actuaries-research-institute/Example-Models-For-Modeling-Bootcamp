"""Vectorised mortality computations over the full inforce.

Computes the cumulative survival matrix (tPx) for every policy and projection year
in a single vectorised NumPy pass, rather than looping over policies one at a time.

The improvement formula matches RnD_Model_example.py exactly:
    improved_qx = base_qx * (1 - projection_scale) ** (calendar_year - BASE_YEAR)

All arrays are float64 so downstream projection and reporting never need to up-cast.
"""

from __future__ import annotations

import numpy as np

from mbc_model.data.models import MortalityTable, PolicyRecord


class MortalityEngine:
    """Builds the cumulative survival matrix (tPx) used by every projection path.

    The output matrix has shape (n_policies, n_years).
    Entry [p, t] = probability that policy p is alive at the end of projection year t,
    measured from the valuation date. This is the actuarial tPx notation.

    The improvement scale is applied as:
        improved_qx = base_qx * (1 - projection_scale) ** (calendar_year - BASE_YEAR)

    Policies at or beyond the terminal age of the mortality table are treated as
    certainly dead: qx = 1.0, px = 0.0, and all subsequent tPx values stay 0.
    """

    def compute_cum_survival(
        self,
        policies: list[PolicyRecord],
        mortality_table: MortalityTable,
        projection_years: np.ndarray,
        valuation_year: int,
    ) -> np.ndarray:
        """Compute tPx for every policy over every projection year.

        Processes males and females in separate vectorised passes using their
        respective mortality tables, then combines into a single output matrix.

        Args:
            policies: Ordered list of inforce policies; output rows follow this order.
            mortality_table: Mortality rates and projection scales indexed by attained age.
            projection_years: Calendar years to project, shape (n_years,), dtype int64.
            valuation_year: Calendar year of the valuation date (e.g. 2024).
                Attained age in each year = projection_year - year_of_birth.

        Returns:
            cumulative_survival_matrix: float64 array, shape (n_policies, n_years).
                Entry [p, t] = probability policy p is alive at end of projection year t.
        """
        number_of_policies: int = len(policies)
        number_of_projection_years: int = len(projection_years)
        number_of_ages_in_table: int = len(mortality_table.male_mortality_rates)

        # Extract years of birth and genders into arrays for vectorised operations.
        # Using arrays lets NumPy process all policies simultaneously instead of looping.
        years_of_birth: np.ndarray = np.array([p.yob for p in policies], dtype=np.int64)
        gender_array: np.ndarray = np.array([p.gender for p in policies])

        # Compute attained age for every (policy, year) combination at once.
        # np.newaxis inserts a length-1 dimension so NumPy can broadcast:
        #   projection_years[np.newaxis, :]  →  shape (1, n_years)
        #   years_of_birth[:, np.newaxis]    →  shape (n_policies, 1)
        # Subtracting these broadcasts to shape (n_policies, n_years).
        attained_age_matrix: np.ndarray = (
            projection_years[np.newaxis, :] - years_of_birth[:, np.newaxis]
        ).astype(np.int64)

        # Clamp age indices to [0, n_ages - 1] to avoid index-out-of-bounds errors.
        # Policies whose actual age exceeds the table will be corrected below.
        age_index_clamped: np.ndarray = np.clip(attained_age_matrix, 0, number_of_ages_in_table - 1)

        # Boolean masks to separate males and females for independent calculations
        is_male_mask: np.ndarray = gender_array == "M"
        is_female_mask: np.ndarray = ~is_male_mask  # everyone who is not male

        # Pre-allocate the output matrix; values filled in by gender below
        cumulative_survival_matrix: np.ndarray = np.empty(
            (number_of_policies, number_of_projection_years), dtype=np.float64
        )

        # Loop over (males, females) using their respective mortality tables.
        # Each iteration processes all policies of one gender simultaneously.
        for gender_mask, base_mortality_rates, projection_scale in (
            (
                is_male_mask,
                mortality_table.male_mortality_rates,
                mortality_table.male_projection_scale,
            ),
            (
                is_female_mask,
                mortality_table.female_mortality_rates,
                mortality_table.female_projection_scale,
            ),
        ):
            if not gender_mask.any():
                # Skip this gender if no policies of that type exist
                continue

            # Select the age index rows for this gender group only
            age_index: np.ndarray = age_index_clamped[gender_mask]  # (n_group, n_years)

            # Compute improvement factor: (1 - projection_scale[age]) ** (year - BASE_YEAR)
            # years_since_base_year has shape (1, n_years) and broadcasts over (n_group, n_years)
            years_since_base_year: np.ndarray = (
                projection_years[np.newaxis, :] - MortalityTable.BASE_YEAR
            ).astype(np.float64)
            improvement_factor: np.ndarray = (
                1.0 - projection_scale[age_index]
            ) ** years_since_base_year  # shape (n_group, n_years)

            # Apply improvement to get the final mortality rate for each policy and year
            improved_mortality_rate: np.ndarray = (
                base_mortality_rates[age_index] * improvement_factor
            )  # shape (n_group, n_years)

            # Probability of surviving each individual year: px = 1 - improved_qx
            probability_of_survival_px: np.ndarray = 1.0 - improved_mortality_rate

            # Zero out px for years where the policy's actual age exceeds the table.
            # The clamping above kept the index in bounds; this corrects the value.
            beyond_terminal_age: np.ndarray = (
                attained_age_matrix[gender_mask] >= number_of_ages_in_table
            )
            probability_of_survival_px[beyond_terminal_age] = 0.0

            # np.cumprod computes the cumulative product along the year axis (axis=1):
            # tPx[t] = px[0] * px[1] * ... * px[t], matching the RnD loop that
            # multiplies cumulative_probability_of_survival_tPx *= px each year.
            cumulative_survival_matrix[gender_mask] = np.cumprod(probability_of_survival_px, axis=1)

        return cumulative_survival_matrix

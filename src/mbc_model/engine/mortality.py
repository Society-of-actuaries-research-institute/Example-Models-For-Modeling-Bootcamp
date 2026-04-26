"""Vectorised mortality computations over the full inforce.

All operations produce float64 arrays so downstream projection and reporting
never need to up-cast.
"""

from __future__ import annotations

import numpy as np

from mbc_model.data.models import MortalityTable, PolicyRecord


class MortalityEngine:
    """Builds the cumulative-survival matrix used by every projection path.

    The matrix has shape (n_policies, n_years).  Entry [p, t] is the
    probability that policy p is alive at the *end* of projection year t,
    i.e. the actuarial tPx starting from the valuation date.

    Improvement scale is applied as:
        improved_qx = base_qx * (1 - scale) ** (calendar_year - BASE_YEAR)

    At ages >= the length of the mortality table the insured is treated as
    having died (qx=1.0, px=0.0) and all subsequent cumulative values stay 0.
    """

    def compute_cum_survival(  # pylint: disable=unused-argument,too-many-locals
        self,
        policies: list[PolicyRecord],
        table: MortalityTable,
        projection_years: np.ndarray,
        valuation_year: int,
    ) -> np.ndarray:
        """Compute tPx for every policy over every projection year.

        Args:
            policies: Ordered inforce list; output rows match this order.
            table: Mortality rates and improvement scales, indexed by attained age.
            projection_years: Calendar years to project, shape (n_years,).
            valuation_year: The calendar year of the valuation date (year portion
                of ModelParameters.valuation_date).  Used to derive attained ages.

        Returns:
            cum_survival: float64 array, shape (n_policies, n_years).
                cum_survival[p, t] = probability policy p is alive at end of
                projection year t.
        """
        n_policies = len(policies)
        n_years = len(projection_years)
        n_ages = len(table.male_qx)

        yobs = np.array([p.yob for p in policies], dtype=np.int64)
        genders = np.array([p.gender for p in policies])

        # Attained age in each projection year: shape (n_policies, n_years)
        ages_mat = (projection_years[np.newaxis, :] - yobs[:, np.newaxis]).astype(np.int64)

        # Clamp to valid index range; beyond terminal age → certain death
        age_idx = np.clip(ages_mat, 0, n_ages - 1)

        male_mask = genders == "M"
        female_mask = ~male_mask

        cum_survival = np.empty((n_policies, n_years), dtype=np.float64)

        for mask, base_qx, improvement in (
            (male_mask, table.male_qx, table.male_improvement),
            (female_mask, table.female_qx, table.female_improvement),
        ):
            if not mask.any():
                continue

            idx = age_idx[mask]  # shape (n_group, n_years)

            # Improvement factor: (1 - scale[age]) ** (year - BASE_YEAR)
            # shape (n_group, n_years)
            exponent = (projection_years[np.newaxis, :] - MortalityTable.BASE_YEAR).astype(
                np.float64
            )
            improve_factor = (1.0 - improvement[idx]) ** exponent

            improved_qx = base_qx[idx] * improve_factor  # (n_group, n_years)

            # At terminal age the base_qx is already 1.0 so improved_qx = 1.0 → px = 0
            # Beyond-terminal ages were clamped to n_ages-1, giving the same result.
            px = 1.0 - improved_qx  # (n_group, n_years)

            # Zero out any years where the clamped age actually exceeded the table
            beyond = ages_mat[mask] >= n_ages  # (n_group, n_years)
            px[beyond] = 0.0

            cum_survival[mask] = np.cumprod(px, axis=1)

        return cum_survival

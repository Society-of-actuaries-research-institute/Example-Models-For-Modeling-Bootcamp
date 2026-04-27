"""Typed dataclasses for all model inputs and outputs.

These dataclasses define the data structures that flow through the model:
    PolicyRecord      — one insured policy from the Inforce sheet
    MortalityTable    — base mortality rates and improvement scales from the Parameters sheet
    ModelParameters   — scalar settings from the Parameters sheet
    ReportingConfig   — output options from the Reporting sheet
    PolicyDetail      — detailed per-year results for one (policy, scenario) pair
    ModelResults      — everything the model produces in a single run
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Literal

import numpy as np


@dataclass
class PolicyRecord:
    """A single insured policy loaded from the Inforce sheet.

    Field names match the Excel column headers in the Inforce sheet.

    Attributes:
        policy_id: Unique policy number (1-based), matching the "Policy #" column.
        yob: Year of birth of the insured (e.g. 1951).
        gender: "M" for male, "F" for female.
        annual_benefit: Benefit paid each year the insured is alive, in dollars.
    """

    policy_id: int               # Unique policy number, 1-based
    yob: int                     # Year of birth (e.g. 1951)
    gender: Literal["M", "F"]   # "M" = male, "F" = female
    annual_benefit: float        # Annual benefit in dollars


@dataclass
class MortalityTable:
    """Mortality rates and improvement scales read from the Parameters sheet.

    Each array has one entry per attained age, starting at age 0.
    The last entry in each mortality rate array must be 1.0 (certain death at the terminal age).

    Naming follows the RnD model: ``male_mortality_rates`` corresponds to
    ``Mortality_Rates["Male"]`` and ``male_projection_scale`` corresponds to
    ``Projection_Scale["Male"]`` in RnD_Model_example.py.

    Not frozen because numpy arrays are not hashable; treat instances as read-only.

    Attributes:
        male_mortality_rates: Base qx for males indexed by attained age, shape (n_ages,).
        female_mortality_rates: Base qx for females indexed by attained age, shape (n_ages,).
        male_projection_scale: Annual improvement percentage for males (e.g. 0.015 = 1.5%),
            shape (n_ages,).
        female_projection_scale: Annual improvement percentage for females, shape (n_ages,).

    Class constant:
        BASE_YEAR: Base year for improvement scale calculations (2012), matching the
            SOA improvement scale used in the bootcamp. Changing this would break
            numerical parity with the RnD model.
    """

    # Improvement formula: improved_qx = base_qx * (1 - scale) ** (calendar_year - BASE_YEAR)
    # BASE_YEAR is hardcoded to 2012 to match the RnD model — do not change.
    BASE_YEAR: ClassVar[int] = 2012

    male_mortality_rates: np.ndarray    # Base qx by age for males,   shape (n_ages,), float64
    female_mortality_rates: np.ndarray  # Base qx by age for females, shape (n_ages,), float64
    male_projection_scale: np.ndarray   # Annual improvement % for males,   shape (n_ages,)
    female_projection_scale: np.ndarray # Annual improvement % for females, shape (n_ages,)


@dataclass(frozen=True)
class ModelParameters:
    """Scalar parameters from the Parameters sheet.

    ``frozen=True`` means these values cannot be modified after creation,
    preventing accidental changes during a model run.

    Attributes:
        valuation_date: End-of-year valuation date; projections start in year + 1.
        last_projection_year: The last year to project (inclusive).
        random_seed: Starting seed for the per-policy random number generators
            when "Which Random Numbers?" is set to "Seed".
    """

    valuation_date: date       # End-of-year valuation date (e.g. 2024-12-31)
    last_projection_year: int  # Last year to project (e.g. 2085)
    random_seed: int           # Base seed for reproducible random number generation


@dataclass
class ReportingConfig:
    """Output settings from the Reporting sheet controlling which tabs to produce.

    Attributes:
        create_policy_results: Whether to write the Policy Results sheet.
        policy_id: Which policy to show in Policy Results (1-based).
        policy_scenario_id: Which scenario to use in Policy Results (1-based).
        create_scenario_results: Whether to write the Scenario Results sheet.
        scenario_id: Which scenario to show in Scenario Results (1-based).
        create_scenario_graph: Whether to embed a bar chart in Scenario Results.
        create_total_results: Whether to write the Total Results sheet.
        create_dashboard_results: Whether to write the Dashboard Results sheet.
        dashboard_scenarios: Number of scenarios to include in Dashboard Results.
        dashboard_policies: Number of policies to include in Dashboard Results.
        discount_rate: Annual discount rate for present value calculations (e.g. 0.04 = 4%).
        create_dashboard_graph: Whether to embed a line chart in Dashboard Results.
    """

    create_policy_results: bool     # True = write the Policy Results sheet
    policy_id: int                  # Which policy to show in Policy Results (1-based)
    policy_scenario_id: int         # Which scenario to use in Policy Results (1-based)
    create_scenario_results: bool   # True = write the Scenario Results sheet
    scenario_id: int                # Which scenario to show in Scenario Results (1-based)
    create_scenario_graph: bool     # True = embed a bar chart in Scenario Results
    create_total_results: bool      # True = write the Total Results sheet
    create_dashboard_results: bool  # True = write the Dashboard Results sheet
    dashboard_scenarios: int        # Number of scenarios in Dashboard Results
    dashboard_policies: int         # Number of policies in Dashboard Results
    discount_rate: float            # Annual discount rate, e.g. 0.04 for 4%
    create_dashboard_graph: bool    # True = embed a line chart in Dashboard Results


@dataclass
class PolicyDetail:
    """Per-year results for exactly one (policy_id, scenario_id) pair.

    Field names are intentionally aligned with the dictionary keys used in
    RnD_Model_example.py so students can cross-reference both implementations.
    Each array contains one value per projection year, in chronological order.

    Attributes:
        policy_id: 1-based policy identifier.
        scenario_id: 1-based scenario identifier.
        random_number: The single random number drawn for this (policy, scenario) pair.
            The survival test is: policy survives year t if
            random_number > cumulative_probability_of_death_1_minus_tPx[t].
        projection_years: Calendar years projected, shape (n_years,), dtype int64.
        attained_ages: Age of the insured in each projected year, shape (n_years,).
        base_qx: Base mortality rate (before improvement) for each year, shape (n_years,).
        improvement_factor: Improvement multiplier = (1 - scale)^(year - BASE_YEAR),
            shape (n_years,). Matches "Improvement" column in the RnD model.
        improved_qx: Final mortality rate = base_qx * improvement_factor, shape (n_years,).
        px: Probability of surviving one year = 1 - improved_qx, shape (n_years,).
        cumulative_probability_of_survival_tPx: Running product of px values (tPx),
            shape (n_years,). Matches RnD key "Cumulative_Probability_of_Survival_tPx".
        cumulative_probability_of_death_1_minus_tPx: 1 - tPx, shape (n_years,).
            Matches RnD key "Cumulative_Probability_of_Death_1_minus_tPx".
        survive_1_dead_0: 1 if the policy is alive in that year, 0 if dead,
            shape (n_years,). Matches RnD key "Survive_1_Dead_0".
        total_cash_flow: annual_benefit * survive_1_dead_0, shape (n_years,).
            Matches RnD key "Total_Cash_Flow".
    """

    policy_id: int           # 1-based policy identifier
    scenario_id: int         # 1-based scenario identifier
    random_number: float     # Single random number for this (policy, scenario) pair

    projection_years: np.ndarray   # Calendar years, shape (n_years,), dtype int64
    attained_ages: np.ndarray      # Age in each year, shape (n_years,), dtype int64

    base_qx: np.ndarray            # Base mortality rate per year, shape (n_years,)
    improvement_factor: np.ndarray # (1 - scale)^(year - BASE_YEAR) per year, shape (n_years,)
    improved_qx: np.ndarray        # base_qx * improvement_factor, shape (n_years,)
    px: np.ndarray                 # 1 - improved_qx, shape (n_years,)

    cumulative_probability_of_survival_tPx: np.ndarray    # Running product of px, shape (n_years,)
    cumulative_probability_of_death_1_minus_tPx: np.ndarray  # 1 - tPx, shape (n_years,)

    survive_1_dead_0: np.ndarray   # 1 = alive, 0 = dead, shape (n_years,), dtype float64
    total_cash_flow: np.ndarray    # annual_benefit * survive_1_dead_0, shape (n_years,)


@dataclass
class ModelResults:
    """All outputs produced by a single complete model run.

    Created by runner.run() and passed to ReportWriter.write().

    Attributes:
        policies: The full list of inforce policies that were projected.
        projection_years: Calendar years of the projection, shape (n_years,).
        cumulative_survival_matrix: tPx for every policy and year,
            shape (n_policies, n_years). Entry [p, t] = probability policy p
            is alive at the end of projection year t.
        scenario_cash_flows: Total cash flows across all policies,
            shape (n_scenarios, n_years). Entry [s, t] = total CF in scenario s, year t.
        scenario_policy_cash_flows: Per-policy cash flows for the single scenario
            selected in ReportingConfig.scenario_id, shape (n_policies, n_years).
            None if Scenario Results was not requested.
        pv_by_scenario: Present value of cash flows for each scenario,
            shape (n_scenarios,). None if Dashboard Results was not requested.
        policy_detail: Detailed per-year results for one (policy, scenario) pair,
            or None if Policy Results was not requested.
        runtime_seconds: Total wall-clock time of the model run in seconds.
        config: The reporting configuration used for this run.
    """

    policies: list[PolicyRecord]
    projection_years: np.ndarray
    cumulative_survival_matrix: np.ndarray    # tPx matrix, shape (n_policies, n_years)
    scenario_cash_flows: np.ndarray           # Total CFs, shape (n_scenarios, n_years)
    scenario_policy_cash_flows: np.ndarray | None  # Per-policy CFs or None
    pv_by_scenario: np.ndarray | None         # PV per scenario or None
    policy_detail: PolicyDetail | None         # Detail for one (policy, scenario) pair or None
    runtime_seconds: float                     # Wall-clock runtime in seconds
    config: ReportingConfig

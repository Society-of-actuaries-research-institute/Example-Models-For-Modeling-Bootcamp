"""Typed dataclasses for all model inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Literal

import numpy as np


@dataclass
class PolicyRecord:
    """A single insured policy from the Inforce sheet.

    Args:
        policy_id: Unique policy identifier (1-based, matches Excel row).
        yob: Year of birth.
        gender: "M" for male, "F" for female.
        annual_benefit: Annual benefit paid while the insured is alive, in dollars.
    """

    policy_id: int
    yob: int
    gender: Literal["M", "F"]
    annual_benefit: float


@dataclass
class MortalityTable:
    """Base mortality rates and improvement scales, keyed by attained age.

    Arrays are indexed by attained age (0 = age 0, 1 = age 1, ...).
    The last entry in each qx array must be 1.0 (terminal age).

    Not frozen: np.ndarray fields are not hashable, so frozen=True would raise
    TypeError on instantiation. Treat instances as logically immutable.

    Class variable BASE_YEAR is hardcoded to 2012 (matches the RnD model and the
    SOA improvement scale used in the bootcamp). It is NOT a user parameter.
    """

    # Improvement scale base year — hardcoded per design Premise 5.
    # Changing this would break numerical parity with the RnD model.
    BASE_YEAR: ClassVar[int] = 2012

    male_qx: np.ndarray  # shape (n_ages,), dtype float64
    female_qx: np.ndarray  # shape (n_ages,), dtype float64
    male_improvement: np.ndarray  # shape (n_ages,), improvement scale factors
    female_improvement: np.ndarray  # shape (n_ages,)


@dataclass(frozen=True)
class ModelParameters:
    """Scalar model parameters read from the Parameters sheet.

    Args:
        valuation_date: End-of-year valuation date; projections start year+1.
        last_projection_year: Final projection year (inclusive).
        random_seed: Seed for per-policy RNG in project_seeded().
    """

    valuation_date: date
    last_projection_year: int
    random_seed: int


@dataclass
class ReportingConfig:
    """Parameters from the Reporting sheet controlling which outputs to produce.

    Args:
        create_policy_results: Whether to write the Policy Results sheet.
        policy_id: Policy number for Policy Results (1-based).
        policy_scenario_id: Scenario number for Policy Results (1-based).
        create_scenario_results: Whether to write the Scenario Results sheet.
        scenario_id: Scenario number for Scenario Results (1-based).
        create_scenario_graph: Whether to embed a chart in Scenario Results.
        create_total_results: Whether to write the Total Results sheet.
        create_dashboard_results: Whether to write the Dashboard Results sheet.
        dashboard_scenarios: Number of scenarios for Dashboard Results.
        dashboard_contracts: Number of contracts for Dashboard Results.
        discount_rate: Annual discount rate for PV calculation (e.g. 0.04 = 4%).
        create_dashboard_graph: Whether to embed a chart in Dashboard Results.
    """

    create_policy_results: bool
    policy_id: int
    policy_scenario_id: int
    create_scenario_results: bool
    scenario_id: int
    create_scenario_graph: bool
    create_total_results: bool
    create_dashboard_results: bool
    dashboard_scenarios: int
    dashboard_contracts: int
    discount_rate: float
    create_dashboard_graph: bool


@dataclass
class PolicyDetail:
    """Per-year results for exactly one (policy_id, scenario_id) pair.

    Used exclusively by the Policy Results sheet. Runner MUST only create one
    instance, for the single pair specified in ReportingConfig. Never iterate
    over all policies to build PolicyDetail objects — that allocates O(n_policies)
    memory with zero benefit.

    Args:
        policy_id: 1-based policy identifier.
        scenario_id: 1-based scenario identifier.
        projection_years: Calendar years of projection, shape (n_years,).
        ages: Attained age in each projection year, shape (n_years,).
        base_qx: Base mortality rate by year, shape (n_years,).
        improvement: Improvement factor by year, shape (n_years,).
        improved_qx: Improved mortality rate by year, shape (n_years,).
        px: Probability of survival in each year, shape (n_years,).
        cum_survival: Cumulative survival probability tPx, shape (n_years,).
        cum_death: 1 - cum_survival, shape (n_years,).
        survive_flag: 1 if alive that year, 0 if dead, shape (n_years,).
        annual_cf: Cash flow per year (benefit × survive_flag), shape (n_years,).
    """

    policy_id: int
    scenario_id: int
    projection_years: np.ndarray
    ages: np.ndarray
    base_qx: np.ndarray
    improvement: np.ndarray
    improved_qx: np.ndarray
    px: np.ndarray
    cum_survival: np.ndarray
    cum_death: np.ndarray
    survive_flag: np.ndarray
    annual_cf: np.ndarray


@dataclass
class ModelResults:
    """All outputs produced by a single model run.

    Args:
        policies: The full inforce list that was projected.
        projection_years: Calendar years, shape (n_years,).
        cum_survival: Cumulative survival matrix, shape (n_policies, n_years).
        scenario_cash_flows: Total cash flows per scenario per year,
            shape (n_scenarios, n_years).
        scenario_policy_cash_flows: Per-policy cash flows for the single scenario
            selected in ReportingConfig.scenario_id, shape (n_policies, n_years).
            None when Scenario Results was not requested.
        pv_by_scenario: Present value per scenario, shape (n_scenarios,).
            None when Dashboard Results was not requested.
        policy_detail: Per-year detail for one policy+scenario pair, or None.
            Must be None unless Policy Results is requested — see PolicyDetail.
        runtime_seconds: Wall-clock runtime of the projection step.
        config: The reporting configuration used for this run.
    """

    policies: list[PolicyRecord]
    projection_years: np.ndarray
    cum_survival: np.ndarray
    scenario_cash_flows: np.ndarray
    scenario_policy_cash_flows: np.ndarray | None
    pv_by_scenario: np.ndarray | None
    policy_detail: PolicyDetail | None
    runtime_seconds: float
    config: ReportingConfig

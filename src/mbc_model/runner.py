"""Top-level model runner.

Entry point for a complete model run:

1. Load inputs from the Excel workbook (ExcelLoader).
2. Build the cumulative-survival matrix (MortalityEngine).
3. Run stochastic projection (ProjectionEngine).
4. Optionally compute present values.
5. Write output workbook (ReportWriter).

Usage::

    from pathlib import Path
    from mbc_model.runner import run

    out_path = run(Path("inputs/Interface_Example_v4.xlsm"))
    print(f"Results written to: {out_path}")
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from mbc_model.data.loader import ExcelLoader
from mbc_model.data.models import ModelResults
from mbc_model.engine.mortality import MortalityEngine
from mbc_model.engine.projection import ProjectionEngine
from mbc_model.reporting.writer import ReportWriter


def run(
    input_path: Path,
    output_dir: Path = Path("outputs"),
    verbose: bool = True,
) -> Path:
    """Execute a complete model run and write the results workbook.

    Args:
        input_path: Path to the xlsm input file.
        output_dir: Directory for the output xlsx file.
        verbose: Print step-by-step progress to stdout.

    Returns:
        Absolute path to the written workbook.
    """
    # ------------------------------------------------------------------ inputs
    if verbose:
        print("Loading inputs...", flush=True)

    loader = ExcelLoader(input_path)
    policies = loader.load_inforce()
    params, mortality_table, random_table = loader.load_parameters()
    config = loader.load_reporting()

    valuation_year = params.valuation_date.year
    projection_years = np.arange(
        valuation_year + 1, params.last_projection_year + 1, dtype=np.int64
    )
    n_scenarios = random_table.shape[0] if random_table is not None else config.dashboard_scenarios

    if verbose:
        print(
            f"  {len(policies):,} policies | {n_scenarios:,} scenarios | "
            f"{len(projection_years)} projection years "
            f"({projection_years[0]}-{projection_years[-1]})"
        )

    # Validate that requested scenario indices fit within the projection
    if config.create_scenario_results and config.scenario_id > n_scenarios:
        raise ValueError(
            f"Scenario Results 'Scenario' = {config.scenario_id} but only "
            f"{n_scenarios} scenario(s) will be run. "
            f"Lower the scenario number in the Reporting sheet."
        )
    if config.create_policy_results and config.policy_scenario_id > n_scenarios:
        raise ValueError(
            f"Policy Results 'Scenario' = {config.policy_scenario_id} but only "
            f"{n_scenarios} scenario(s) will be run. "
            f"Lower the scenario number in the Reporting sheet."
        )

    mort_engine = MortalityEngine()
    proj_engine = ProjectionEngine()

    t_start = time.perf_counter()

    # ------------------------------------------------------- cumulative survival
    if verbose:
        print("Computing cumulative survival...", end=" ", flush=True)
    t_step = time.perf_counter()
    cum_survival = mort_engine.compute_cum_survival(
        policies, mortality_table, projection_years, valuation_year
    )
    if verbose:
        print(f"done ({time.perf_counter() - t_step:.1f}s)")

    # ------------------------------------------------------------ projection
    if verbose:
        print(
            f"Running stochastic projection "
            f"({len(policies):,} policies x {n_scenarios:,} scenarios)...",
            flush=True,
        )
    t_step = time.perf_counter()
    if random_table is not None:
        scenario_cash_flows = proj_engine.project_from_table(
            policies, cum_survival, random_table, verbose=verbose
        )
    else:
        scenario_cash_flows = proj_engine.project_seeded(
            policies, cum_survival, n_scenarios=n_scenarios,
            seed=params.random_seed, verbose=verbose
        )
    if verbose:
        print(f"  done ({time.perf_counter() - t_step:.1f}s)")

    # ------------------------------------------------------- present values
    pv_by_scenario: np.ndarray | None = None
    if config.create_dashboard_results:
        pv_by_scenario = proj_engine.compute_pv(
            scenario_cash_flows,
            projection_years,
            valuation_year,
            config.discount_rate,
        )

    # ----------------------------------------- per-policy scenario cash flows
    scenario_policy_cash_flows: np.ndarray | None = None
    if config.create_scenario_results:
        s_idx = config.scenario_id - 1  # 0-based
        if random_table is not None:
            random_vec = random_table[s_idx, :]  # (n_policies,)
        else:
            random_vec = np.array(
                [
                    float(np.random.default_rng(params.random_seed + p).random(s_idx + 1)[-1])
                    for p in range(len(policies))
                ],
                dtype=np.float64,
            )
        cum_death = 1.0 - cum_survival  # (n_policies, n_years)
        survive = random_vec[:, np.newaxis] > cum_death  # (n_policies, n_years)
        benefits = np.array([p.annual_benefit for p in policies], dtype=np.float64)
        scenario_policy_cash_flows = survive.astype(np.float64) * benefits[:, np.newaxis]

    # ---------------------------------------------------------- policy detail
    policy_detail = None
    if config.create_policy_results:
        p_idx = config.policy_id - 1  # 0-based
        s_idx = config.policy_scenario_id - 1  # 0-based
        policy = policies[p_idx]
        if random_table is not None:
            rng_val = float(random_table[s_idx, p_idx])
        else:
            rng = np.random.default_rng(params.random_seed + p_idx)
            rng_val = float(rng.random(config.policy_scenario_id)[-1])
        policy_detail = proj_engine.build_policy_detail(
            policy,
            config.policy_scenario_id,
            mortality_table,
            projection_years,
            rng_val,
        )

    runtime = time.perf_counter() - t_start

    results = ModelResults(
        policies=policies,
        projection_years=projection_years,
        cum_survival=cum_survival,
        scenario_cash_flows=scenario_cash_flows,
        scenario_policy_cash_flows=scenario_policy_cash_flows,
        pv_by_scenario=pv_by_scenario,
        policy_detail=policy_detail,
        runtime_seconds=runtime,
        config=config,
    )

    # --------------------------------------------------------------- write
    if verbose:
        print("Writing results...", end=" ", flush=True)
    t_step = time.perf_counter()
    writer = ReportWriter(output_dir)
    out_path = writer.write(results)
    if verbose:
        print(f"done ({time.perf_counter() - t_step:.1f}s)")
        print(f"Total runtime: {runtime:.1f}s")

    return out_path

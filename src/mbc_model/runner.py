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
) -> Path:
    """Execute a complete model run and write the results workbook.

    Args:
        input_path: Path to the xlsm input file.
        output_dir: Directory for the output xlsx file.

    Returns:
        Absolute path to the written workbook.
    """
    loader = ExcelLoader(input_path)
    policies = loader.load_inforce()
    params, mortality_table, random_table = loader.load_parameters()
    config = loader.load_reporting()

    valuation_year = params.valuation_date.year
    projection_years = np.arange(
        valuation_year + 1, params.last_projection_year + 1, dtype=np.int64
    )

    mort_engine = MortalityEngine()
    proj_engine = ProjectionEngine()

    t_start = time.perf_counter()

    cum_survival = mort_engine.compute_cum_survival(
        policies, mortality_table, projection_years, valuation_year
    )

    if random_table is not None:
        scenario_cash_flows = proj_engine.project_from_table(
            policies, cum_survival, random_table
        )
    else:
        n_scenarios = 1
        scenario_cash_flows = proj_engine.project_seeded(
            policies, cum_survival, n_scenarios=n_scenarios, seed=params.random_seed
        )

    pv_by_scenario: np.ndarray | None = None
    if config.create_dashboard_results:
        pv_by_scenario = proj_engine.compute_pv(
            scenario_cash_flows,
            projection_years,
            valuation_year,
            config.discount_rate,
        )

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
        pv_by_scenario=pv_by_scenario,
        policy_detail=policy_detail,
        runtime_seconds=runtime,
        config=config,
    )

    writer = ReportWriter(output_dir)
    return writer.write(results)

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
        output_dir: Directory where the output xlsx file is written.
        verbose: If True, print step-by-step progress and timing to stdout.

    Returns:
        Absolute path to the written workbook.
    """
    # ------------------------------------------------------------------ inputs
    if verbose:
        print("Loading inputs...", flush=True)

    # ExcelLoader reads all three sheets: Inforce, Parameters, and Reporting
    excel_loader: ExcelLoader = ExcelLoader(input_path)

    # Load the list of insured policies from the Inforce sheet
    inforce_policies = excel_loader.load_inforce()

    # Load scalar parameters, the mortality table, and (optionally) the random
    # number table from the Parameters sheet.
    # random_number_table is None when "Which Random Numbers?" = "Seed".
    model_parameters, mortality_table, random_number_table = (
        excel_loader.load_parameters()
    )

    # Load output settings (which tabs to create, discount rate, etc.)
    reporting_config = excel_loader.load_reporting()

    # Build the list of calendar years to project: valuation_year+1 to last_projection_year
    valuation_year: int = model_parameters.valuation_date.year
    projection_years: np.ndarray = np.arange(
        valuation_year + 1, model_parameters.last_projection_year + 1, dtype=np.int64
    )

    # Determine how many scenarios to run before starting the projection:
    #   - Table mode: the number of rows in the random number table
    #   - Seed mode: the number specified in the Reporting sheet's "Scenarios" field
    number_of_scenarios: int = (
        random_number_table.shape[0]
        if random_number_table is not None
        else reporting_config.dashboard_scenarios
    )

    if verbose:
        print(
            f"  {len(inforce_policies):,} policies | {number_of_scenarios:,} scenarios | "
            f"{len(projection_years)} projection years "
            f"({projection_years[0]}-{projection_years[-1]})"
        )

    # Validate that scenario numbers in the Reporting sheet are within range.
    # Checking early gives a clear error message instead of a cryptic crash later.
    if (
        reporting_config.create_scenario_results
        and reporting_config.scenario_id > number_of_scenarios
    ):
        raise ValueError(
            f"Scenario Results 'Scenario' = {reporting_config.scenario_id} but only "
            f"{number_of_scenarios} scenario(s) will be run. "
            f"Lower the scenario number in the Reporting sheet."
        )
    if (
        reporting_config.create_policy_results
        and reporting_config.policy_scenario_id > number_of_scenarios
    ):
        raise ValueError(
            f"Policy Results 'Scenario' = {reporting_config.policy_scenario_id} but only "
            f"{number_of_scenarios} scenario(s) will be run. "
            f"Lower the scenario number in the Reporting sheet."
        )

    mortality_engine: MortalityEngine = MortalityEngine()
    projection_engine: ProjectionEngine = ProjectionEngine()

    # Record overall start time to report total runtime at the end
    run_start_time: float = time.perf_counter()

    # ------------------------------------------------------- cumulative survival
    if verbose:
        print("Computing cumulative survival...", end=" ", flush=True)
    step_start_time: float = time.perf_counter()

    # Build the tPx matrix: shape (n_policies, n_years)
    # Entry [p, t] = probability that policy p is alive at the end of projection year t
    cumulative_survival_matrix: np.ndarray = mortality_engine.compute_cum_survival(
        inforce_policies, mortality_table, projection_years, valuation_year
    )

    if verbose:
        print(f"done ({time.perf_counter() - step_start_time:.1f}s)")

    # ------------------------------------------------------------ projection
    if verbose:
        print(
            f"Running stochastic projection "
            f"({len(inforce_policies):,} policies x {number_of_scenarios:,} scenarios)...",
            flush=True,
        )
    step_start_time = time.perf_counter()

    # Run using either the pre-loaded random number table or the seeded generator
    if random_number_table is not None:
        scenario_cash_flows: np.ndarray = projection_engine.project_from_table(
            inforce_policies,
            cumulative_survival_matrix,
            random_number_table,
            verbose=verbose,
        )
    else:
        scenario_cash_flows = projection_engine.project_seeded(
            inforce_policies,
            cumulative_survival_matrix,
            number_of_scenarios=number_of_scenarios,
            seed=model_parameters.random_seed,
            verbose=verbose,
        )

    if verbose:
        print(f"  done ({time.perf_counter() - step_start_time:.1f}s)")

    # ------------------------------------------------------- present values
    # Compute the present value of cash flows for each scenario (Dashboard Results)
    present_value_by_scenario: np.ndarray | None = None
    if reporting_config.create_dashboard_results:
        present_value_by_scenario = projection_engine.compute_pv(
            scenario_cash_flows,
            projection_years,
            valuation_year,
            reporting_config.discount_rate,
        )

    # ----------------------------------------- per-policy scenario cash flows
    # Break out cash flows by individual policy for the single selected scenario
    # (used in the Scenario Results sheet)
    scenario_policy_cash_flows: np.ndarray | None = None
    if reporting_config.create_scenario_results:
        # Convert 1-based scenario number to 0-based array index
        scenario_index: int = reporting_config.scenario_id - 1

        if random_number_table is not None:
            # Use the pre-loaded random number row for this scenario
            random_numbers_for_scenario: np.ndarray = random_number_table[
                scenario_index, :
            ]
        else:
            # Re-derive the exact random numbers that were used in the projection
            # for this scenario, using the same per-policy seeded RNG streams
            random_numbers_for_scenario = np.array(
                [
                    float(
                        np.random.default_rng(
                            model_parameters.random_seed + policy_index
                        ).random(scenario_index + 1)[-1]
                    )
                    for policy_index in range(len(inforce_policies))
                ],
                dtype=np.float64,
            )

        # Cumulative death probability for each (policy, year): 1 - tPx
        cumulative_death_probability: np.ndarray = 1.0 - cumulative_survival_matrix

        # Survival flag for each (policy, year): 1 if alive, 0 if dead.
        # random_numbers_for_scenario[:, np.newaxis] broadcasts to (n_policies, n_years)
        policy_survival_flags: np.ndarray = (
            random_numbers_for_scenario[:, np.newaxis] > cumulative_death_probability
        )

        annual_benefits: np.ndarray = np.array(
            [p.annual_benefit for p in inforce_policies], dtype=np.float64
        )

        # Cash flow per policy per year: benefit if alive, zero if dead
        scenario_policy_cash_flows = (
            policy_survival_flags.astype(np.float64) * annual_benefits[:, np.newaxis]
        )

    # ---------------------------------------------------------- policy detail
    # Build the detailed per-year table for one (policy, scenario) pair
    # (used in the Policy Results sheet)
    policy_detail = None
    if reporting_config.create_policy_results:
        # Convert 1-based IDs to 0-based array indices
        policy_index: int = reporting_config.policy_id - 1
        scenario_index = reporting_config.policy_scenario_id - 1
        selected_policy = inforce_policies[policy_index]

        if random_number_table is not None:
            random_number_for_policy: float = float(
                random_number_table[scenario_index, policy_index]
            )
        else:
            # Reproduce the same random number that was used for this policy in the projection
            random_number_generator = np.random.default_rng(
                model_parameters.random_seed + policy_index
            )
            random_number_for_policy = float(
                random_number_generator.random(reporting_config.policy_scenario_id)[-1]
            )

        policy_detail = projection_engine.build_policy_detail(
            selected_policy,
            reporting_config.policy_scenario_id,
            mortality_table,
            projection_years,
            random_number_for_policy,
        )

    total_runtime_seconds: float = time.perf_counter() - run_start_time

    # Bundle all outputs into a single ModelResults object for the writer
    model_results: ModelResults = ModelResults(
        policies=inforce_policies,
        projection_years=projection_years,
        cumulative_survival_matrix=cumulative_survival_matrix,
        scenario_cash_flows=scenario_cash_flows,
        scenario_policy_cash_flows=scenario_policy_cash_flows,
        pv_by_scenario=present_value_by_scenario,
        policy_detail=policy_detail,
        runtime_seconds=total_runtime_seconds,
        config=reporting_config,
    )

    # --------------------------------------------------------------- write
    if verbose:
        print("Writing results...", end=" ", flush=True)
    step_start_time = time.perf_counter()

    report_writer: ReportWriter = ReportWriter(output_dir)
    output_path: Path = report_writer.write(model_results)

    if verbose:
        print(f"done ({time.perf_counter() - step_start_time:.1f}s)")
        print(f"Total runtime: {total_runtime_seconds:.1f}s")

    return output_path

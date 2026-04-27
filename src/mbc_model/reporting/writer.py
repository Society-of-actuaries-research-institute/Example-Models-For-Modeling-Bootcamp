"""Excel report writer.

Writes a new ``outputs/results_{timestamp}.xlsx`` workbook with up to four
sheets as directed by ReportingConfig:

* **Policy Results**    — per-year detail for one (policy_id, scenario_id) pair.
* **Scenario Results**  — annual cash flows for every policy in one scenario.
* **Total Results**     — annual cash flows for every scenario.
* **Dashboard Results** — descriptive stats (mean, median, std, min, max PV)
                          across scenarios, optionally a bar chart.

All sheets are populated row-by-row with ``ws.append()``; openpyxl normal mode
is used so that chart images can be embedded via ``add_image()``.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl.drawing.image import Image as XlImage

from mbc_model.data.models import ModelResults

# Use the non-interactive Agg backend so matplotlib never tries to open a window.
# This must be set before any other matplotlib/pyplot calls.
matplotlib.use("Agg")


class ReportWriter:
    """Writes model results to a new Excel workbook.

    Args:
        output_dir: Directory where the output file is written.
            Created automatically if it does not exist.
    """

    def __init__(self, output_dir: Path = Path("outputs")) -> None:
        self._output_dir: Path = output_dir  # Output directory for the xlsx file

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, results: ModelResults) -> Path:
        """Write all requested sheets and return the path to the new workbook.

        Args:
            results: Fully-populated ModelResults from the runner.

        Returns:
            Absolute path to the written xlsx file.
        """
        # Create the output directory if it does not already exist
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Build a timestamped filename so each run produces a unique file
        timestamp_string: str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path: Path = self._output_dir / f"results_{timestamp_string}.xlsx"

        workbook = openpyxl.Workbook()
        # openpyxl creates one blank sheet by default; remove it so we control all sheets
        workbook.remove(workbook.active)  # type: ignore[arg-type]

        reporting_config = results.config

        if reporting_config.create_policy_results and results.policy_detail is not None:
            self._write_policy_results(workbook, results)

        if reporting_config.create_scenario_results:
            self._write_scenario_results(workbook, results)

        if reporting_config.create_total_results:
            self._write_total_results(workbook, results)

        if reporting_config.create_dashboard_results:
            self._write_dashboard_results(workbook, results)

        if not workbook.sheetnames:
            raise ValueError(
                "ReportingConfig has no output sheets enabled. "
                "Set at least one 'Create?' field to 'Yes' in the Reporting sheet."
            )

        workbook.save(output_path)
        return output_path.resolve()

    # ------------------------------------------------------------------
    # Sheet writers
    # ------------------------------------------------------------------

    def _write_policy_results(
        self, workbook: openpyxl.Workbook, results: ModelResults
    ) -> None:
        """Write the Policy Results sheet with per-year detail for one (policy, scenario)."""
        policy_detail = results.policy_detail
        assert policy_detail is not None

        # Look up the full PolicyRecord for this policy so we can show gender and benefit
        matched_policy = next(
            p for p in results.policies if p.policy_id == policy_detail.policy_id
        )

        worksheet = workbook.create_sheet("Policy Results")

        # Header block: policy and scenario identification (rows 1-4)
        worksheet.append(["Policy", policy_detail.policy_id, None, "Scenario", policy_detail.scenario_id])
        worksheet.append(["Gender", matched_policy.gender, None, "Random Number", policy_detail.random_number])
        worksheet.append(["Benefit", matched_policy.annual_benefit, None, None, None, None, "Cumulative Probability of"])
        worksheet.append([None, None, None, None, None, None, "Survival", "Death", "Survive = 1"])

        # Column headers (row 5): one column per output variable
        worksheet.append(
            [
                "Year",
                "Age",
                "Base Qx",
                "Improvement",
                "Improved Qx",
                "Px",
                "tPx",
                "1 - tPx",
                "Dead = 0",
                "Total Cash Flow",
            ]
        )

        # Data rows: one row per projection year
        for year_index, projection_year in enumerate(policy_detail.projection_years):
            worksheet.append(
                [
                    int(projection_year),
                    int(policy_detail.attained_ages[year_index]),
                    float(policy_detail.base_qx[year_index]),
                    float(policy_detail.improvement_factor[year_index]),
                    float(policy_detail.improved_qx[year_index]),
                    float(policy_detail.px[year_index]),
                    float(policy_detail.cumulative_probability_of_survival_tPx[year_index]),
                    float(policy_detail.cumulative_probability_of_death_1_minus_tPx[year_index]),
                    int(policy_detail.survive_1_dead_0[year_index]),
                    float(policy_detail.total_cash_flow[year_index]),
                ]
            )

    def _write_scenario_results(
        self, workbook: openpyxl.Workbook, results: ModelResults
    ) -> None:
        """Write the Scenario Results sheet with cash flows by policy for one scenario."""
        reporting_config = results.config
        scenario_index: int = reporting_config.scenario_id - 1  # convert 1-based to 0-based

        inforce_policies = results.policies
        projection_years = results.projection_years
        policy_cash_flows = results.scenario_policy_cash_flows  # (n_policies, n_years) or None
        total_scenario_cash_flow = results.scenario_cash_flows[scenario_index]  # (n_years,)

        # When there are many policies, showing one column per policy is impractical
        show_total_only: bool = len(inforce_policies) > 10

        worksheet = workbook.create_sheet("Scenario Results")
        worksheet.append(["Scenario", reporting_config.scenario_id])
        worksheet.append([None, "Cash Flow Projection by Policy"])

        if show_total_only:
            # More than 10 policies: just show Year and Total to keep the sheet manageable
            worksheet.append(["Year", "Total"])
        else:
            # 10 or fewer policies: show a column per policy plus Total
            worksheet.append(
                ["Year \\ Policy"] + [p.policy_id for p in inforce_policies] + ["Total"]
            )

        # Data rows: one row per projection year
        for year_index, projection_year in enumerate(projection_years):
            if show_total_only:
                worksheet.append([int(projection_year), float(total_scenario_cash_flow[year_index])])
            else:
                if policy_cash_flows is not None:
                    cash_flow_per_policy: list[float] = [
                        float(policy_cash_flows[policy_index, year_index])
                        for policy_index in range(len(inforce_policies))
                    ]
                else:
                    cash_flow_per_policy = [""] * len(inforce_policies)  # type: ignore[list-item]
                worksheet.append(
                    [int(projection_year)] + cash_flow_per_policy + [float(total_scenario_cash_flow[year_index])]
                )

        if reporting_config.create_scenario_graph:
            # When there are many policies, draw only the Total line to avoid a cluttered graph
            chart_policy_cash_flows = None if len(inforce_policies) > 10 else policy_cash_flows
            figure = self._make_stacked_bar_chart(
                projection_years=projection_years,
                policy_cash_flows=chart_policy_cash_flows,
                total_cash_flow=total_scenario_cash_flow,
                policies=inforce_policies,
                title=f"Scenario {reporting_config.scenario_id} Cash Flows by Policy",
            )
            self._embed_chart(worksheet, figure, anchor="A" + str(worksheet.max_row + 2))

    def _write_total_results(
        self, workbook: openpyxl.Workbook, results: ModelResults
    ) -> None:
        """Write the Total Results sheet with cash flows by scenario for each year."""
        worksheet = workbook.create_sheet("Total Results")
        number_of_scenarios: int = results.scenario_cash_flows.shape[0]
        projection_years = results.projection_years
        discount_rate: float = results.config.discount_rate

        # Compute the present value of each scenario's cash flows for the header rows
        valuation_year: int = int(projection_years[0]) - 1
        time_periods_from_valuation: np.ndarray = (
            projection_years - valuation_year
        ).astype(np.float64)
        discount_factors_by_year: np.ndarray = (
            1.0 / (1.0 + discount_rate) ** time_periods_from_valuation
        )
        present_values_by_scenario: np.ndarray = (
            results.scenario_cash_flows @ discount_factors_by_year
        )

        # Summary rows shown regardless of scenario count
        worksheet.append(["Discount Rate", discount_rate])
        worksheet.append(
            ["PV Cash Flow"] + [float(present_values_by_scenario[s]) for s in range(number_of_scenarios)]
        )

        # Full cash-flow table by scenario and year (only for small runs)
        if number_of_scenarios <= 25:
            worksheet.append([None, "Total Cash Flow by Scenario"])
            worksheet.append(["Year \\ Scen"] + list(range(1, number_of_scenarios + 1)))
            for year_index, projection_year in enumerate(projection_years):
                data_row: list = [int(projection_year)] + [
                    float(results.scenario_cash_flows[scenario_index, year_index])
                    for scenario_index in range(number_of_scenarios)
                ]
                worksheet.append(data_row)

    def _write_dashboard_results(
        self, workbook: openpyxl.Workbook, results: ModelResults
    ) -> None:
        """Write the Dashboard Results sheet with summary statistics across scenarios."""
        reporting_config = results.config
        present_values_by_scenario = results.pv_by_scenario
        if present_values_by_scenario is None:
            # pv_by_scenario is only populated when Dashboard Results is requested
            return

        number_of_scenarios_used: int = min(
            reporting_config.dashboard_scenarios, len(present_values_by_scenario)
        )
        number_of_policies_used: int = min(
            reporting_config.dashboard_policies, len(results.policies)
        )

        # Slice the PV array down to the requested number of scenarios
        present_values_subset: np.ndarray = present_values_by_scenario[:number_of_scenarios_used]

        # Compute summary statistics across all selected scenarios
        mean_present_value: float = float(np.mean(present_values_subset))
        median_present_value: float = float(np.median(present_values_subset))
        std_dev_present_value: float = float(np.std(present_values_subset))
        min_present_value: float = float(np.min(present_values_subset))
        max_present_value: float = float(np.max(present_values_subset))

        # Format runtime as HH:MM:SS for readability
        total_runtime_seconds: int = int(results.runtime_seconds)
        runtime_formatted: str = (
            f"{total_runtime_seconds // 3600:02d}:"
            f"{(total_runtime_seconds % 3600) // 60:02d}:"
            f"{total_runtime_seconds % 60:02d}"
        )

        worksheet = workbook.create_sheet("Dashboard Results")
        worksheet.append(["Number of Scenarios", None, number_of_scenarios_used])
        worksheet.append(["Number of Policies", None, number_of_policies_used])
        worksheet.append(["Discount rate", None, reporting_config.discount_rate])
        worksheet.append(["PV Cash Flow Statistics"])
        worksheet.append(["Mean", "Median", "Std Dev", "Min", "Max", "Runtime"])
        worksheet.append([
            mean_present_value,
            median_present_value,
            std_dev_present_value,
            min_present_value,
            max_present_value,
            runtime_formatted,
        ])

        if reporting_config.create_dashboard_graph:
            selected_scenario_indices: np.ndarray | None = None
            if number_of_scenarios_used > 25:
                # Too many scenarios to plot individually — select 11 representative ones
                # at each 10th percentile of the PV distribution (P0, P10, ..., P100)
                scenarios_sorted_by_pv: np.ndarray = np.argsort(present_values_subset)
                # np.linspace picks 11 evenly-spaced positions from index 0 to n-1
                percentile_positions: np.ndarray = np.round(
                    np.linspace(0, number_of_scenarios_used - 1, 11)
                ).astype(int)
                selected_scenario_indices = scenarios_sorted_by_pv[percentile_positions]

            figure = self._make_scenario_lines_chart(
                projection_years=results.projection_years,
                scenario_cash_flows=results.scenario_cash_flows[:number_of_scenarios_used],
                selected_indices=selected_scenario_indices,
            )
            self._embed_chart(worksheet, figure, anchor="A" + str(worksheet.max_row + 2))

    # ------------------------------------------------------------------
    # Chart helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_stacked_bar_chart(
        projection_years: np.ndarray,
        policy_cash_flows: "np.ndarray | None",
        total_cash_flow: np.ndarray,
        policies: "list",
        title: str,
    ) -> "plt.Figure":
        """Build a stacked bar chart with one bar segment per policy and a black total line.

        When policy_cash_flows is None, only the total line is drawn (used when
        there are more than 10 policies).

        Args:
            projection_years: X-axis values (calendar years).
            policy_cash_flows: Per-policy cash flows, shape (n_policies, n_years), or None.
            total_cash_flow: Aggregate cash flows across all policies, shape (n_years,).
            policies: List of PolicyRecord objects (used for legend labels).
            title: Chart title string.

        Returns:
            A matplotlib Figure object ready to be embedded in Excel.
        """
        figure, chart_axes = plt.subplots(figsize=(10, 5))

        if policy_cash_flows is not None:
            # Stack one bar segment per policy, building up from the bottom
            stacked_bar_bottom: np.ndarray = np.zeros(len(projection_years), dtype=np.float64)
            for policy_index, policy_record in enumerate(policies):
                chart_axes.bar(
                    projection_years,
                    policy_cash_flows[policy_index],
                    bottom=stacked_bar_bottom,
                    label=f"Policy_{policy_record.policy_id}",
                )
                stacked_bar_bottom += policy_cash_flows[policy_index]

        # Draw the total as a black dashed line on top of the bars
        chart_axes.plot(
            projection_years,
            total_cash_flow,
            color="black",
            marker="o",
            markersize=3,
            linestyle="--",
            label="Total",
        )
        chart_axes.set_title(title)
        chart_axes.set_xlabel("Year")
        chart_axes.set_ylabel("Cash Flow")
        chart_axes.legend()
        figure.tight_layout()
        return figure

    @staticmethod
    def _make_scenario_lines_chart(
        projection_years: np.ndarray,
        scenario_cash_flows: np.ndarray,
        selected_indices: "np.ndarray | None" = None,
    ) -> "plt.Figure":
        """Build a line chart with one line per scenario over the projection years.

        When selected_indices is provided, only those scenarios are plotted and
        labelled as Percentile_0_Scenario_N ... Percentile_100_Scenario_N
        (used when there are more than 25 scenarios to avoid an unreadable graph).

        Args:
            projection_years: X-axis values (calendar years).
            scenario_cash_flows: Cash flows, shape (n_scenarios, n_years).
            selected_indices: 0-based indices of the scenarios to plot, or None
                to plot all scenarios.

        Returns:
            A matplotlib Figure object ready to be embedded in Excel.
        """
        figure, chart_axes = plt.subplots(figsize=(10, 5))

        if selected_indices is not None:
            # Plot only the selected percentile-representative scenarios
            for percentile_index, scenario_index in enumerate(selected_indices):
                # Label shows both the percentile rank and the original scenario number
                scenario_label: str = (
                    f"Percentile_{percentile_index * 10}_Scenario_{int(scenario_index) + 1}"
                )
                chart_axes.plot(
                    projection_years,
                    scenario_cash_flows[scenario_index],
                    label=scenario_label,
                )
        else:
            # Plot all scenarios with simple sequential labels
            for scenario_index in range(scenario_cash_flows.shape[0]):
                chart_axes.plot(
                    projection_years,
                    scenario_cash_flows[scenario_index],
                    label=f"Scenario_{scenario_index + 1}",
                )

        chart_axes.set_title("Cash Flow Projection by Scenario")
        chart_axes.set_xlabel("Year")
        chart_axes.set_ylabel("Cash Flow")
        chart_axes.legend()
        figure.tight_layout()
        return figure

    @staticmethod
    def _embed_chart(
        worksheet: openpyxl.worksheet.worksheet.Worksheet,
        figure: "plt.Figure",
        anchor: str,
    ) -> None:
        """Save a matplotlib figure as a PNG and embed it in an Excel worksheet.

        Args:
            worksheet: The openpyxl worksheet to embed the image in.
            figure: The matplotlib figure to save.
            anchor: Cell address where the top-left corner of the image is placed (e.g. "A10").
        """
        # io.BytesIO is an in-memory file buffer — we save the PNG here instead of
        # writing to disk, then pass the buffer directly to openpyxl
        image_buffer = io.BytesIO()
        figure.savefig(image_buffer, format="png", dpi=100)
        plt.close(figure)  # Release matplotlib memory for this figure
        image_buffer.seek(0)  # Rewind the buffer to the beginning before reading

        chart_image = XlImage(image_buffer)
        worksheet.add_image(chart_image, anchor)

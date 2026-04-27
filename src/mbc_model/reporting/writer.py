"""Excel report writer.

Writes a new `outputs/results_{timestamp}.xlsx` workbook with up to four
sheets as directed by ReportingConfig:

* **Policy Results**   — per-year detail for one (policy_id, scenario_id) pair.
* **Scenario Results** — annual cash flows for every policy in one scenario.
* **Total Results**    — annual cash flows for every scenario.
* **Dashboard Results**— descriptive stats (mean, median, std, min, max PV)
                         across scenarios, optionally a bar chart.

All sheets are populated row-by-row with ``ws.append()``; openpyxl normal mode
is used throughout so that chart images can be embedded via ``add_image()``.
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

matplotlib.use("Agg")  # non-interactive backend; must be set before any plt call


class ReportWriter:
    """Writes model results to a new Excel workbook.

    Args:
        output_dir: Directory where the output file is written.
            Created if it does not exist.
    """

    def __init__(self, output_dir: Path = Path("outputs")) -> None:
        self._output_dir = output_dir

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
        self._output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = self._output_dir / f"results_{timestamp}.xlsx"

        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # type: ignore[arg-type]  # remove the default blank sheet

        cfg = results.config
        if cfg.create_policy_results and results.policy_detail is not None:
            self._write_policy_results(wb, results)

        if cfg.create_scenario_results:
            self._write_scenario_results(wb, results)

        if cfg.create_total_results:
            self._write_total_results(wb, results)

        if cfg.create_dashboard_results:
            self._write_dashboard_results(wb, results)

        if not wb.sheetnames:
            raise ValueError(
                "ReportingConfig has no output sheets enabled. "
                "Set at least one 'Create?' field to 'Yes' in the Reporting sheet."
            )

        wb.save(out_path)
        return out_path.resolve()

    # ------------------------------------------------------------------
    # Sheet writers
    # ------------------------------------------------------------------

    def _write_policy_results(
        self, wb: openpyxl.Workbook, results: ModelResults
    ) -> None:
        detail = results.policy_detail
        assert detail is not None

        policy = next(p for p in results.policies if p.policy_id == detail.policy_id)

        ws = wb.create_sheet("Policy Results")
        ws.append(["Policy", detail.policy_id, None, "Scenario", detail.scenario_id])
        ws.append(["Gender", policy.gender, None, "Random Number", detail.random_number])
        ws.append(["Benefit", policy.annual_benefit, None, None, None, None, "Cumulative Probability of"])
        ws.append([None, None, None, None, None, None, "Survival", "Death", "Survive = 1"])
        ws.append(
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
        for i, year in enumerate(detail.projection_years):
            ws.append(
                [
                    int(year),
                    int(detail.ages[i]),
                    float(detail.base_qx[i]),
                    float(detail.improvement[i]),
                    float(detail.improved_qx[i]),
                    float(detail.px[i]),
                    float(detail.cum_survival[i]),
                    float(detail.cum_death[i]),
                    int(detail.survive_flag[i]),
                    float(detail.annual_cf[i]),
                ]
            )

    def _write_scenario_results(
        self, wb: openpyxl.Workbook, results: ModelResults
    ) -> None:
        cfg = results.config
        scenario_idx = cfg.scenario_id - 1  # 0-based
        policies = results.policies
        years = results.projection_years
        policy_cfs = results.scenario_policy_cash_flows  # (n_policies, n_years) or None
        scenario_cf = results.scenario_cash_flows[scenario_idx]  # (n_years,)

        ws = wb.create_sheet("Scenario Results")
        ws.append(["Scenario", cfg.scenario_id])
        ws.append([None, "Cash Flow Projection by Contract"])
        ws.append(["Year \\ Contract"] + [p.policy_id for p in policies] + ["Total"])

        for t, year in enumerate(years):
            if policy_cfs is not None:
                per_policy = [float(policy_cfs[p, t]) for p in range(len(policies))]
            else:
                per_policy = [""] * len(policies)
            ws.append([int(year)] + per_policy + [float(scenario_cf[t])])

        if cfg.create_scenario_graph:
            chart_policy_cfs = None if len(policies) > 10 else policy_cfs
            fig = self._make_stacked_bar_chart(
                years=years,
                policy_cfs=chart_policy_cfs,
                total_cf=scenario_cf,
                policies=policies,
                title=f"Scenario {cfg.scenario_id} Cash Flows by Policy",
            )
            self._embed_chart(ws, fig, anchor="A" + str(ws.max_row + 2))

    def _write_total_results(
        self, wb: openpyxl.Workbook, results: ModelResults
    ) -> None:
        ws = wb.create_sheet("Total Results")
        n_scenarios = results.scenario_cash_flows.shape[0]
        years = results.projection_years
        discount_rate = results.config.discount_rate

        valuation_year = int(years[0]) - 1
        t_exp = (years - valuation_year).astype(np.float64)
        discount_factors = 1.0 / (1.0 + discount_rate) ** t_exp
        pv = results.scenario_cash_flows @ discount_factors

        ws.append(["Discount Rate", discount_rate])
        ws.append(["PV Cash Flow"] + [float(pv[s]) for s in range(n_scenarios)])
        ws.append([None, "Total Cash Flow by Scenario"])
        ws.append(["Year \\ Scen"] + list(range(1, n_scenarios + 1)))

        for t_idx, year in enumerate(years):
            row = [int(year)] + [
                float(results.scenario_cash_flows[s, t_idx]) for s in range(n_scenarios)
            ]
            ws.append(row)

    def _write_dashboard_results(
        self, wb: openpyxl.Workbook, results: ModelResults
    ) -> None:
        cfg = results.config
        pv = results.pv_by_scenario
        if pv is None:
            return

        n_used = min(cfg.dashboard_scenarios, len(pv))
        n_policies = min(cfg.dashboard_policies, len(results.policies))
        pv_subset = pv[:n_used]

        mean_pv = float(np.mean(pv_subset))
        median_pv = float(np.median(pv_subset))
        std_pv = float(np.std(pv_subset))
        min_pv = float(np.min(pv_subset))
        max_pv = float(np.max(pv_subset))

        ws = wb.create_sheet("Dashboard Results")
        ws.append(["Number of Scenarios", None, n_used])
        ws.append(["Number of Policies", None, n_policies])
        ws.append(["Discount rate", None, cfg.discount_rate])
        ws.append(["PV Cash Flow Statistics"])
        ws.append(["Mean", "Median", "Std Dev", "Min", "Max", "Runtime"])
        ws.append([mean_pv, median_pv, std_pv, min_pv, max_pv, results.runtime_seconds])

        if cfg.create_dashboard_graph:
            selected: np.ndarray | None = None
            if n_used > 25:
                sorted_idx = np.argsort(pv_subset)
                positions = np.round(np.linspace(0, n_used - 1, 11)).astype(int)
                selected = sorted_idx[positions]
            fig = self._make_scenario_lines_chart(
                years=results.projection_years,
                scenario_cash_flows=results.scenario_cash_flows[:n_used],
                selected_indices=selected,
            )
            self._embed_chart(ws, fig, anchor="A" + str(ws.max_row + 2))

    # ------------------------------------------------------------------
    # Chart helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_stacked_bar_chart(
        years: np.ndarray,
        policy_cfs: "np.ndarray | None",
        total_cf: np.ndarray,
        policies: "list",
        title: str,
    ) -> "plt.Figure":
        """Stacked bar per policy + black total line, matching plot_scenario_results."""
        fig, ax = plt.subplots(figsize=(10, 5))
        if policy_cfs is not None:
            bottom = np.zeros(len(years), dtype=np.float64)
            for p, policy in enumerate(policies):
                ax.bar(
                    years,
                    policy_cfs[p],
                    bottom=bottom,
                    label=f"Policy_{policy.policy_id}",
                )
                bottom += policy_cfs[p]
        ax.plot(years, total_cf, color="black", marker="o", markersize=3,
                linestyle="--", label="Total")
        ax.set_title(title)
        ax.set_xlabel("Year")
        ax.set_ylabel("Cash Flow")
        ax.legend()
        fig.tight_layout()
        return fig

    @staticmethod
    def _make_scenario_lines_chart(
        years: np.ndarray,
        scenario_cash_flows: np.ndarray,
        selected_indices: "np.ndarray | None" = None,
    ) -> "plt.Figure":
        """One line per scenario over projection years.

        When selected_indices is provided, only those rows are plotted and
        labelled as P0, P10, …, P100 (percentile representatives).
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        if selected_indices is not None:
            percentile_labels = [f"P{i * 10}" for i in range(len(selected_indices))]
            for label, s in zip(percentile_labels, selected_indices):
                ax.plot(years, scenario_cash_flows[s], label=label)
        else:
            for s in range(scenario_cash_flows.shape[0]):
                ax.plot(years, scenario_cash_flows[s], label=f"Scenario_{s + 1}")
        ax.set_title("Cash Flow Projection by Scenario")
        ax.set_xlabel("Year")
        ax.set_ylabel("Cash Flow")
        ax.legend()
        fig.tight_layout()
        return fig

    @staticmethod
    def _embed_chart(  # type: ignore[name-defined]
        ws: openpyxl.worksheet.worksheet.Worksheet,
        fig: "plt.Figure",
        anchor: str,
    ) -> None:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        plt.close(fig)
        buf.seek(0)
        img = XlImage(buf)
        ws.add_image(img, anchor)

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

        ws = wb.create_sheet("Policy Results")
        ws.append(
            [
                "Year",
                "Age",
                "Base_Qx",
                "Improvement",
                "Improved_Qx",
                "Px",
                "tPx",
                "1-tPx",
                "Survive_1_Dead_0",
                "Cash_Flow",
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
        policy_headers = [f"Policy_{p.policy_id}" for p in policies]
        ws.append(["Year"] + policy_headers + ["Total"])

        for t, year in enumerate(years):
            if policy_cfs is not None:
                per_policy = [float(policy_cfs[p, t]) for p in range(len(policies))]
            else:
                per_policy = [""] * len(policies)
            ws.append([int(year)] + per_policy + [float(scenario_cf[t])])

        if cfg.create_scenario_graph:
            fig = self._make_stacked_bar_chart(
                years=years,
                policy_cfs=policy_cfs,
                total_cf=scenario_cf,
                policies=policies,
                title=f"Scenario {cfg.scenario_id} Cash Flows by Policy",
            )
            self._embed_chart(ws, fig, anchor="A" + str(len(years) + 3))

    def _write_total_results(
        self, wb: openpyxl.Workbook, results: ModelResults
    ) -> None:
        ws = wb.create_sheet("Total Results")
        n_scenarios = results.scenario_cash_flows.shape[0]
        scenario_headers = [f"Scenario_{s + 1}" for s in range(n_scenarios)]
        ws.append(["Year"] + scenario_headers)

        for t, year in enumerate(results.projection_years):
            row = [int(year)] + [
                float(results.scenario_cash_flows[s, t]) for s in range(n_scenarios)
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
        pv_subset = pv[:n_used]

        mean_pv = float(np.mean(pv_subset))
        median_pv = float(np.median(pv_subset))
        std_pv = float(np.std(pv_subset))
        min_pv = float(np.min(pv_subset))
        max_pv = float(np.max(pv_subset))

        ws = wb.create_sheet("Dashboard Results")
        ws.append(["Metric", "Value"])
        ws.append(["Runtime (seconds)", results.runtime_seconds])
        ws.append(["Scenarios used", n_used])
        ws.append(["Mean PV Cash Flow", mean_pv])
        ws.append(["Median PV Cash Flow", median_pv])
        ws.append(["Std Dev PV Cash Flow", std_pv])
        ws.append(["Min PV Cash Flow", min_pv])
        ws.append(["Max PV Cash Flow", max_pv])

        if cfg.create_dashboard_graph:
            fig = self._make_scenario_lines_chart(
                years=results.projection_years,
                scenario_cash_flows=results.scenario_cash_flows[:n_used],
                n_scenarios=n_used,
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
        n_scenarios: int,
    ) -> "plt.Figure":
        """One line per scenario over projection years, matching plot_cash_flows_by_scenario."""
        fig, ax = plt.subplots(figsize=(10, 5))
        for s in range(n_scenarios):
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

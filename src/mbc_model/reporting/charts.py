"""Shared matplotlib chart renderers for Excel and desktop outputs."""

from __future__ import annotations

import base64
import io

import matplotlib
import numpy as np

# Use the non-interactive Agg backend so matplotlib never tries to open a window.
# This must be set before any other matplotlib/pyplot calls.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # pylint: disable=wrong-import-position

from mbc_model.data.models import ModelResults, PolicyRecord

GRAPH_NOT_REQUESTED_MESSAGE = "Graph was not requested in the Reporting tab."


def make_scenario_cash_flows_chart(results: ModelResults) -> "plt.Figure | None":
    """Build the Scenario Results graph when requested by ReportingConfig."""
    if not results.config.create_scenario_graph:
        return None

    scenario_index: int = results.config.scenario_id - 1
    total_scenario_cash_flow = results.scenario_cash_flows[scenario_index]
    chart_policy_cash_flows = (
        None if len(results.policies) > 10 else results.scenario_policy_cash_flows
    )
    return make_stacked_bar_chart(
        projection_years=results.projection_years,
        policy_cash_flows=chart_policy_cash_flows,
        total_cash_flow=total_scenario_cash_flow,
        policies=results.policies,
        title=f"Scenario {results.config.scenario_id} Cash Flows by Policy",
    )


def make_dashboard_cash_flow_chart(results: ModelResults) -> "plt.Figure | None":
    """Build the Dashboard Results graph when requested by ReportingConfig."""
    if not results.config.create_dashboard_graph or results.pv_by_scenario is None:
        return None

    number_of_scenarios_used: int = min(
        results.config.dashboard_scenarios, len(results.pv_by_scenario)
    )
    selected_scenario_indices: np.ndarray | None = None

    if number_of_scenarios_used > 25:
        present_values_subset = results.pv_by_scenario[:number_of_scenarios_used]
        scenarios_sorted_by_pv: np.ndarray = np.argsort(present_values_subset)
        percentile_positions: np.ndarray = np.round(
            np.linspace(0, number_of_scenarios_used - 1, 11)
        ).astype(int)
        selected_scenario_indices = scenarios_sorted_by_pv[percentile_positions]

    return make_scenario_lines_chart(
        projection_years=results.projection_years,
        scenario_cash_flows=results.scenario_cash_flows[:number_of_scenarios_used],
        selected_indices=selected_scenario_indices,
    )


def make_stacked_bar_chart(
    projection_years: np.ndarray,
    policy_cash_flows: "np.ndarray | None",
    total_cash_flow: np.ndarray,
    policies: list[PolicyRecord],
    title: str,
) -> "plt.Figure":
    """Build a stacked bar chart with one bar segment per policy and a total line."""
    figure, chart_axes = plt.subplots(figsize=(10, 5))

    if policy_cash_flows is not None:
        stacked_bar_bottom: np.ndarray = np.zeros(len(projection_years), dtype=np.float64)
        for policy_index, policy_record in enumerate(policies):
            chart_axes.bar(
                projection_years,
                policy_cash_flows[policy_index],
                bottom=stacked_bar_bottom,
                label=f"Policy_{policy_record.policy_id}",
            )
            stacked_bar_bottom += policy_cash_flows[policy_index]

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


def make_scenario_lines_chart(
    projection_years: np.ndarray,
    scenario_cash_flows: np.ndarray,
    selected_indices: "np.ndarray | None" = None,
) -> "plt.Figure":
    """Build a line chart with one line per scenario over the projection years."""
    figure, chart_axes = plt.subplots(figsize=(10, 5))

    if selected_indices is not None:
        for percentile_index, scenario_index in enumerate(selected_indices):
            scenario_label: str = (
                f"Percentile_{percentile_index * 10}_Scenario_{int(scenario_index) + 1}"
            )
            chart_axes.plot(
                projection_years,
                scenario_cash_flows[scenario_index],
                label=scenario_label,
            )
    else:
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


def figure_to_png_bytes(figure: "plt.Figure") -> bytes:
    """Render a figure to PNG bytes and close it."""
    image_buffer = io.BytesIO()
    figure.savefig(image_buffer, format="png", dpi=100)
    plt.close(figure)
    image_buffer.seek(0)
    return image_buffer.read()


def figure_to_data_url(figure: "plt.Figure") -> str:
    """Render a figure to a browser-displayable PNG data URL."""
    encoded = base64.b64encode(figure_to_png_bytes(figure)).decode("ascii")
    return f"data:image/png;base64,{encoded}"

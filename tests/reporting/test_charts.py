"""Tests for shared reporting chart renderers."""

from __future__ import annotations

from mbc_model.reporting.charts import (
    figure_to_png_bytes,
    make_dashboard_cash_flow_chart,
    make_scenario_cash_flows_chart,
)
from tests.reporting.test_writer import _make_results


def test_scenario_chart_renders_png_bytes() -> None:
    results = _make_results(create_scenario=True, create_scenario_graph=True)

    figure = make_scenario_cash_flows_chart(results)

    assert figure is not None
    image_bytes = figure_to_png_bytes(figure)
    assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(image_bytes) > 1000


def test_dashboard_chart_renders_png_bytes() -> None:
    results = _make_results(create_dashboard=True, create_dashboard_graph=True)

    figure = make_dashboard_cash_flow_chart(results)

    assert figure is not None
    image_bytes = figure_to_png_bytes(figure)
    assert image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(image_bytes) > 1000


def test_disabled_graphs_return_none() -> None:
    results = _make_results(
        create_scenario=True,
        create_dashboard=True,
        create_scenario_graph=False,
        create_dashboard_graph=False,
    )

    assert make_scenario_cash_flows_chart(results) is None
    assert make_dashboard_cash_flow_chart(results) is None

"""Excel loader: reads Interface_Example_v4.xlsm and returns typed Python objects.

Parameters sheet layout (state-machine parser):
    Each logical table starts when column A contains the table name.
    The following rows (col A = None) contain data until the next table marker.

    Markers recognised:
        'Valuation Date'      → scalar date     (col C)
        'Last Projection Year'→ scalar int      (col C)
        'Random Numbers Seed' → scalar int      (col C)
        'Mortality Rates'     → matrix float64  (col C = age, D = Male, E = Female)
        'Projection Scale'    → matrix float64  (col C = age, D = Male, E = Female)
        'Random Numbers'      → matrix float64  (col C = scenario, D+ = policies)

    ┌─────────────────────────────────────────────────────────────────┐
    │ State: SCANNING                                                  │
    │   col A = marker? ─── Yes ──► State: IN_TABLE(marker)          │
    │   No → continue                   data rows (col A = None)      │
    │                                   → accumulate                  │
    │                                   next marker → switch table    │
    │                                   EOF → return tables           │
    └─────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd

from mbc_model.data.models import (
    ModelParameters,
    MortalityTable,
    PolicyRecord,
    ReportingConfig,
)

_MIN_YOB = 1800
_VALID_GENDERS = frozenset({"M", "F"})
_KNOWN_REPORTS = frozenset(
    {"Policy Results", "Scenario Results", "Total Results", "Dashboard Results"}
)


class ExcelLoader:
    """Reads a validated Excel workbook and returns typed model objects.

    Args:
        path: Path to the xlsm input file (read-only; never written to).
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def load_inforce(self) -> list[PolicyRecord]:
        """Read the Inforce sheet and return a validated list of policies.

        Returns:
            Ordered list of PolicyRecord, one per inforce row.

        Raises:
            ValueError: On missing columns, null values, invalid gender, YOB ≤ 1800,
                or non-positive benefit. Error message includes the Excel row number.
        """
        df: pd.DataFrame = pd.read_excel(
            self._path,
            sheet_name="Inforce",
            header=0,
            engine="openpyxl",
        )
        required = {"Policy #", "YOB", "Gender", "Annual Benefit"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Inforce sheet: missing columns {missing}.")

        if df.empty:
            raise ValueError("Inforce sheet: no data rows found.")

        null_mask = df[list(required)].isnull().any(axis=1)
        if null_mask.any():
            row_num = int(null_mask.idxmax()) + 2  # +1 header, +1 zero-index
            raise ValueError(f"Inforce sheet row {row_num}: null value in required column.")

        policies: list[PolicyRecord] = []
        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # type: ignore[arg-type]
            gender = str(row["Gender"]).strip()
            if gender not in _VALID_GENDERS:
                raise ValueError(
                    f"Inforce sheet row {row_num}: Gender must be 'M' or 'F', got {gender!r}."
                )
            yob = int(row["YOB"])
            if yob <= _MIN_YOB:
                raise ValueError(
                    f"Inforce sheet row {row_num}: YOB must be > {_MIN_YOB}, got {yob}."
                )
            benefit = float(row["Annual Benefit"])
            if benefit <= 0.0:
                raise ValueError(
                    f"Inforce sheet row {row_num}: Annual Benefit must be > 0, got {benefit}."
                )
            policies.append(
                PolicyRecord(
                    policy_id=int(row["Policy #"]),
                    yob=yob,
                    gender=gender,  # type: ignore[arg-type]
                    annual_benefit=benefit,
                )
            )
        return policies

    def load_parameters(  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        self,
    ) -> tuple[ModelParameters, MortalityTable, np.ndarray | None]:
        """Read the Parameters sheet.

        Returns:
            (ModelParameters, MortalityTable, random_table)
            random_table: float64 array shape (n_scenarios, n_policies) if the
                Random Numbers table is populated; None otherwise.

        Raises:
            KeyError: If Mortality Rates or Projection Scale table is absent.
        """
        wb = openpyxl.load_workbook(
            self._path, read_only=True, data_only=True, keep_vba=True
        )
        ws = wb["Parameters"]

        scalars: dict[str, Any] = {}
        mortality_rows: list[tuple[float, float]] = []
        improvement_rows: list[tuple[float, float]] = []
        rng_rows: list[list[float]] = []

        idle = "idle"
        mort = "mortality"
        impr = "improvement"
        rand = "random"
        state = idle

        for raw_row in ws.iter_rows(values_only=True):
            row = list(raw_row)
            col_a = row[0] if row else None
            col_c = row[2] if len(row) > 2 else None

            # --- Table name markers -----------------------------------------------
            if col_a is not None and col_a != "Table":
                if col_a == "Valuation Date":
                    val = col_c
                    if isinstance(val, datetime):
                        scalars["valuation_date"] = val.date()
                    elif isinstance(val, date):
                        scalars["valuation_date"] = val
                    state = idle
                elif col_a == "Last Projection Year":
                    scalars["last_projection_year"] = int(col_c)  # type: ignore[arg-type]
                    state = idle
                elif col_a == "Which Random Numbers?":
                    scalars["which_random_numbers"] = str(col_c).strip() if col_c is not None else "Seed"
                    state = idle
                elif col_a == "Random Numbers Seed":
                    scalars["random_seed"] = int(col_c)  # type: ignore[arg-type]
                    state = idle
                elif col_a == "Mortality Rates":
                    state = mort
                elif col_a == "Projection Scale":
                    state = impr
                elif col_a == "Random Numbers":
                    state = rand
                continue

            # --- Data rows within the current table --------------------------------
            if col_a is not None:
                continue  # unexpected non-None col A; skip

            if state == mort:
                col_d = row[3] if len(row) > 3 else None
                col_e = row[4] if len(row) > 4 else None
                if isinstance(col_c, (int, float)) and col_d is not None:
                    mortality_rows.append(
                        (float(col_d), float(col_e) if col_e is not None else 0.0)
                    )
            elif state == impr:
                col_d = row[3] if len(row) > 3 else None
                col_e = row[4] if len(row) > 4 else None
                if isinstance(col_c, (int, float)) and col_d is not None:
                    improvement_rows.append(
                        (float(col_d), float(col_e) if col_e is not None else 0.0)
                    )
            elif state == rand:
                # col D onward holds per-policy random numbers for this scenario.
                # col C holds the scenario index (may be a formula string in
                # non-data_only mode, or an integer in data_only mode).
                policy_values = [float(v) for v in row[3:] if v is not None]
                if policy_values:
                    rng_rows.append(policy_values)

        # --- Validate required tables found ----------------------------------------
        for key in ("valuation_date", "last_projection_year", "random_seed"):
            if key not in scalars:
                raise KeyError(
                    f"Parameters sheet: required scalar '{key}' not found. "
                    "Check that the table marker is present in column A."
                )
        if not mortality_rows:
            raise KeyError(
                "Parameters sheet: 'Mortality Rates' table not found or empty."
            )
        if not improvement_rows:
            raise KeyError(
                "Parameters sheet: 'Projection Scale' table not found or empty."
            )

        params = ModelParameters(
            valuation_date=scalars["valuation_date"],
            last_projection_year=int(scalars["last_projection_year"]),
            random_seed=int(scalars["random_seed"]),
        )
        mortality_table = MortalityTable(
            male_qx=np.array([r[0] for r in mortality_rows], dtype=np.float64),
            female_qx=np.array([r[1] for r in mortality_rows], dtype=np.float64),
            male_improvement=np.array([r[0] for r in improvement_rows], dtype=np.float64),
            female_improvement=np.array([r[1] for r in improvement_rows], dtype=np.float64),
        )
        which_rng = scalars.get("which_random_numbers", "Seed")
        if which_rng.lower() == "table":
            random_table: np.ndarray | None = (
                np.array(rng_rows, dtype=np.float64) if rng_rows else None
            )
        elif which_rng.lower() == "seed":
            random_table = None
        else:
            raise ValueError(
                f"Parameters sheet: 'Which Random Numbers?' must be 'Table' or 'Seed', "
                f"got {which_rng!r}."
            )
        return params, mortality_table, random_table

    def load_reporting(self) -> ReportingConfig:
        """Read the Reporting sheet.

        Returns:
            ReportingConfig with all fields populated. Missing boolean fields
            default to False; missing numeric fields raise ValueError.

        Raises:
            ValueError: If a required numeric field (e.g. Discount Rate) is absent.
        """
        wb = openpyxl.load_workbook(
            self._path, read_only=True, data_only=True, keep_vba=True
        )
        ws = wb["Reporting"]

        data: dict[str, dict[str, Any]] = {}
        current: str | None = None

        for raw_row in ws.iter_rows(values_only=True):
            row = list(raw_row)
            col_a = row[0] if row else None
            col_b = row[1] if len(row) > 1 else None
            col_c = row[2] if len(row) > 2 else None

            if col_a in _KNOWN_REPORTS:
                current = col_a
                data[current] = {}
                if col_b == "Create?":
                    data[current]["Create?"] = col_c
                continue

            if current and col_a is None and col_b is not None:
                data[current][str(col_b)] = col_c

        def _bool(report: str, key: str, default: bool = False) -> bool:
            val = data.get(report, {}).get(key)
            if val is None:
                return default
            return str(val).strip().lower() == "yes"

        def _int(report: str, key: str, default: int | None = None) -> int:
            val = data.get(report, {}).get(key)
            if val is None:
                if default is not None:
                    return default
                raise ValueError(
                    f"Reporting sheet: '{report}' is missing required field '{key}'."
                )
            return int(val)  # type: ignore[arg-type]

        def _float_required(report: str, key: str) -> float:
            val = data.get(report, {}).get(key)
            if val is None:
                raise ValueError(
                    f"Reporting sheet: '{report}' is missing required field '{key}'."
                )
            return float(val)  # type: ignore[arg-type]

        return ReportingConfig(
            create_policy_results=_bool("Policy Results", "Create?"),
            policy_id=_int("Policy Results", "Policy", default=1),
            policy_scenario_id=_int("Policy Results", "Scenario", default=1),
            create_scenario_results=_bool("Scenario Results", "Create?"),
            scenario_id=_int("Scenario Results", "Scenario", default=1),
            create_scenario_graph=_bool("Scenario Results", "Create graph?"),
            create_total_results=_bool("Total Results", "Create?"),
            create_dashboard_results=_bool("Dashboard Results", "Create?"),
            dashboard_scenarios=_int("Dashboard Results", "Scenarios", default=1),
            dashboard_policies=_int("Dashboard Results", "Policies", default=1),
            discount_rate=_float_required("Dashboard Results", "Discount Rate"),
            create_dashboard_graph=_bool("Dashboard Results", "Create graph?"),
        )

"""Tests for ExcelLoader validation error paths.

Uses unittest.mock to inject bad DataFrames without needing real Excel files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from mbc_model.data.loader import ExcelLoader

_DUMMY_PATH = Path("dummy.xlsx")


def _good_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Policy #": [1, 2],
            "YOB": [1951, 1950],
            "Gender": ["M", "F"],
            "Annual Benefit": [20000.0, 98000.0],
        }
    )


# ---------------------------------------------------------------------------
# load_inforce validation
# ---------------------------------------------------------------------------


def test_missing_columns_raises() -> None:
    bad_df = pd.DataFrame({"Policy #": [1], "YOB": [1960]})  # missing Gender, Annual Benefit
    with patch("mbc_model.data.loader.pd.read_excel", return_value=bad_df):
        with pytest.raises(ValueError, match="missing columns"):
            ExcelLoader(_DUMMY_PATH).load_inforce()


def test_empty_inforce_raises() -> None:
    empty_df = pd.DataFrame(columns=["Policy #", "YOB", "Gender", "Annual Benefit"])
    with patch("mbc_model.data.loader.pd.read_excel", return_value=empty_df):
        with pytest.raises(ValueError, match="no data rows"):
            ExcelLoader(_DUMMY_PATH).load_inforce()


def test_null_value_raises() -> None:
    df = _good_df().copy()
    df.loc[0, "YOB"] = None  # inject null
    with patch("mbc_model.data.loader.pd.read_excel", return_value=df):
        with pytest.raises(ValueError, match="null value"):
            ExcelLoader(_DUMMY_PATH).load_inforce()


def test_invalid_gender_raises() -> None:
    df = _good_df().copy()
    df.loc[0, "Gender"] = "X"
    with patch("mbc_model.data.loader.pd.read_excel", return_value=df):
        with pytest.raises(ValueError, match="Gender must be"):
            ExcelLoader(_DUMMY_PATH).load_inforce()


def test_yob_too_old_raises() -> None:
    df = _good_df().copy()
    df.loc[0, "YOB"] = 1799
    with patch("mbc_model.data.loader.pd.read_excel", return_value=df):
        with pytest.raises(ValueError, match="YOB must be"):
            ExcelLoader(_DUMMY_PATH).load_inforce()


def test_non_positive_benefit_raises() -> None:
    df = _good_df().copy()
    df.loc[0, "Annual Benefit"] = -1.0
    with patch("mbc_model.data.loader.pd.read_excel", return_value=df):
        with pytest.raises(ValueError, match="Annual Benefit must be"):
            ExcelLoader(_DUMMY_PATH).load_inforce()

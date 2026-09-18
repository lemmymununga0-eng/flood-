"""
tests/test_validation.py
=========================
Unit tests for the data validation module.

These tests verify that the DataValidator correctly:
- Identifies missing required columns
- Rejects non-DatetimeIndex
- Flags duplicate dates
- Detects physical bound violations
- Passes valid data without errors
"""

import pandas as pd
import numpy as np
import pytest

from src.preprocessing.validation import DataValidator


def make_valid_df(n: int = 100) -> pd.DataFrame:
    """Create a minimal valid weather DataFrame for testing."""
    rng = np.random.default_rng(42)
    date_range = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "prectotcorr": rng.gamma(0.8, 10, n).clip(0, 200),
            "t2m": rng.normal(22, 3, n).clip(5, 38),
            "t2m_max": rng.normal(27, 3, n).clip(10, 42),
            "t2m_min": rng.normal(15, 3, n).clip(2, 30),
            "rh2m": rng.uniform(30, 90, n),
            "ws2m": rng.gamma(2, 2, n).clip(0, 15),
            "gwetroot": rng.uniform(0.1, 0.9, n),
        },
        index=date_range,
    )


class TestDataValidator:
    """Tests for DataValidator."""

    def setup_method(self):
        self.validator = DataValidator()

    def test_valid_dataframe_passes(self):
        df = make_valid_df()
        report = self.validator.validate(df)
        assert report.is_valid, f"Expected valid, got errors: {report.errors}"

    def test_missing_required_column(self):
        df = make_valid_df().drop(columns=["prectotcorr"])
        report = self.validator.validate(df)
        assert not report.is_valid
        assert any("prectotcorr" in e for e in report.errors)

    def test_non_datetime_index_fails(self):
        df = make_valid_df().reset_index(drop=True)
        report = self.validator.validate(df)
        assert not report.is_valid
        assert any("DatetimeIndex" in e for e in report.errors)

    def test_duplicate_dates_fail(self):
        df = make_valid_df()
        df_duped = pd.concat([df.head(10), df.head(10)])
        report = self.validator.validate(df_duped)
        assert not report.is_valid
        assert any("duplicate" in e.lower() for e in report.errors)

    def test_physical_bounds_warning(self):
        df = make_valid_df()
        df.loc[df.index[5], "rh2m"] = 110  # Impossible RH
        report = self.validator.validate(df)
        # Should be a warning (not an error) since it will be clipped
        assert any("rh2m" in w for w in report.warnings)

    def test_stats_computed(self):
        df = make_valid_df()
        report = self.validator.validate(df)
        assert "shape" in report.stats
        assert "date_range" in report.stats
        assert "missing_pct" in report.stats

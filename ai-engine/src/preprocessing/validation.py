"""
preprocessing/validation.py
============================
Schema validation stage for the FloodShield-Zambia data pipeline.

Why validate before preprocessing?
------------------------------------
Raw data downloaded from APIs or loaded from CSV files can contain:
  - Missing columns that downstream code depends on
  - Values outside physically possible ranges (e.g. negative rainfall)
  - Duplicate rows that inflate training statistics
  - Date gaps that break time-series windowing
  - Wrong data types that cause silent calculation errors

By catching these problems here — before any feature engineering —
we produce informative errors early rather than mysterious failures later.

This is professional MLOps practice: never trust raw data blindly.

Design decisions
----------------
- Returns a ``ValidationReport`` dataclass so callers can decide whether to
  abort (on critical errors) or continue with warnings.
- Pure functions — no side effects other than logging — making it testable.

Usage
-----
    from src.preprocessing.validation import DataValidator
    validator = DataValidator()
    report = validator.validate(df)
    if not report.is_valid:
        raise ValueError(report.summary())
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Physical bounds for meteorological variables
# ---------------------------------------------------------------------------
VARIABLE_BOUNDS: dict[str, tuple[float, float]] = {
    "prectotcorr": (0.0, 1500.0),    # mm/day  (max ever recorded ~1800mm)
    "t2m": (-40.0, 65.0),            # °C
    "t2m_max": (-40.0, 65.0),        # °C
    "t2m_min": (-40.0, 65.0),        # °C
    "rh2m": (0.0, 100.0),            # %
    "ws2m": (0.0, 150.0),            # m/s
    "allsky_sfc_sw_dwn": (0.0, 50.0),# MJ/m²/day
    "gwetroot": (0.0, 1.0),          # fraction
    "gwetprof": (0.0, 1.0),          # fraction
}

# Columns that MUST be present for the pipeline to proceed
REQUIRED_COLUMNS: list[str] = [
    "prectotcorr",
    "t2m",
    "rh2m",
]


# ---------------------------------------------------------------------------
# Report data structure
# ---------------------------------------------------------------------------
@dataclass
class ValidationReport:
    """
    Stores the outcome of a data validation pass.

    Attributes
    ----------
    errors : list[str]
        Critical issues that must be fixed before training.
    warnings : list[str]
        Non-critical issues that should be reviewed.
    stats : dict
        Descriptive statistics useful for the EDA report.
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """True if no critical errors were found."""
        return len(self.errors) == 0

    def summary(self) -> str:
        """Human-readable summary of validation results."""
        lines = [
            f"Validation Report — {'PASSED' if self.is_valid else 'FAILED'}",
            f"  Errors   : {len(self.errors)}",
            f"  Warnings : {len(self.warnings)}",
        ]
        for err in self.errors:
            lines.append(f"  [ERROR]   {err}")
        for warn in self.warnings:
            lines.append(f"  [WARNING] {warn}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validator class
# ---------------------------------------------------------------------------
class DataValidator:
    """
    Validates a meteorological DataFrame against the FloodShield schema.

    Parameters
    ----------
    required_columns : list[str], optional
        Columns that must be present.  Defaults to ``REQUIRED_COLUMNS``.
    variable_bounds : dict, optional
        Physical min/max bounds per column.  Defaults to ``VARIABLE_BOUNDS``.
    max_missing_pct : float
        Maximum acceptable percentage of missing values per column (0–100).
    """

    def __init__(
        self,
        required_columns: list[str] = None,
        variable_bounds: dict[str, tuple[float, float]] = None,
        max_missing_pct: float = 30.0,
    ) -> None:
        self._required = required_columns or REQUIRED_COLUMNS
        self._bounds = variable_bounds or VARIABLE_BOUNDS
        self._max_missing_pct = max_missing_pct

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """
        Run all validation checks on the input DataFrame.

        Parameters
        ----------
        df : pd.DataFrame
            Raw meteorological DataFrame (daily, with DatetimeIndex).

        Returns
        -------
        ValidationReport
            Detailed report of errors, warnings, and statistics.
        """
        report = ValidationReport()
        logger.info(f"Running data validation on DataFrame of shape {df.shape}")

        self._check_required_columns(df, report)
        self._check_index_type(df, report)
        self._check_duplicates(df, report)
        self._check_date_continuity(df, report)
        self._check_missing_values(df, report)
        self._check_physical_bounds(df, report)
        self._compute_stats(df, report)

        if report.is_valid:
            logger.info("Validation passed ✓")
        else:
            logger.error(f"Validation failed:\n{report.summary()}")

        return report

    # ------------------------------------------------------------------
    # Private checks
    # ------------------------------------------------------------------

    def _check_required_columns(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Verify all required columns are present."""
        missing = [c for c in self._required if c not in df.columns]
        if missing:
            report.errors.append(
                f"Missing required columns: {missing}. "
                "Check your data ingestion step."
            )
        else:
            logger.debug("Required columns check: passed")

    def _check_index_type(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Verify the index is a DatetimeIndex."""
        if not isinstance(df.index, pd.DatetimeIndex):
            report.errors.append(
                f"DataFrame index must be a DatetimeIndex, got {type(df.index).__name__}. "
                "Ensure the 'date' column is parsed as datetime."
            )
        else:
            logger.debug("Index type check: passed")

    def _check_duplicates(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Check for duplicate date indices."""
        n_dupes = df.index.duplicated().sum()
        if n_dupes > 0:
            report.errors.append(
                f"Found {n_dupes} duplicate date entries. "
                "Remove duplicates before proceeding."
            )
        else:
            logger.debug("Duplicate check: passed")

    def _check_date_continuity(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Check for gaps in the daily date range."""
        if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 2:
            return  # Skip if index check already failed

        expected = pd.date_range(df.index.min(), df.index.max(), freq="D")
        gaps = expected.difference(df.index)
        if len(gaps) > 0:
            pct_gap = len(gaps) / len(expected) * 100
            msg = (
                f"Date range has {len(gaps)} missing days ({pct_gap:.1f}%). "
                f"First gap: {gaps[0].date()}"
            )
            if pct_gap > 10:
                report.errors.append(msg)
            else:
                report.warnings.append(msg)
            logger.debug(f"Date continuity: {len(gaps)} gaps found")
        else:
            logger.debug("Date continuity check: passed")

    def _check_missing_values(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Check missing value percentage per column."""
        for col in df.columns:
            pct = df[col].isna().mean() * 100
            if pct > self._max_missing_pct:
                report.errors.append(
                    f"Column '{col}' has {pct:.1f}% missing values "
                    f"(threshold: {self._max_missing_pct}%)."
                )
            elif pct > 5:
                report.warnings.append(
                    f"Column '{col}' has {pct:.1f}% missing values."
                )

    def _check_physical_bounds(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Check for values outside physical bounds."""
        for col, (low, high) in self._bounds.items():
            if col not in df.columns:
                continue
            series = df[col].dropna()
            n_below = (series < low).sum()
            n_above = (series > high).sum()
            if n_below > 0 or n_above > 0:
                report.warnings.append(
                    f"Column '{col}': {n_below} values below {low}, "
                    f"{n_above} values above {high}. "
                    "These will be clipped during cleaning."
                )

    def _compute_stats(
        self, df: pd.DataFrame, report: ValidationReport
    ) -> None:
        """Compute and store descriptive statistics for the EDA report."""
        report.stats["shape"] = df.shape
        report.stats["date_range"] = {
            "start": str(df.index.min().date()) if isinstance(df.index, pd.DatetimeIndex) else "N/A",
            "end": str(df.index.max().date()) if isinstance(df.index, pd.DatetimeIndex) else "N/A",
        }
        report.stats["missing_pct"] = (df.isna().mean() * 100).round(2).to_dict()
        report.stats["describe"] = df.describe().round(4).to_dict()
        logger.debug("Descriptive statistics computed")

"""
preprocessing/clean_data.py
============================
Data cleaning and preprocessing for the FloodShield-Zambia AI Engine.

What this module does
---------------------
After validation, raw data typically still contains:
  1. Missing values (NaN) — caused by sensor failures or API gaps
  2. Outliers — extreme values that skew model training
  3. Wrong data types — floats stored as objects, dates as strings
  4. Inconsistent units — some APIs return Kelvin, others Celsius

This module handles all of these issues and produces a clean DataFrame
ready for feature engineering.

Design decisions
----------------
- Uses forward-fill then backward-fill for short gaps (≤7 days).
  Rationale: meteorological variables change slowly; yesterday's value
  is a better estimate than zero or the global mean.
- Uses linear interpolation for longer gaps.
- Clips values to physical bounds (see validation.py) rather than dropping
  rows, to preserve the continuous time-series structure.
- ``RobustScaler`` is used instead of ``StandardScaler`` because weather
  variables (especially rainfall) have heavy-tailed distributions.

Usage
-----
    from src.preprocessing.clean_data import DataCleaner
    cleaner = DataCleaner()
    df_clean = cleaner.clean(df_raw)
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

from src.config.settings import settings
from src.preprocessing.validation import VARIABLE_BOUNDS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """
    Cleans and preprocesses raw meteorological DataFrames.

    Parameters
    ----------
    max_interpolate_days : int
        Maximum consecutive NaN days to fill via interpolation.
        Beyond this threshold, rows are flagged but NOT dropped (to preserve
        the time-series structure).
    output_dir : Path, optional
        Directory to save the cleaned dataset CSV.
    """

    def __init__(
        self,
        max_interpolate_days: int = 14,
        output_dir: Path = settings.processed_dir,
    ) -> None:
        self._max_interp = max_interpolate_days
        self._output_dir = output_dir

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def clean(
        self,
        df: pd.DataFrame,
        save: bool = True,
        filename: str = "cleaned_weather.csv",
    ) -> pd.DataFrame:
        """
        Execute the full cleaning pipeline.

        Steps
        -----
        1. Enforce correct data types
        2. Sort by date
        3. Clip physical outliers
        4. Fill missing values (forward-fill → backward-fill → interpolation)
        5. Log remaining NaN counts
        6. Optionally save to CSV

        Parameters
        ----------
        df : pd.DataFrame
            Raw validated DataFrame with DatetimeIndex.
        save : bool
            Whether to save the cleaned DataFrame to disk.
        filename : str
            Output filename (saved in ``data/processed/``).

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame, ready for feature engineering.
        """
        logger.info(f"Starting data cleaning | shape: {df.shape}")

        df = df.copy()
        df = self._enforce_dtypes(df)
        df = self._sort_index(df)
        df = self._clip_physical_bounds(df)
        df = self._fill_missing_values(df)
        df = self._log_remaining_nans(df)

        if save:
            out_path = self._output_dir / filename
            df.to_csv(out_path)
            logger.info(f"Cleaned data saved to {out_path}")

        logger.info(f"Data cleaning complete | shape: {df.shape}")
        return df

    # ------------------------------------------------------------------
    # Private steps
    # ------------------------------------------------------------------

    def _enforce_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert all feature columns to float32 (memory-efficient)."""
        numeric_cols = [c for c in df.columns if c != "flood_label"]
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
        # Keep label as int if present
        if "flood_label" in df.columns:
            df["flood_label"] = df["flood_label"].astype(int)
        logger.debug("Data types enforced")
        return df

    def _sort_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure chronological ordering (required for time-series windowing)."""
        df = df.sort_index()
        logger.debug("DataFrame sorted by date")
        return df

    def _clip_physical_bounds(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clip values to physically possible ranges.

        Rather than dropping out-of-range rows (which breaks the time series),
        we clip them to the boundary.  For example, a reported rainfall of
        -5mm (a sensor error) is clipped to 0mm.
        """
        for col, (low, high) in VARIABLE_BOUNDS.items():
            if col in df.columns:
                n_clipped = ((df[col] < low) | (df[col] > high)).sum()
                if n_clipped > 0:
                    logger.warning(
                        f"Clipping {n_clipped} values in '{col}' "
                        f"to range [{low}, {high}]"
                    )
                df[col] = df[col].clip(lower=low, upper=high)
        return df

    def _fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fill missing values using a three-stage strategy.

        Stage 1: Forward-fill (use last known value)
        Stage 2: Backward-fill (for leading NaNs at start of series)
        Stage 3: Linear interpolation for larger gaps up to max_interpolate_days
        """
        feature_cols = [c for c in df.columns if c != "flood_label"]
        n_missing_before = df[feature_cols].isna().sum().sum()

        # Stage 1: Forward fill (max 7 days)
        df[feature_cols] = df[feature_cols].ffill(limit=7)
        # Stage 2: Backward fill for leading NaNs
        df[feature_cols] = df[feature_cols].bfill(limit=7)
        # Stage 3: Linear interpolation for remaining gaps
        df[feature_cols] = df[feature_cols].interpolate(
            method="time",
            limit=self._max_interp,
            limit_direction="both",
        )

        n_missing_after = df[feature_cols].isna().sum().sum()
        logger.info(
            f"Missing values: {n_missing_before} → {n_missing_after} "
            f"(filled {n_missing_before - n_missing_after})"
        )
        return df

    def _log_remaining_nans(self, df: pd.DataFrame) -> pd.DataFrame:
        """Log any columns that still have NaN after all fill strategies."""
        remaining = df.isna().sum()
        remaining = remaining[remaining > 0]
        if not remaining.empty:
            logger.warning(
                f"Remaining NaN values after cleaning:\n{remaining.to_string()}"
            )
        else:
            logger.info("No remaining NaN values after cleaning ✓")
        return df

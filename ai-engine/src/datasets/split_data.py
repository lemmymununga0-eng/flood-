"""
datasets/split_data.py
=======================
Train / Validation / Test splitting for the FloodShield-Zambia AI Engine.

Why time-based splitting?
--------------------------
For time-series data, random shuffling before splitting is WRONG.

If we randomly split the data, we risk "data leakage": the model might see
future data (e.g. flood patterns from December 2022) during training, then
be evaluated on past data (e.g. January 2020).  This produces misleadingly
high evaluation scores on data the model has already seen in a different form.

The correct approach is a strict chronological split:
  - Train : oldest 70% of the data
  - Validation : next 15% (used for hyperparameter tuning)
  - Test  : most recent 15% (held out completely until final evaluation)

This mimics real-world deployment where we train on the past and predict
the future.

Usage
-----
    from src.datasets.split_data import DataSplitter
    splitter = DataSplitter()
    splits = splitter.split(df_features)
    X_train, y_train = splits["train"]
    X_val,   y_val   = splits["val"]
    X_test,  y_test  = splits["test"]
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DataSplits:
    """
    Container for all train/val/test splits.

    Flat splits (for baseline models) — 2D arrays:
        X_train, X_val, X_test  shape: (n_samples, n_features)
        y_train, y_val, y_test  shape: (n_samples,)

    Sequential splits (for LSTM) — 3D arrays:
        X_seq_train, X_seq_val, X_seq_test  shape: (n_samples, window, n_features)
        y_seq_train, y_seq_val, y_seq_test  shape: (n_samples,)

    Date indices (for plotting):
        dates_train, dates_val, dates_test
    """

    # Flat splits
    X_train: np.ndarray
    X_val: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    y_val: np.ndarray
    y_test: np.ndarray

    # Sequential splits (set after create_sequences)
    X_seq_train: Optional[np.ndarray] = None
    X_seq_val: Optional[np.ndarray] = None
    X_seq_test: Optional[np.ndarray] = None
    y_seq_train: Optional[np.ndarray] = None
    y_seq_val: Optional[np.ndarray] = None
    y_seq_test: Optional[np.ndarray] = None

    # Date ranges
    dates_train: Optional[pd.DatetimeIndex] = None
    dates_val: Optional[pd.DatetimeIndex] = None
    dates_test: Optional[pd.DatetimeIndex] = None

    # Feature column names (saved for model metadata)
    feature_columns: Optional[list[str]] = None


class DataSplitter:
    """
    Performs chronological train/validation/test splitting.

    Parameters
    ----------
    test_size : float
        Fraction of data for the test set (e.g. 0.15 = 15%).
    val_size : float
        Fraction of data for the validation set.
    target_col : str
        Name of the target (label) column.
    """

    def __init__(
        self,
        test_size: float = settings.training.test_size,
        val_size: float = settings.training.validation_size,
        target_col: str = "flood_label",
    ) -> None:
        self.test_size = test_size
        self.val_size = val_size
        self.target_col = target_col

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def split(self, df: pd.DataFrame) -> DataSplits:
        """
        Split a feature DataFrame into train/val/test sets chronologically.

        Parameters
        ----------
        df : pd.DataFrame
            Feature-engineered DataFrame with DatetimeIndex and label column.

        Returns
        -------
        DataSplits
            Dataclass containing all split arrays and date indices.
        """
        n = len(df)
        n_test = int(n * self.test_size)
        n_val = int(n * self.val_size)
        n_train = n - n_val - n_test

        feature_cols = [c for c in df.columns if c != self.target_col]
        X = df[feature_cols].values.astype(np.float32)
        y = df[self.target_col].values.astype(np.int32)

        X_train = X[:n_train]
        X_val = X[n_train : n_train + n_val]
        X_test = X[n_train + n_val :]

        y_train = y[:n_train]
        y_val = y[n_train : n_train + n_val]
        y_test = y[n_train + n_val :]

        dates_train = df.index[:n_train]
        dates_val = df.index[n_train : n_train + n_val]
        dates_test = df.index[n_train + n_val :]

        self._log_split_info(y_train, y_val, y_test, dates_train, dates_val, dates_test)

        return DataSplits(
            X_train=X_train,
            X_val=X_val,
            X_test=X_test,
            y_train=y_train,
            y_val=y_val,
            y_test=y_test,
            dates_train=dates_train,
            dates_val=dates_val,
            dates_test=dates_test,
            feature_columns=feature_cols,
        )

    def split_sequences(
        self,
        X: np.ndarray,
        y: np.ndarray,
        dates: pd.DatetimeIndex,
    ) -> DataSplits:
        """
        Split pre-built LSTM sequence arrays chronologically.

        Parameters
        ----------
        X : np.ndarray
            3D array of shape (samples, window, features).
        y : np.ndarray
            1D label array of shape (samples,).
        dates : pd.DatetimeIndex
            Corresponding dates for each sample.

        Returns
        -------
        DataSplits
            DataSplits with sequential fields populated.
        """
        n = len(X)
        n_test = int(n * self.test_size)
        n_val = int(n * self.val_size)
        n_train = n - n_val - n_test

        splits = DataSplits(
            X_train=X[:n_train, -1, :],  # last timestep for flat baseline compat
            X_val=X[n_train : n_train + n_val, -1, :],
            X_test=X[n_train + n_val :, -1, :],
            y_train=y[:n_train],
            y_val=y[n_train : n_train + n_val],
            y_test=y[n_train + n_val :],
            X_seq_train=X[:n_train],
            X_seq_val=X[n_train : n_train + n_val],
            X_seq_test=X[n_train + n_val :],
            y_seq_train=y[:n_train],
            y_seq_val=y[n_train : n_train + n_val],
            y_seq_test=y[n_train + n_val :],
            dates_train=dates[:n_train] if dates is not None else None,
            dates_val=dates[n_train : n_train + n_val] if dates is not None else None,
            dates_test=dates[n_train + n_val :] if dates is not None else None,
        )

        logger.info(
            f"Sequence splits | train: {splits.X_seq_train.shape}, "
            f"val: {splits.X_seq_val.shape}, test: {splits.X_seq_test.shape}"
        )
        return splits

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _log_split_info(
        self,
        y_train: np.ndarray,
        y_val: np.ndarray,
        y_test: np.ndarray,
        dates_train: pd.DatetimeIndex,
        dates_val: pd.DatetimeIndex,
        dates_test: pd.DatetimeIndex,
    ) -> None:
        """Log split sizes, date ranges, and class balance."""
        for name, y, dates in [
            ("Train", y_train, dates_train),
            ("Val  ", y_val, dates_val),
            ("Test ", y_test, dates_test),
        ]:
            pos_rate = y.mean() if len(y) > 0 else 0.0
            date_str = (
                f"{dates.min().date()} → {dates.max().date()}"
                if dates is not None and len(dates) > 0
                else "N/A"
            )
            logger.info(
                f"{name} | n={len(y):6d} | flood rate={pos_rate:.1%} | {date_str}"
            )

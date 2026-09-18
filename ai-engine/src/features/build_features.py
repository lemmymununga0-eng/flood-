"""
features/build_features.py
============================
Feature engineering for the FloodShield-Zambia AI Engine.

Why feature engineering matters
---------------------------------
Raw meteorological variables (temperature, humidity, rainfall) do not fully
capture the conditions that lead to flooding.  Feature engineering creates
new, more informative variables by combining or transforming the raw ones.

Features we create
-------------------
1. **Rolling statistics** — mean/sum/max over 3, 7, 14, 30-day windows
   Why? A single day of heavy rain is less dangerous than 7 consecutive
   days.  Rolling sums capture cumulative soil saturation.

2. **Lag features** — value 1, 2, 3, 7, 14 days ago
   Why? The LSTM needs to see past patterns; lag features also help the
   baseline (non-sequential) models capture temporal dependencies.

3. **Temporal indicators** — month, day-of-year, season, sine/cosine encoding
   Why? Flooding in Zambia is highly seasonal (November–April rainy season).
   Sine/cosine encoding captures cyclical relationships without arbitrary
   ordinal encoding.

4. **Proxy flood label (SPI-based)** — created when real labels are absent
   Why? We need a target variable to train.  The Standardised Precipitation
   Index (SPI) is a widely-used hydrological measure of rainfall anomaly.

5. **Soil saturation index** — combined soil moisture proxy
   Why? Saturated soil cannot absorb more water; even moderate rain on
   saturated soil causes flooding.

Design decisions
----------------
- All features are computed in-memory on the clean DataFrame.
- The final feature list is logged so it can be saved alongside the model
  for reproducibility.
- Time-series windowing (for LSTM) is handled here too, returning 3D arrays
  (samples, timesteps, features).

Usage
-----
    from src.features.build_features import FeatureEngineer
    fe = FeatureEngineer()
    df_features = fe.build(df_clean)
    X_seq, y_seq = fe.create_sequences(df_features, target_col="flood_label")
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
import joblib

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """
    Builds model-ready features from a cleaned meteorological DataFrame.

    Parameters
    ----------
    window_size : int
        Number of past time steps used to predict the next step (LSTM window).
    rolling_windows : tuple of int
        Rolling window sizes for computing statistics.
    lag_periods : tuple of int
        Lag periods (in days) for lag feature creation.
    scaler_path : Path, optional
        Path to save/load the fitted RobustScaler.
    """

    def __init__(
        self,
        window_size: int = settings.features.window_size,
        rolling_windows: tuple = settings.features.rolling_windows,
        lag_periods: tuple = settings.features.lag_periods,
        scaler_path: Path = settings.saved_models_dir / "scaler.joblib",
    ) -> None:
        self.window_size = window_size
        self.rolling_windows = rolling_windows
        self.lag_periods = lag_periods
        self.scaler_path = scaler_path
        self._scaler: Optional[RobustScaler] = None
        self._feature_columns: list[str] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build(
        self,
        df: pd.DataFrame,
        has_labels: bool = True,
        save: bool = True,
        filename: str = "features.csv",
    ) -> pd.DataFrame:
        """
        Execute the full feature engineering pipeline.

        Parameters
        ----------
        df : pd.DataFrame
            Cleaned weather DataFrame with DatetimeIndex.
        has_labels : bool
            Whether a 'flood_label' column is present (True during training).
        save : bool
            Whether to save the feature DataFrame to ``data/processed/``.
        filename : str
            Output CSV filename.

        Returns
        -------
        pd.DataFrame
            DataFrame with all engineered features plus the label column.
        """
        logger.info("Starting feature engineering ...")
        df = df.copy()

        df = self._add_rolling_features(df)
        df = self._add_lag_features(df)
        df = self._add_temporal_features(df)
        df = self._add_soil_saturation_index(df)

        if not has_labels or "flood_label" not in df.columns:
            df = self._add_proxy_labels(df)

        # Drop rows with NaN created by lag/rolling at the start of the series
        n_before = len(df)
        df = df.dropna()
        logger.info(
            f"Dropped {n_before - len(df)} rows with NaN after feature engineering "
            f"(expected due to rolling/lag windows)"
        )

        # Record feature columns (exclude the label)
        self._feature_columns = [c for c in df.columns if c != "flood_label"]
        logger.info(
            f"Feature engineering complete | "
            f"{len(self._feature_columns)} features | {len(df)} rows"
        )

        if save:
            out_path = settings.processed_dir / filename
            df.to_csv(out_path)
            logger.info(f"Feature dataset saved to {out_path}")

        return df

    def scale_features(
        self,
        df: pd.DataFrame,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Scale numerical features using RobustScaler.

        RobustScaler uses the median and IQR instead of mean/std, making it
        robust to the extreme rainfall values common in flood datasets.

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with feature columns (and optionally 'flood_label').
        fit : bool
            If True, fit the scaler on this data and save it.
            If False, load a previously fitted scaler (for inference).

        Returns
        -------
        pd.DataFrame
            DataFrame with scaled feature columns.  The label column is
            left unchanged.
        """
        feature_cols = [c for c in df.columns if c != "flood_label"]
        df_scaled = df.copy()

        if fit:
            self._scaler = RobustScaler()
            df_scaled[feature_cols] = self._scaler.fit_transform(df[feature_cols])
            joblib.dump(self._scaler, self.scaler_path)
            logger.info(f"Scaler fitted and saved to {self.scaler_path}")
        else:
            if self._scaler is None:
                self._scaler = joblib.load(self.scaler_path)
                logger.info(f"Scaler loaded from {self.scaler_path}")
            df_scaled[feature_cols] = self._scaler.transform(df[feature_cols])

        return df_scaled

    def create_sequences(
        self,
        df: pd.DataFrame,
        target_col: str = "flood_label",
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Convert a flat DataFrame into 3D sequences for LSTM input.

        The LSTM model expects input of shape:
            (num_samples, window_size, num_features)

        For each time step t, the input is the window of ``window_size``
        days ending at t-1, and the target is the label at day t.

        Parameters
        ----------
        df : pd.DataFrame
            Feature-engineered and scaled DataFrame.
        target_col : str
            Name of the target (label) column.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            X of shape (samples, window_size, features) and y of shape (samples,).
        """
        feature_cols = [c for c in df.columns if c != target_col]
        X_data = df[feature_cols].values
        y_data = df[target_col].values

        X_seqs, y_seqs = [], []
        for i in range(self.window_size, len(df)):
            X_seqs.append(X_data[i - self.window_size : i])
            y_seqs.append(y_data[i])

        X = np.array(X_seqs, dtype=np.float32)
        y = np.array(y_seqs, dtype=np.int32)

        logger.info(
            f"Sequences created | X: {X.shape}, y: {y.shape} | "
            f"window={self.window_size}"
        )
        return X, y

    @property
    def feature_columns(self) -> list[str]:
        """Return the list of feature column names (set after ``build()``)."""
        return self._feature_columns

    # ------------------------------------------------------------------
    # Private feature builders
    # ------------------------------------------------------------------

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute rolling mean, sum, and max for key weather variables.

        Rainfall accumulation over multiple days is one of the strongest
        predictors of flooding.  A 7-day rolling sum captures the slow
        process of soil saturation that precedes flash floods.
        """
        rain_col = "prectotcorr"
        rh_col = "rh2m"

        for w in self.rolling_windows:
            if rain_col in df.columns:
                df[f"rain_rolling_sum_{w}d"] = (
                    df[rain_col].rolling(w, min_periods=1).sum()
                )
                df[f"rain_rolling_mean_{w}d"] = (
                    df[rain_col].rolling(w, min_periods=1).mean()
                )
                df[f"rain_rolling_max_{w}d"] = (
                    df[rain_col].rolling(w, min_periods=1).max()
                )
            if rh_col in df.columns:
                df[f"rh_rolling_mean_{w}d"] = (
                    df[rh_col].rolling(w, min_periods=1).mean()
                )

        logger.debug(f"Rolling features added for windows: {self.rolling_windows}")
        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add lagged values for key predictors.

        Lag features allow non-sequential models (Random Forest, etc.) to
        access temporal information without requiring 3D inputs.
        """
        lag_cols = [c for c in ["prectotcorr", "t2m", "rh2m", "gwetroot"] if c in df.columns]
        for col in lag_cols:
            for lag in self.lag_periods:
                df[f"{col}_lag{lag}d"] = df[col].shift(lag)

        logger.debug(f"Lag features added: {lag_cols}, lags: {self.lag_periods}")
        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract temporal features from the DatetimeIndex.

        Sine/cosine encoding of month and day-of-year converts the cyclical
        calendar into continuous variables that a model can interpolate across
        year boundaries (e.g. Dec and Jan are neighbours, not strangers).
        """
        df["month"] = df.index.month.astype(np.float32)
        df["day_of_year"] = df.index.day_of_year.astype(np.float32)
        df["year"] = df.index.year.astype(np.float32)

        # Sine/cosine encoding for cyclic variables
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
        df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

        # Binary rainy season flag: November (11) to April (4)
        df["is_rainy_season"] = df["month"].apply(
            lambda m: 1 if m >= 11 or m <= 4 else 0
        ).astype(np.float32)

        logger.debug("Temporal features added")
        return df

    def _add_soil_saturation_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create a composite soil saturation index from soil moisture variables.

        When both root-zone and profile soil moisture are near 1.0 (fully
        saturated), even moderate rainfall causes runoff and flooding.
        """
        if "gwetroot" in df.columns and "gwetprof" in df.columns:
            df["soil_saturation_index"] = (
                0.6 * df["gwetroot"] + 0.4 * df["gwetprof"]
            )
        elif "gwetroot" in df.columns:
            df["soil_saturation_index"] = df["gwetroot"]
        else:
            df["soil_saturation_index"] = np.nan

        logger.debug("Soil saturation index added")
        return df

    def _add_proxy_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create proxy flood labels when real historical events are unavailable.

        Method
        ------
        A day is labelled as a flood risk day (1) if ANY of the following
        conditions are met:
        - 3-day cumulative rainfall > 50mm
        - 7-day cumulative rainfall > 80mm
        - Soil saturation index > 0.85 AND daily rainfall > 20mm

        These thresholds are based on Zambia Meteorological Department (ZMD)
        guidelines and published hydrological studies for sub-Saharan Africa.

        IMPORTANT: Proxy labels must be clearly documented in your
        dissertation.  State that they are approximations and that model
        performance is limited by label quality.
        """
        cfg = settings.labels
        labels = pd.Series(0, index=df.index, name="flood_label", dtype=int)

        if "rain_rolling_sum_3d" in df.columns:
            labels[df["rain_rolling_sum_3d"] >= cfg.rainfall_3day_threshold_mm] = 1

        if "rain_rolling_sum_7d" in df.columns:
            labels[df["rain_rolling_sum_7d"] >= cfg.rainfall_7day_threshold_mm] = 1

        if "soil_saturation_index" in df.columns and "prectotcorr" in df.columns:
            labels[
                (df["soil_saturation_index"] > 0.85) & (df["prectotcorr"] > 20)
            ] = 1

        df["flood_label"] = labels
        positive_rate = labels.mean()
        logger.warning(
            f"Using PROXY flood labels (no real events file found). "
            f"Flood days: {labels.sum()} ({positive_rate:.1%} of dataset). "
            f"Document this assumption in your dissertation."
        )
        return df

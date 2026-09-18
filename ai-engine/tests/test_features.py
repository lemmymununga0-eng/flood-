"""
tests/test_features.py
========================
Unit tests for the feature engineering module.
"""

import numpy as np
import pandas as pd
import pytest

from src.features.build_features import FeatureEngineer


def make_clean_df(n: int = 200) -> pd.DataFrame:
    """Create a minimal clean weather DataFrame for feature engineering tests."""
    rng = np.random.default_rng(42)
    date_range = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "prectotcorr": rng.gamma(0.8, 10, n).clip(0, 150),
            "t2m": rng.normal(22, 3, n).clip(5, 38),
            "t2m_max": rng.normal(27, 3, n).clip(10, 42),
            "t2m_min": rng.normal(15, 3, n).clip(2, 30),
            "rh2m": rng.uniform(30, 90, n),
            "ws2m": rng.gamma(2, 2, n).clip(0, 15),
            "gwetroot": rng.uniform(0.1, 0.9, n),
            "gwetprof": rng.uniform(0.1, 0.9, n),
            "allsky_sfc_sw_dwn": rng.uniform(10, 30, n),
        },
        index=date_range,
    )


class TestFeatureEngineer:
    """Tests for FeatureEngineer."""

    def setup_method(self):
        self.fe = FeatureEngineer(window_size=7)

    def test_build_produces_features(self):
        df = make_clean_df()
        result = self.fe.build(df, has_labels=False, save=False)
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) > 9  # More features than raw columns

    def test_proxy_labels_created(self):
        df = make_clean_df()
        result = self.fe.build(df, has_labels=False, save=False)
        assert "flood_label" in result.columns
        assert result["flood_label"].isin([0, 1]).all()

    def test_temporal_features_present(self):
        df = make_clean_df()
        result = self.fe.build(df, has_labels=False, save=False)
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns
        assert "is_rainy_season" in result.columns

    def test_rolling_features_present(self):
        df = make_clean_df()
        result = self.fe.build(df, has_labels=False, save=False)
        assert "rain_rolling_sum_7d" in result.columns
        assert "rain_rolling_mean_3d" in result.columns

    def test_create_sequences_shape(self):
        df = make_clean_df()
        result = self.fe.build(df, has_labels=False, save=False)
        X, y = self.fe.create_sequences(result)
        n_seq = len(result) - self.fe.window_size
        n_feat = len(self.fe.feature_columns)
        assert X.shape == (n_seq, self.fe.window_size, n_feat)
        assert y.shape == (n_seq,)

    def test_no_nan_after_build(self):
        df = make_clean_df()
        # Add some NaN to test cleaning
        df.loc[df.index[50:55], "prectotcorr"] = np.nan
        result = self.fe.build(df, has_labels=False, save=False)
        assert not result.isna().any().any(), "NaN values found after build"

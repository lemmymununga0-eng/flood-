"""
tests/test_synthetic_generator.py
====================================
Unit tests for the synthetic data generator.
"""

import numpy as np
import pandas as pd

from src.ingestion.synthetic_data_generator import SyntheticDataGenerator


class TestSyntheticDataGenerator:
    """Tests for synthetic data generation."""

    def setup_method(self):
        self.gen = SyntheticDataGenerator(seed=42)

    def test_generates_correct_shape(self):
        df = self.gen.generate(start_year=2000, end_year=2005, save=False)
        # 6 years × 365 days ≈ 2191 rows (includes leap years)
        assert 2150 < len(df) < 2250
        assert len(df.columns) == 9  # 9 meteorological variables

    def test_rainfall_non_negative(self):
        df = self.gen.generate(start_year=2000, end_year=2002, save=False)
        non_nan_rain = df["prectotcorr"].dropna()
        assert (non_nan_rain >= 0).all()

    def test_humidity_in_range(self):
        df = self.gen.generate(start_year=2000, end_year=2002, save=False)
        rh = df["rh2m"].dropna()
        assert (rh >= 0).all() and (rh <= 100).all()

    def test_has_datetime_index(self):
        df = self.gen.generate(start_year=2000, end_year=2001, save=False)
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_reproducibility_with_same_seed(self):
        gen1 = SyntheticDataGenerator(seed=99)
        gen2 = SyntheticDataGenerator(seed=99)
        df1 = gen1.generate(start_year=2000, end_year=2001, save=False)
        df2 = gen2.generate(start_year=2000, end_year=2001, save=False)
        assert (df1["prectotcorr"].dropna().values == df2["prectotcorr"].dropna().values).all()

    def test_different_seeds_differ(self):
        gen1 = SyntheticDataGenerator(seed=1)
        gen2 = SyntheticDataGenerator(seed=2)
        df1 = gen1.generate(start_year=2000, end_year=2001, save=False)
        df2 = gen2.generate(start_year=2000, end_year=2001, save=False)
        assert not df1.equals(df2)

    def test_contains_some_rain(self):
        df = self.gen.generate(start_year=2000, end_year=2005, save=False)
        assert df["prectotcorr"].dropna().sum() > 0

    def test_soil_moisture_fraction(self):
        df = self.gen.generate(start_year=2000, end_year=2002, save=False)
        soil = df["gwetroot"].dropna()
        assert (soil >= 0).all() and (soil <= 1).all()

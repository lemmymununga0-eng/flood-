"""
ingestion/synthetic_data_generator.py
======================================
Generates realistic synthetic meteorological data for Zambia.

Purpose
-------
This module exists for TWO reasons:

1. **Development & Testing**: When NASA POWER or other external APIs are
   unavailable (e.g. no internet connection), this module generates
   realistic synthetic data so the entire pipeline can be tested end-to-end.

2. **Demonstrating the Pipeline**: For presentations and marking, the project
   must produce output even without a live internet connection.

IMPORTANT ACADEMIC NOTE
-----------------------
This data is NOT used for the final trained model.  The dissertation clearly
states when real API data is used versus synthetic demo data.  All synthetic
data is clearly labelled in filenames (``synthetic_`` prefix).

How the synthetic data is generated
-------------------------------------
- Zambia's climate is modelled with:
  - Strong seasonality: wet season Nov–Apr, dry season May–Oct
  - Inter-annual variability (±15% around mean)
  - Realistic correlations: rainfall ↑ → humidity ↑, soil moisture ↑
  - Random flood events (probability higher in rainy season)
  - Occasional extreme events (El Niño/La Niña patterns)

Usage
-----
    from src.ingestion.synthetic_data_generator import SyntheticDataGenerator
    gen = SyntheticDataGenerator(seed=42)
    df = gen.generate(start_year=2000, end_year=2023)
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SyntheticDataGenerator:
    """
    Generates realistic synthetic daily meteorological data for Zambia.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility.
    output_dir : Path
        Directory to save the generated CSV.
    """

    def __init__(
        self,
        seed: int = settings.training.random_seed,
        output_dir: Path = settings.raw_dir,
    ) -> None:
        self._seed = seed
        self._output_dir = output_dir
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        start_year: int = 2000,
        end_year: int = 2023,
        latitude: float = -15.4167,
        longitude: float = 28.2833,
        save: bool = True,
        filename: str = "synthetic_zambia_weather.csv",
    ) -> pd.DataFrame:
        """
        Generate a daily weather DataFrame for the specified date range.

        Parameters
        ----------
        start_year : int
        end_year : int
        latitude : float
        longitude : float
        save : bool
        filename : str

        Returns
        -------
        pd.DataFrame
            DataFrame with DatetimeIndex and realistic meteorological columns.
        """
        logger.info(
            f"Generating synthetic data: {start_year}–{end_year} | "
            f"lat={latitude}, lon={longitude}"
        )

        date_range = pd.date_range(
            start=f"{start_year}-01-01",
            end=f"{end_year}-12-31",
            freq="D",
        )
        n = len(date_range)
        doy = np.array([d.timetuple().tm_yday for d in date_range])
        month = np.array([d.month for d in date_range])
        year = np.array([d.year for d in date_range])

        # ------------------------------------------------------------------
        # Seasonal signal (Zambia rainy season: Nov–Apr)
        # Phase shift so that peak is in January (doy ~15)
        # ------------------------------------------------------------------
        season = np.cos(2 * np.pi * (doy - 15) / 365)  # +1 = rainy, -1 = dry

        rainfall = self._generate_rainfall(season, n, year)
        temperature = self._generate_temperature(season, n)
        humidity = self._generate_humidity(season, rainfall, n)
        wind_speed = self._generate_wind_speed(season, n)
        soil_root = self._generate_soil_moisture(rainfall, n)
        soil_prof = self._generate_soil_moisture(rainfall, n, lag=7)
        solar_rad = self._generate_solar_radiation(season, n)

        df = pd.DataFrame(
            {
                "prectotcorr": np.round(rainfall, 2),
                "t2m": np.round(temperature, 2),
                "t2m_max": np.round(temperature + self._rng.uniform(2, 5, n), 2),
                "t2m_min": np.round(temperature - self._rng.uniform(2, 5, n), 2),
                "rh2m": np.round(humidity, 2),
                "ws2m": np.round(wind_speed, 2),
                "allsky_sfc_sw_dwn": np.round(solar_rad, 2),
                "gwetroot": np.round(np.clip(soil_root, 0, 1), 3),
                "gwetprof": np.round(np.clip(soil_prof, 0, 1), 3),
            },
            index=date_range,
        )
        df.index.name = "date"

        # Introduce ~2% random missing values (realistic API gaps)
        for col in df.columns:
            mask = self._rng.random(n) < 0.02
            df.loc[mask, col] = np.nan

        if save:
            out_path = self._output_dir / filename
            df.to_csv(out_path)
            logger.info(
                f"Synthetic data saved to {out_path} | {len(df)} rows"
            )

        logger.warning(
            "SYNTHETIC DATA in use — for development/testing only. "
            "Replace with real NASA POWER data for dissertation submission."
        )
        return df

    # ------------------------------------------------------------------
    # Private generators
    # ------------------------------------------------------------------

    def _generate_rainfall(
        self, season: np.ndarray, n: int, year: np.ndarray
    ) -> np.ndarray:
        """
        Generate realistic daily rainfall using a two-component model:
        - Occurrence: Bernoulli process (probability is seasonal)
        - Amount: Gamma distribution (right-skewed, matches real rainfall)
        """
        # Rainy season probability: peaks at ~70% in January
        rain_prob = np.clip(0.4 + 0.35 * season, 0.02, 0.75)

        # Inter-annual variability (El Niño/La Niña, roughly 3.5-year cycle)
        enso_phase = np.sin(2 * np.pi * year / 3.5)
        rain_prob *= (1 + 0.15 * enso_phase)
        rain_prob = np.clip(rain_prob, 0.02, 0.80)

        # Rain occurrence
        rain_occurs = self._rng.random(n) < rain_prob

        # Gamma-distributed amounts (shape=0.8, scale=15mm — tuned for Zambia)
        amounts = self._rng.gamma(shape=0.8, scale=15.0, size=n)

        # Add occasional extreme events (5mm in 1% of days)
        extreme = self._rng.random(n) < 0.01
        amounts[extreme] *= 8

        return amounts * rain_occurs

    def _generate_temperature(
        self, season: np.ndarray, n: int
    ) -> np.ndarray:
        """
        Generate daily mean temperature.
        Zambia mean: ~23°C; hotter in dry season (Oct), cooler in July.
        """
        # Invert season: peak temp in Oct (dry season)
        base_temp = 22.5 - 4 * season
        noise = self._rng.normal(0, 1.5, n)
        return np.clip(base_temp + noise, 10, 38)

    def _generate_humidity(
        self, season: np.ndarray, rainfall: np.ndarray, n: int
    ) -> np.ndarray:
        """Relative humidity: high in rainy season and after rain events."""
        base_rh = 55 + 25 * (season + 1) / 2  # 55–80%
        rain_boost = np.minimum(rainfall * 0.5, 20)
        noise = self._rng.normal(0, 3, n)
        return np.clip(base_rh + rain_boost + noise, 20, 99)

    def _generate_wind_speed(
        self, season: np.ndarray, n: int
    ) -> np.ndarray:
        """Wind speed (m/s): slightly higher in dry season."""
        base_ws = 2.5 - 0.5 * season
        return np.clip(
            self._rng.gamma(shape=2, scale=base_ws / 2, size=n),
            0, 20,
        )

    def _generate_soil_moisture(
        self,
        rainfall: np.ndarray,
        n: int,
        lag: int = 1,
    ) -> np.ndarray:
        """
        Soil moisture modelled as a leaky bucket:
        soil[t] = soil[t-1] * decay + rainfall[t-1] * fill_rate
        """
        soil = np.zeros(n)
        soil[0] = 0.3
        decay = 0.97
        fill_rate = 0.01
        for t in range(1, n):
            rain_input = rainfall[max(0, t - lag)]
            soil[t] = soil[t - 1] * decay + rain_input * fill_rate
        return soil

    def _generate_solar_radiation(
        self, season: np.ndarray, n: int
    ) -> np.ndarray:
        """Solar irradiance (MJ/m²/day): lower in rainy season (cloud cover)."""
        base_solar = 22 - 8 * season
        noise = self._rng.normal(0, 1.5, n)
        return np.clip(base_solar + noise, 5, 35)

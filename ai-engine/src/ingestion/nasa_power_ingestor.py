"""
ingestion/nasa_power_ingestor.py
================================
Downloads daily meteorological data for Zambia from the NASA POWER API.

NASA POWER (Prediction Of Worldwide Energy Resources) provides freely
accessible daily weather data derived from satellite observations and
meteorological models.  It is ideal for developing countries like Zambia
where ground-based weather stations have sparse coverage.

Variables downloaded
--------------------
- PRECTOTCORR : Corrected precipitation (mm/day)
- T2M         : Temperature at 2m (°C)
- T2M_MAX     : Daily maximum temperature (°C)
- T2M_MIN     : Daily minimum temperature (°C)
- RH2M        : Relative humidity at 2m (%)
- WS2M        : Wind speed at 2m (m/s)
- ALLSKY_SFC_SW_DWN : Solar irradiance (MJ/m²/day)
- GWETROOT    : Root-zone soil wetness (0–1)
- GWETPROF    : Profile soil wetness (0–1)

Design decisions
----------------
- Uses ``httpx`` (async-ready HTTP client) for future compatibility with
  FastAPI async routes.
- All raw data is saved to ``data/raw/`` immediately after download so that
  the pipeline can be restarted without re-downloading.
- Multiple lat/lon locations (Zambia's key river basins) can be downloaded
  in one call by passing a list of coordinate tuples.

Usage
-----
    from src.ingestion.nasa_power_ingestor import NASAPowerIngestor
    ingestor = NASAPowerIngestor()
    df = ingestor.download(latitude=-15.4167, longitude=28.2833)
"""

import time
from pathlib import Path

import httpx
import pandas as pd

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NASAPowerIngestor:
    """
    Downloads daily NASA POWER data for a given location in Zambia.

    Parameters
    ----------
    output_dir : Path, optional
        Directory to save the raw CSV file.  Defaults to ``data/raw/``.
    max_retries : int
        Number of times to retry a failed API request.
    """

    def __init__(
        self,
        output_dir: Path = settings.raw_dir,
        max_retries: int = 3,
    ) -> None:
        self.output_dir = output_dir
        self.max_retries = max_retries
        self._cfg = settings.nasa_power

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def download(
        self,
        latitude: float = None,
        longitude: float = None,
        start_year: int = None,
        end_year: int = None,
        filename: str = None,
    ) -> pd.DataFrame:
        """
        Download NASA POWER daily data and save as CSV.

        Parameters
        ----------
        latitude : float
            Target latitude in decimal degrees (negative = South).
        longitude : float
            Target longitude in decimal degrees (positive = East).
        start_year : int
            First year to download (e.g. 2000).
        end_year : int
            Last year to download (e.g. 2023).
        filename : str, optional
            Output filename.  Defaults to config value.

        Returns
        -------
        pd.DataFrame
            DataFrame with a DatetimeIndex and one column per variable.

        Raises
        ------
        RuntimeError
            If the API returns an error after all retries are exhausted.
        """
        lat = latitude or self._cfg.default_latitude
        lon = longitude or self._cfg.default_longitude
        start = start_year or self._cfg.start_year
        end = end_year or self._cfg.end_year
        out_file = self.output_dir / (filename or self._cfg.output_filename)

        # Skip download if file already exists (idempotent pipeline)
        if out_file.exists():
            logger.info(f"Raw file already exists, loading from cache: {out_file}")
            return pd.read_csv(out_file, index_col="date", parse_dates=True)

        logger.info(
            f"Downloading NASA POWER data | lat={lat}, lon={lon} | "
            f"{start}–{end} | params={self._cfg.parameters}"
        )

        params_str = ",".join(self._cfg.parameters)
        url = (
            f"{self._cfg.base_url}"
            f"?parameters={params_str}"
            f"&community={self._cfg.community}"
            f"&longitude={lon}"
            f"&latitude={lat}"
            f"&start={start}0101"
            f"&end={end}1231"
            f"&format=JSON"
        )

        raw_json = self._fetch_with_retry(url)
        df = self._parse_response(raw_json)
        df.to_csv(out_file)
        logger.info(f"Saved {len(df)} rows to {out_file}")
        return df

    def download_multiple_locations(
        self,
        locations: list[tuple[float, float, str]],
    ) -> dict[str, pd.DataFrame]:
        """
        Download data for multiple locations (Zambia's key river basins).

        Parameters
        ----------
        locations : list of (lat, lon, name) tuples
            Each tuple represents a monitoring location.

        Returns
        -------
        dict[str, pd.DataFrame]
            Mapping of location name to DataFrame.
        """
        results: dict[str, pd.DataFrame] = {}
        for lat, lon, name in locations:
            logger.info(f"Downloading location: {name} ({lat}, {lon})")
            safe_name = name.replace(" ", "_").lower()
            df = self.download(
                latitude=lat,
                longitude=lon,
                filename=f"nasa_power_{safe_name}.csv",
            )
            results[name] = df
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_with_retry(self, url: str) -> dict:
        """
        Execute an HTTP GET request with exponential back-off retry logic.

        Parameters
        ----------
        url : str
            The fully-formed API URL.

        Returns
        -------
        dict
            Parsed JSON response body.

        Raises
        ------
        RuntimeError
            If all retries are exhausted.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"HTTP GET attempt {attempt}: {url}")
                with httpx.Client(timeout=self._cfg.timeout_seconds) as client:
                    response = client.get(url)
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: {exc}"
                )
                if attempt < self.max_retries:
                    sleep_secs = 2 ** attempt   # exponential back-off
                    logger.info(f"Retrying in {sleep_secs}s ...")
                    time.sleep(sleep_secs)
                else:
                    raise RuntimeError(
                        f"NASA POWER API failed after {self.max_retries} attempts. "
                        "Check your internet connection or try again later."
                    ) from exc

    def _parse_response(self, raw: dict) -> pd.DataFrame:
        """
        Parse the NASA POWER JSON response into a tidy DataFrame.

        The API returns a nested dict:
        ``properties -> parameter -> PARAM_NAME -> {YYYYMMDD: value}``

        Parameters
        ----------
        raw : dict
            Parsed JSON from the NASA POWER API.

        Returns
        -------
        pd.DataFrame
            Tidy DataFrame with DatetimeIndex and one column per parameter.

        Raises
        ------
        KeyError
            If the response structure is unexpected.
        """
        try:
            param_data = raw["properties"]["parameter"]
        except KeyError as exc:
            raise KeyError(
                f"Unexpected NASA POWER response structure: {list(raw.keys())}"
            ) from exc

        frames: dict[str, pd.Series] = {}
        for param_name, daily_values in param_data.items():
            series = pd.Series(daily_values, name=param_name)
            series.index = pd.to_datetime(series.index, format="%Y%m%d")
            # NASA POWER uses -999 as a fill value for missing data.
            series = series.replace(-999, float("nan"))
            frames[param_name] = series

        df = pd.DataFrame(frames)
        df.index.name = "date"
        df.columns = [c.lower() for c in df.columns]   # Standardise column names
        logger.debug(f"Parsed NASA POWER response: {df.shape}")
        return df

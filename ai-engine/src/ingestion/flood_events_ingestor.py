"""
ingestion/flood_events_ingestor.py
===================================
Loads and standardises historical flood event records for Zambia.

Data Sources
------------
1. EM-DAT International Disaster Database (https://www.emdat.be/)
   - Must be requested and downloaded manually (free for academic use).
   - Provides disaster type, start date, end date, affected provinces.

2. DMMU (Disaster Management and Mitigation Unit) Zambia
   - National-level flood records from government reports.
   - Available as PDF/Excel from https://www.dmmu.gov.zm/

3. ReliefWeb (https://reliefweb.int/)
   - UN-coordinated situational reports for Zambia floods.

This module loads whichever CSV files are available, standardises the schema,
and outputs a unified events DataFrame that the label creator uses.

Design decisions
----------------
- We favour real historical labels over synthetic ones.  This gives the model
  something real to learn from, rather than learning a hand-crafted rule.
- When real labels are unavailable, a clear warning is logged and the
  synthetic proxy fallback (SPI / multi-day accumulation) is used.
- The function is tolerant of slightly different column names from different
  sources by using a column-mapping approach.

Usage
-----
    from src.ingestion.flood_events_ingestor import FloodEventsIngestor
    events = FloodEventsIngestor().load()
    print(events.head())
"""

from pathlib import Path

import pandas as pd

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Column name mappings from common source formats to our standard schema.
_EMDAT_COLUMN_MAP: dict[str, str] = {
    "Start Year": "year_start",
    "Start Month": "month_start",
    "Start Day": "day_start",
    "End Year": "year_end",
    "End Month": "month_end",
    "End Day": "day_end",
    "Country": "country",
    "Subregion": "province",
    "Disaster Type": "disaster_type",
    "Total Affected": "total_affected",
}

_STANDARD_COLUMNS: list[str] = [
    "event_start",
    "event_end",
    "country",
    "province",
    "source",
    "total_affected",
]


class FloodEventsIngestor:
    """
    Loads historical flood event records from CSV files.

    Supported formats: EM-DAT export, custom DMMU format.

    Parameters
    ----------
    events_path : Path, optional
        Path to the flood events CSV.  Defaults to the path in settings.
    """

    def __init__(self, events_path: Path = None) -> None:
        self._path = events_path or settings.labels.historical_events_path

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def load(self) -> pd.DataFrame | None:
        """
        Load historical flood events.

        Returns
        -------
        pd.DataFrame or None
            Standardised DataFrame with columns ``event_start``, ``event_end``,
            ``country``, ``province``, ``source``, ``total_affected``.
            Returns ``None`` if no events file is found (proxy labels will be
            used instead).
        """
        if not self._path.exists():
            logger.warning(
                f"No historical flood events file found at {self._path}. "
                "Proxy labels (SPI / multi-day rainfall accumulation) will be "
                "used instead.  For stronger results, download EM-DAT data and "
                f"save it to {self._path}"
            )
            return None

        logger.info(f"Loading historical flood events from {self._path}")
        try:
            df = pd.read_csv(self._path)
            df = self._standardise(df)
            # Filter for Zambia only
            if "country" in df.columns:
                df = df[df["country"].str.upper().str.contains("ZAMBIA", na=False)]
            logger.info(f"Loaded {len(df)} Zambia flood events.")
            return df
        except Exception as exc:
            logger.error(f"Failed to load flood events: {exc}")
            return None

    def events_to_daily_labels(
        self,
        date_range: pd.DatetimeIndex,
    ) -> pd.Series:
        """
        Convert event records to a daily binary flood label Series.

        Any date that falls within a recorded flood event window is
        labelled 1 (Flood); all other dates are labelled 0 (No Flood).

        Parameters
        ----------
        date_range : pd.DatetimeIndex
            The full daily date range of our weather dataset.

        Returns
        -------
        pd.Series
            Binary flood label (1 = flood, 0 = no flood) indexed by date.
        """
        events_df = self.load()
        labels = pd.Series(0, index=date_range, name="flood_label", dtype=int)

        if events_df is None:
            logger.warning(
                "No events available — returning all-zero labels. "
                "These will be overwritten by proxy labels downstream."
            )
            return labels

        for _, row in events_df.iterrows():
            try:
                start = pd.Timestamp(row["event_start"])
                # A missing event_end means a single-day event (no end date was
                # recorded) — default it to event_start rather than letting a
                # NaT comparison silently produce an all-False mask, which used
                # to drop 9 of the 11 real events with no warning at all.
                end_raw = row["event_end"]
                end = pd.Timestamp(end_raw) if pd.notna(end_raw) else start
                mask = (date_range >= start) & (date_range <= end)
                labels[mask] = 1
            except Exception as exc:
                logger.warning(f"Skipping malformed event row: {exc}")

        positive_rate = labels.mean()
        logger.info(
            f"Label encoding complete: {labels.sum()} flood days "
            f"({positive_rate:.1%} of dataset)"
        )
        return labels

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _standardise(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename and restructure columns from known source formats.

        Parameters
        ----------
        df : pd.DataFrame
            Raw DataFrame loaded from CSV.

        Returns
        -------
        pd.DataFrame
            DataFrame with standardised column names.
        """
        # Try EM-DAT column mapping
        if "Start Year" in df.columns:
            df = df.rename(columns=_EMDAT_COLUMN_MAP)
            df = self._build_dates_from_components(df)
        # Try direct date columns
        elif "event_start" not in df.columns and "start_date" in df.columns:
            df = df.rename(columns={"start_date": "event_start", "end_date": "event_end"})

        if "source" not in df.columns:
            df["source"] = "unknown"

        return df

    def _build_dates_from_components(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build datetime columns from year/month/day component columns (EM-DAT format).

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with year_start, month_start, day_start columns.

        Returns
        -------
        pd.DataFrame
            DataFrame with event_start and event_end datetime columns.
        """
        for prefix in ("start", "end"):
            y_col = f"year_{prefix}"
            m_col = f"month_{prefix}"
            d_col = f"day_{prefix}"
            out_col = f"event_{prefix}"

            if all(c in df.columns for c in [y_col, m_col, d_col]):
                df[out_col] = pd.to_datetime(
                    {
                        "year": df[y_col].fillna(2000).astype(int),
                        "month": df[m_col].fillna(1).astype(int),
                        "day": df[d_col].fillna(1).astype(int),
                    },
                    errors="coerce",
                )
        return df

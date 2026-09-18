"""
tests/test_flood_events_ingestor.py
====================================
Regression coverage for two real bugs found in the 2026-09-08 audit and fixed in the
Phase 3 data-pipeline pass:

1. `zambia_flood_events_log.csv` row `ZM-2020-02` had an unquoted comma in
   `confidence_notes`, which crashed `pd.read_csv` and was silently swallowed by
   `FloodEventsIngestor.load()`'s broad except-clause, falling back to proxy labels.
2. `events_to_daily_labels()` compared against `pd.Timestamp(NaN)` (== NaT) for any
   event missing an `end_date`, which is always False — silently contributing zero
   labeled days for 9 of the real log's 11 events, with no warning.

2026-09-09: three pre-2020 events (`ZM-2007-01`, `ZM-2007-02`, `ZM-2009-01`) were added
to the log — researched specifically to give this project's chronological train/val/test
split real positive examples in the training period (see that CSV's README and
docs/bug-register.md BUG-16). The event count assertion below was updated from 11 to 14
accordingly.

These tests assert against the real, checked-in CSV file, not a synthetic fixture, since
the bugs (and the new coverage) were specific to that file's actual content.
"""
import pandas as pd

from src.ingestion.flood_events_ingestor import FloodEventsIngestor


def test_load_returns_all_fourteen_real_events_without_crashing():
    df = FloodEventsIngestor().load()
    assert df is not None, "load() returned None — the CSV parse is broken again"
    assert len(df) == 14


def test_single_day_events_each_contribute_exactly_one_labeled_day():
    date_range = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    labels = FloodEventsIngestor().events_to_daily_labels(date_range)

    # The 9 real 2020-2022 events with no recorded end_date are single-day events.
    single_day_starts = [
        "2020-01-03", "2020-01-17", "2020-01-24", "2020-02-06",
        "2020-03-11", "2020-03-24", "2020-04-02", "2021-01-08", "2022-01-20",
    ]
    for day in single_day_starts:
        assert labels.loc[day] == 1, f"expected {day} to be labeled a flood day"


def test_multi_day_events_label_their_full_window():
    date_range = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    labels = FloodEventsIngestor().events_to_daily_labels(date_range)

    zm_2023_01_window = pd.date_range("2023-01-16", "2023-02-27", freq="D")
    assert labels.loc[zm_2023_01_window].sum() == len(zm_2023_01_window)

    # 9 single-day events (1 day each) + the 43-day ZM-2023-01 window = 52. The three
    # 2007-2009 events and ZM-2025-01 fall outside this date_range and contribute
    # nothing here.
    assert labels.sum() == 9 + len(zm_2023_01_window)


def test_pre_2020_events_label_their_reported_month_range():
    # Regression coverage for the 2026-09-09 additions: month-level ranges, not
    # single days, and outside the 2020+ window the other tests use.
    date_range = pd.date_range("2007-01-01", "2009-12-31", freq="D")
    labels = FloodEventsIngestor().events_to_daily_labels(date_range)

    zm_2007_01 = pd.date_range("2007-01-01", "2007-04-30", freq="D")
    zm_2007_02 = pd.date_range("2007-12-01", "2008-01-31", freq="D")
    zm_2009_01 = pd.date_range("2009-03-01", "2009-04-30", freq="D")

    assert labels.loc[zm_2007_01].sum() == len(zm_2007_01)
    assert labels.loc[zm_2007_02].sum() == len(zm_2007_02)
    assert labels.loc[zm_2009_01].sum() == len(zm_2009_01)
    assert labels.sum() == len(zm_2007_01) + len(zm_2007_02) + len(zm_2009_01)


def test_missing_end_date_does_not_silently_drop_the_event():
    # Regression guard for the exact bug: before the fix, a NaT end_date made the
    # mask all-False, so this would have been 0.
    date_range = pd.date_range("2019-12-01", "2019-12-31", freq="D")
    # No real event falls in this range, so extend to include one single-day event.
    date_range = pd.date_range("2020-01-01", "2020-01-05", freq="D")
    labels = FloodEventsIngestor().events_to_daily_labels(date_range)
    assert labels.loc["2020-01-03"] == 1
    assert labels.sum() == 1

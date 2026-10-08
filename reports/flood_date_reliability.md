# DesInventar flood-date reliability

_Generated 2026-10-07T19:37:17+00:00 by `scripts/assess_flood_date_reliability.py`. Records are flagged, never removed._

**Why this matters:** the eventual target is *a flood starts in (t, t+7]*. That needs the flood **onset** date. Many DesInventar Zambia records carry the date of a later assessment, repair programme or data-entry batch.

Evidence (independent of rainfall, to avoid circular label selection): dry-season date (May–Oct), batch date (≥5 flood records on the same day), administrative text (assessment, repair, rehabilitation, construction, funding request…).

| Class | Rule | Records |
|---|---|---:|
| onset_plausible | exact day, no flag | 91 |
| onset_uncertain | exact day, one flag (or wet-season with batch/admin flag) | 102 |
| onset_unlikely | exact day in dry season AND batch or administrative text | 83 |
| no_exact_date | year-/month-only or invalid date | 168 |

Flags among exact-day records: dry season 117, batch date 69, administrative text 122.

Largest same-date batches: 2013-06-06 (20), 2017-05-03 (15), 2013-12-13 (7), 2009-03-27 (6), 2012-10-05 (6), 2012-05-03 (5), 2009-02-11 (5), 2004-03-31 (5)

## By year

|   event_start_date |   onset_plausible |   onset_uncertain |   onset_unlikely |
|-------------------:|------------------:|------------------:|-----------------:|
|               2000 |                 1 |                 0 |                1 |
|               2001 |                 3 |                 2 |                0 |
|               2004 |                 0 |                 5 |                0 |
|               2006 |                 3 |                 1 |                0 |
|               2007 |                 2 |                 2 |                0 |
|               2008 |                 8 |                 4 |                0 |
|               2009 |                 4 |                12 |                1 |
|               2010 |                 0 |                13 |                0 |
|               2011 |                 2 |                 6 |               11 |
|               2012 |                 6 |                 8 |               13 |
|               2013 |                12 |                19 |               24 |
|               2014 |                22 |                10 |                3 |
|               2015 |                 8 |                 6 |                8 |
|               2016 |                 6 |                 2 |                0 |
|               2017 |                 5 |                12 |               22 |
|               2022 |                 1 |                 0 |                0 |
|               2023 |                 1 |                 0 |                0 |
|               2025 |                 2 |                 0 |                0 |
|               2026 |                 5 |                 0 |                0 |

## Supporting (descriptive) evidence from rainfall

See `reports/chirps_validation_report.md` → *Rainfall on DesInventar exact-day flood dates*: the median 3-day rainfall ending on the recorded date is below a typical wet-season day for both CHIRPS and NASA POWER. This is reported as evidence about the dates, and is **not** used to classify records.

## Independent check of the flags (rainfall is not used to assign them)

7-day CHIRPS total ending on the recorded date, as a percentile of that district's wet-season (Nov–Apr) 7-day totals:

| date_reliability   |   records |   median_7day_chirps_mm |   median_wet_season_percentile |   pct_in_top_quarter |
|:-------------------|----------:|------------------------:|-------------------------------:|---------------------:|
| onset_plausible    |        90 |                    57.1 |                             75 |                   52 |
| onset_uncertain    |       101 |                    24.3 |                             38 |                   22 |
| onset_unlikely     |        82 |                     0.3 |                              4 |                    0 |

If the flags were arbitrary the classes would look alike. They separate sharply: `onset_unlikely` dates fall in essentially rain-free weeks, while `onset_plausible` dates follow unusually wet weeks.

## Decision for the researcher (Stage 3)

Options, none applied here: (1) positives = `onset_plausible` only, and treat `onset_uncertain`/`onset_unlikely` district-periods as *excluded* (neither class); (2) also include `onset_uncertain`; (3) widen the target window or move to a seasonal/monthly target if too few onset-plausible events remain; (4) seek corroborating dates from an independent source (DFO, ReliefWeb, DMMU situation reports). Using rainfall to select labels is not recommended (circular).

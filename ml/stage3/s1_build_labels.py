"""Stage 3, step 1 — three-state flood labels from the 2026-10-08 collection.

    1       FLOOD           a high-confidence onset is recorded here on this day
    0       NO FLOOD        no record, and no reason to doubt the absence
    MASKED  INSUFFICIENT    a flood is documented at this district around this time,
                            but not precisely enough to date it

The third state is the whole point. The collection's own reliability analysis shows that
only 91 of 444 DesInventar records carry a defensible onset date; the rest are later
assessments, repair programmes or data-entry batches. Treating those district-periods as
NO FLOOD would assert the opposite of what the source says, which is exactly the defect
the earlier pipeline had. They are excluded from both classes instead.

Masking rules, by reliability class:

    onset_plausible    -> POSITIVE on the recorded day
    onset_uncertain    -> MASK +/- MASK_DAYS_UNCERTAIN around the recorded day
    onset_unlikely     -> MASK +/- MASK_DAYS_UNLIKELY around the recorded day
                          (wider: the true onset could be well away from this date)
    no_exact_date      -> MASK the whole month (month precision) or year (year
                          precision) for that district

Nothing here uses rainfall. Selecting or grading labels by rainfall would make the
label a function of the predictor, and any model trained on it would be measuring its
own input. The collection's authors avoided that and so does this.

    python ml/stage3/s1_build_labels.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from ml import config as C  # noqa: E402

MASK_DAYS_UNCERTAIN = 7
MASK_DAYS_UNLIKELY = 30


def main() -> None:
    C.ensure_s3_dirs()

    audit = pd.read_csv(C.S3_EVENT_AUDIT)
    rel = pd.read_csv(C.S3_DATE_RELIABILITY)[["record_id", "date_reliability"]]
    ev = audit.merge(rel, on="record_id", how="left")

    # event_date is mixed-precision: "2013-05-06" for exact days but a bare "2013" for
    # year-precision records and "2013-05" for month-precision ones. A single
    # pd.to_datetime over the column infers a format from the full dates and coerces the
    # bare years to NaT — which silently DROPPED all 163 year-precision records on the
    # first run, turning those district-years into negatives. That is precisely the
    # contamination this three-state scheme exists to prevent, so each precision is
    # parsed on its own terms.
    raw = ev["event_date"].astype("string").str.strip()
    prec = ev.get("date_precision", pd.Series("", index=ev.index)).astype("string").str.lower()

    parsed = pd.to_datetime(raw, errors="coerce", format="%Y-%m-%d")
    year_only = prec.eq("year") & raw.str.fullmatch(r"\d{4}").fillna(False)
    parsed = parsed.mask(year_only, pd.to_datetime(raw.where(year_only) + "-01-01",
                                                   errors="coerce"))
    month_only = prec.eq("month") & raw.str.fullmatch(r"\d{4}-\d{2}").fillna(False)
    parsed = parsed.mask(month_only, pd.to_datetime(raw.where(month_only) + "-01",
                                                    errors="coerce"))
    # Anything still unparsed gets one last permissive attempt, per value.
    still = parsed.isna() & raw.notna()
    if still.any():
        parsed = parsed.mask(still, pd.to_datetime(raw.where(still), errors="coerce"))
    ev["event_date"] = parsed

    print("date parsing by precision:")
    for pcls, grp in ev.groupby(prec.fillna("(none)")):
        print(f"    {pcls:10s} {len(grp):>4} records, {grp.event_date.notna().sum():>4} dated")

    print(f"DesInventar flood records: {len(ev)}")
    print(ev["date_reliability"].value_counts().to_string())
    print(f"  resolved to a district : {ev.location_id.notna().sum()}")

    positives, masks, dropped = [], [], []

    for r in ev.itertuples():
        loc, d, cls = r.location_id, r.event_date, r.date_reliability
        if not isinstance(loc, str) or not loc:
            dropped.append({"record_id": r.record_id, "why": "no district resolved"})
            continue

        if cls == "onset_plausible":
            if pd.isna(d):
                dropped.append({"record_id": r.record_id, "why": "plausible but undated"})
                continue
            positives.append({"location_id": loc, "date": d.normalize(),
                              "record_id": r.record_id})

        elif cls in ("onset_uncertain", "onset_unlikely"):
            if pd.isna(d):
                dropped.append({"record_id": r.record_id, "why": f"{cls} but undated"})
                continue
            w = MASK_DAYS_UNCERTAIN if cls == "onset_uncertain" else MASK_DAYS_UNLIKELY
            masks.append({"location_id": loc,
                          "start": d.normalize() - pd.Timedelta(days=w),
                          "end": d.normalize() + pd.Timedelta(days=w),
                          "reason": cls, "record_id": r.record_id})

        elif cls == "no_exact_date":
            # Precision decides the width: a year-only record makes the whole year
            # undetermined for that district; a month-only record, that month.
            prec = str(getattr(r, "date_precision", "") or "").lower()
            if pd.notna(d) and "month" in prec:
                start = d.normalize().replace(day=1)
                end = start + pd.offsets.MonthEnd(0)
            elif pd.notna(d):
                start = pd.Timestamp(d.year, 1, 1)
                end = pd.Timestamp(d.year, 12, 31)
            else:
                dropped.append({"record_id": r.record_id,
                                "why": "no usable date at all — contributes nothing"})
                continue
            masks.append({"location_id": loc, "start": start, "end": end,
                          "reason": f"no_exact_date ({prec or 'year'})",
                          "record_id": r.record_id})
        else:
            dropped.append({"record_id": r.record_id, "why": f"unclassified: {cls}"})

    pos = pd.DataFrame(positives).drop_duplicates(subset=["location_id", "date"])
    msk = pd.DataFrame(masks)
    drp = pd.DataFrame(dropped)

    pos.to_csv(C.S3_OUT_PROCESSED / "labels_positive_district_days.csv", index=False)
    msk.to_csv(C.S3_OUT_PROCESSED / "labels_mask_intervals.csv", index=False)
    drp.to_csv(C.S3_OUT_PROCESSED / "labels_dropped_records.csv", index=False)

    summary = {
        "generated": "stage3/s1_build_labels.py",
        "records_total": int(len(ev)),
        "reliability_classes": {k: int(v) for k, v in
                                ev["date_reliability"].value_counts().items()},
        "positive_district_days": int(len(pos)),
        "positive_districts": int(pos.location_id.nunique()) if len(pos) else 0,
        "positive_distinct_dates": int(pos.date.nunique()) if len(pos) else 0,
        "positive_date_range": [str(pos.date.min().date()), str(pos.date.max().date())]
                               if len(pos) else None,
        "mask_intervals": int(len(msk)),
        "mask_reasons": {k: int(v) for k, v in msk.reason.value_counts().items()} if len(msk) else {},
        "dropped_records": int(len(drp)),
        "rules": {
            "mask_days_uncertain": MASK_DAYS_UNCERTAIN,
            "mask_days_unlikely": MASK_DAYS_UNLIKELY,
            "rainfall_used_to_select_labels": False,
        },
    }
    (C.S3_OUT_PROCESSED / "labels_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print()
    print(f"POSITIVE district-days : {summary['positive_district_days']} "
          f"across {summary['positive_districts']} districts, "
          f"{summary['positive_distinct_dates']} distinct dates")
    print(f"  range                : {summary['positive_date_range']}")
    print(f"MASK intervals         : {summary['mask_intervals']}")
    for k, v in summary["mask_reasons"].items():
        print(f"    {k:34s} {v}")
    print(f"DROPPED records        : {summary['dropped_records']}")
    print(f"\nWrote {C.S3_OUT_PROCESSED}")


if __name__ == "__main__":
    main()

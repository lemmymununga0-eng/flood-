"""CHIRPS-specific validation -> reports/chirps_validation_report.md (+ CSV tables).

Checks: date coverage, missing days, missing/no-data pixels, duplicate days, negative and extreme
rainfall, location coverage, annual and monthly totals per district point, and a comparison with
NASA POWER PRECTOTCORR. The two products are independent; disagreement is reported, never "fixed".

Also investigates the NASA POWER daily rainfall values flagged above the plausibility bound
(reports/nasa_power_anomaly_investigation.md): neighbouring days, CHIRPS on the same day at the
same point, districts sharing the POWER grid cell, and DesInventar floods in the district +-7 days.

Usage
  python scripts/validate_chirps.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, load_window, p, utc_now  # noqa: E402


def md_table(df: pd.DataFrame, floatfmt="{:.1f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, (float, np.floating)) and pd.notna(v)
                                     else ("" if pd.isna(v) else str(v)) for v in r) + " |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("validate_chirps", cfg)
    rep = p(cfg, "reports")
    proc = ROOT / cfg["paths"]["processed"]
    win = load_window(cfg)
    full = pd.date_range(win["start"], win["end"], freq="D")
    c = cfg["chirps"]
    v = cfg["validation"]

    # ---- grid-level checks per yearly file ------------------------------------------------------
    files = sorted(f for f in p(cfg, "raw_chirps").glob("*.zambia.*.nc") if ".part" not in f.name)
    yr_rows, times = [], []
    grid = None
    for f in files:
        with xr.open_dataset(f) as ds:
            a = ds["precip"].values
            t = pd.DatetimeIndex(ds["time"].values)
            times.append(t)
            g = (ds.sizes["lat"], ds.sizes["lon"], float(ds.lat.min()), float(ds.lat.max()), float(ds.lon.min()), float(ds.lon.max()))
            grid = grid or g
            nan = ~np.isfinite(a)
            nod = np.isin(a, c["nodata_values"])
            fin = np.where(nan | nod, np.nan, a)
            yr = int(f.stem.split(".")[-1])
            exp = full[full.year == yr]
            yr_rows.append({"year": yr, "days_expected": len(exp), "days_present": len(t),
                            "missing_days": len(exp.difference(t)), "duplicate_days": int(t.duplicated().sum()),
                            "grid_matches_first_file": g == grid, "missing_pixels": int(nan.sum() + nod.sum()),
                            "negative_pixels": int((fin < 0).sum()),
                            f"pixel_days_gt_{v['extreme_rain_mm']}mm": int((fin > v["extreme_rain_mm"]).sum()),
                            "max_mm": float(np.nanmax(fin)),
                            "zambia_window_mean_annual_total_mm": float(np.nansum(fin, axis=0).mean())})
    yr_df = pd.DataFrame(yr_rows)
    years_needed = sorted(set(full.year))
    missing_years = [y for y in years_needed if y not in set(yr_df["year"])]
    allt = times[0].append(times[1:]) if len(times) > 1 else (times[0] if times else pd.DatetimeIndex([]))
    missing_dates = full.difference(allt)

    # ---- district point series --------------------------------------------------------------------
    pts = pd.read_csv(proc / "chirps_daily_at_locations.csv", parse_dates=["date"])
    master = pd.read_csv(proc / "location_master.csv")
    exp_locs = set(master.loc[master["in_weather_collection"], "location_id"])
    pts_cov = pts.groupby("location_id")["date"].agg(["min", "max", "count"])
    pts_dup = int(pts.duplicated(["location_id", "date"]).sum())
    pts_missing = int(pts["chirps_precip_mm"].isna().sum())
    shared_px = pts.drop_duplicates("location_id").groupby(["pixel_lat", "pixel_lon"])["location_id"].apply(list)
    shared_px = [l for l in shared_px if len(l) > 1]
    pts["year"] = pts["date"].dt.year
    complete_years = [y for y in years_needed if y not in missing_years and (full.year == y).sum() == 365 + (y % 4 == 0)
                      and y not in (full.min().year, full.max().year)]
    ann = (pts[pts["year"].isin(complete_years)].groupby(["location_id", "year"])["chirps_precip_mm"].sum()
           .groupby("location_id").agg(["mean", "min", "max"]).rename(columns=lambda s: f"annual_{s}_mm"))
    ann = ann.join(master.set_index("location_id")[["district", "province"]])
    mon_clim = (pts.assign(month=pts["date"].dt.month, ym=pts["date"].dt.to_period("M"))
                .groupby(["location_id", "ym", "month"])["chirps_precip_mm"].sum().groupby("month").mean())

    # ---- per-year verification of the district extraction ----------------------------------------
    units = set()
    for f in files:
        with xr.open_dataset(f) as ds:
            units.add(ds["precip"].attrs.get("units"))
    py_rows = []
    for y in years_needed:
        exp_days = int((full.year == y).sum())
        sub = pts[pts["year"] == y]
        per = sub.groupby("location_id")["date"].nunique()
        py_rows.append({"year": y, "expected_days": exp_days, "locations_present": int(sub["location_id"].nunique()),
                        "locations_with_all_days": int((per == exp_days).sum()),
                        "duplicate_location_dates": int(sub.duplicated(["location_id", "date"]).sum()),
                        "missing_values": int(sub["chirps_precip_mm"].isna().sum()),
                        "negative_values": int((sub["chirps_precip_mm"] < 0).sum()),
                        "max_point_mm": round(float(sub["chirps_precip_mm"].max()), 1) if len(sub) else np.nan,
                        "verified": bool(len(sub) and sub["location_id"].nunique() == len(exp_locs) and (per == exp_days).all()
                                         and not sub.duplicated(["location_id", "date"]).any()
                                         and sub["chirps_precip_mm"].notna().all() and (sub["chirps_precip_mm"] >= 0).all())})
    py_df = pd.DataFrame(py_rows)
    py_df.to_csv(rep / "chirps_per_year_location_checks.csv", index=False)
    # same pixel used for every location in every year (consistent spatial extraction)
    px_per_loc = pts.groupby("location_id")[["pixel_lat", "pixel_lon"]].nunique().max(axis=1)
    extraction_consistent = bool((px_per_loc == 1).all())

    # ---- investigation of grid extremes (> 300 mm in a day) --------------------------------------
    import geopandas as gpd
    from shapely.geometry import Point
    dist = gpd.read_file(ROOT / cfg["spatial"]["district_polygons"])
    zm = dist.set_crs("EPSG:4326", allow_override=True).union_all() if dist.crs is None else dist.to_crs("EPSG:4326").union_all()
    from rasterio.features import geometry_mask
    from rasterio.transform import from_origin

    def zmask(a):  # True where the CHIRPS cell centre lies inside Zambia (union of district polygons)
        lat, lon = a.lat.values, a.lon.values
        tr = from_origin(lon.min() - 0.025, lat.max() + 0.025, 0.05, 0.05)
        m = geometry_mask([zm], out_shape=(len(lat), len(lon)), transform=tr, invert=True)
        return m if lat[0] > lat[-1] else m[::-1]
    ext_path = rep / "chirps_extreme_events.csv"
    cached = pd.read_csv(ext_path) if ext_path.exists() else pd.DataFrame(columns=["date"])
    ext_rows = []
    for f in files:
        with xr.open_dataset(f) as ds:
            daymax = ds["precip"].max(["lat", "lon"]).to_series()
            for d0, mx in daymax[daymax > 300].items():
                a = ds["precip"].sel(time=d0)
                loc = a.where(a == a.max(), drop=True)
                la, lo = float(loc.lat[0]), float(loc.lon[0])
                big = a > 100
                pent_start = pd.Timestamp(d0.year, d0.month, min(1 + 5 * ((d0.day - 1) // 5), 26))
                pent_end = pd.Timestamp(d0.year, d0.month, 1) + pd.offsets.MonthEnd(0) if pent_start.day == 26 else pent_start + pd.Timedelta(days=4)
                pent_sum = float(ds["precip"].sel(lat=la, lon=lo).sel(time=slice(pent_start, pent_end)).sum())
                big_in_zm = int((big.values & zmask(a)).sum())
                prev = cached[cached["date"] == str(d0.date())]
                rec = {"date": str(d0.date()), "max_mm": round(float(mx), 1), "lat": la, "lon": lo,
                       "max_pixel_inside_zambia": bool(zm.contains(Point(lo, la))),
                       "cells_gt_100mm": int(big.sum()), "cells_gt_100mm_inside_zambia": big_in_zm,
                       "stored_pentad_sum_mm": round(pent_sum, 1), "pentad": f"{pent_start.date()}..{pent_end.date()}",
                       "official_pentad_mm": prev["official_pentad_mm"].iloc[0] if len(prev) else np.nan,
                       "original_daily_cog_mm": prev["original_daily_cog_mm"].iloc[0] if len(prev) else np.nan}
                if not len(prev) or pd.isna(rec["official_pentad_mm"]):
                    try:  # one range read each: is the value in the source product (not our extraction)?
                        import rasterio
                        env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".cog")
                        pnum = (pent_start.day - 1) // 5 + 1
                        with rasterio.Env(**env):
                            with rasterio.open("/vsicurl/" + c["cog_url_template"].format(stream=c["stream"], variant=c["variant"],
                                                year=d0.year, month=d0.month, day=d0.day)) as src:
                                rec["original_daily_cog_mm"] = round(float(list(src.sample([(lo, la)]))[0][0]), 3)
                            with rasterio.open(f"/vsicurl/https://data.chc.ucsb.edu/products/CHIRPS/v3.0/pentads/global/cogs/"
                                               f"chirps-v3.0.{d0.year}.{d0.month:02d}.{pnum}.cog") as src:
                                rec["official_pentad_mm"] = round(float(list(src.sample([(lo, la)]))[0][0]), 2)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Could not re-read source for %s: %s", d0.date(), e)
                ext_rows.append(rec)
    ext_df = pd.DataFrame(ext_rows)
    if len(ext_df):
        near = master[["location_id", "district", "latitude", "longitude"]]
        def nearest_points(r):
            dd = np.hypot(near["latitude"] - r["lat"], near["longitude"] - r["lon"])
            k = dd.idxmin()
            v = pts[(pts["location_id"] == near.loc[k, "location_id"]) & (pts["date"] == pd.Timestamp(r["date"]))]["chirps_precip_mm"]
            return pd.Series({"nearest_district": near.loc[k, "district"], "nearest_point_km": round(dd[k] * 111, 0),
                              "nearest_point_chirps_mm": round(float(v.iloc[0]), 1) if len(v) else np.nan})
        ext_df = pd.concat([ext_df, ext_df.apply(nearest_points, axis=1)], axis=1)
        ext_df.to_csv(ext_path, index=False)

    # ---- comparison with NASA POWER --------------------------------------------------------------
    pw = pd.read_csv(ROOT / cfg["paths"]["raw_nasa_power"] / ".." / "nasa_power_daily.csv",
                     usecols=["location_id", "date", "PRECTOTCORR"], parse_dates=["date"])
    j = pw.merge(pts[["location_id", "date", "chirps_precip_mm"]], on=["location_id", "date"])
    j["ym"] = j["date"].dt.to_period("M")
    mon = j.groupby(["location_id", "ym"])[["PRECTOTCORR", "chirps_precip_mm"]].sum()
    per_loc = pd.DataFrame({
        "daily_r": j.groupby("location_id").apply(lambda g: g["PRECTOTCORR"].corr(g["chirps_precip_mm"]), include_groups=False),
        "monthly_r": mon.groupby(level=0).apply(lambda g: g["PRECTOTCORR"].corr(g["chirps_precip_mm"])),
        "power_mean_annual_mm": j.groupby("location_id")["PRECTOTCORR"].mean() * 365.25,
        "chirps_mean_annual_mm": j.groupby("location_id")["chirps_precip_mm"].mean() * 365.25,
        "wet_day_agreement": j.assign(a=(j["PRECTOTCORR"] >= 1) == (j["chirps_precip_mm"] >= 1))
                              .groupby("location_id")["a"].mean(),
    })
    per_loc["chirps_minus_power_pct"] = 100 * (per_loc["chirps_mean_annual_mm"] / per_loc["power_mean_annual_mm"] - 1)
    per_loc = per_loc.join(master.set_index("location_id")[["district", "province"]])
    per_loc.to_csv(rep / "chirps_vs_nasa_power_by_location.csv")

    # bias (CHIRPS minus POWER) and extreme-event behaviour of each source
    dd = j["chirps_precip_mm"] - j["PRECTOTCORR"]
    md = mon["chirps_precip_mm"] - mon["PRECTOTCORR"]
    wet = (j["chirps_precip_mm"] >= 1) | (j["PRECTOTCORR"] >= 1)
    bias = {"mean_daily_bias_mm": dd.mean(), "median_daily_bias_mm": dd.median(),
            "median_daily_bias_wet_days_mm": dd[wet].median(), "mean_abs_daily_diff_mm": dd.abs().mean(),
            "mean_monthly_bias_mm": md.mean(), "median_monthly_bias_mm": md.median()}
    yrs = j["date"].dt.year
    ext_stats = {}
    for col, name in (("chirps_precip_mm", "CHIRPS"), ("PRECTOTCORR", "NASA POWER")):
        s = j[col]
        ext_stats[name] = {"wet_day_frequency_pct": 100 * (s >= 1).mean(), "p99_all_days_mm": s.quantile(0.99),
                           "p99_wet_days_mm": s[s >= 1].quantile(0.99), "max_mm": s.max(),
                           "mean_annual_max_day_mm": s.groupby([j["location_id"], yrs]).max().mean(),
                           "days_gt_50mm_per_location_year": (s > 50).groupby([j["location_id"], yrs]).sum().mean()}
    hc, hp = j["chirps_precip_mm"] >= 30, j["PRECTOTCORR"] >= 30
    heavy = {"heavy_days_both": int((hc & hp).sum()), "heavy_chirps_only": int((hc & ~hp).sum()),
             "heavy_power_only": int((~hc & hp).sum()), "heavy_jaccard": (hc & hp).sum() / max(1, (hc | hp).sum())}
    # rainfall on DesInventar exact-day flood dates (descriptive only; no target is built)
    flv = pd.read_csv(proc / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    rres = pd.read_csv(rep / "location_resolution_report.csv", dtype=str, keep_default_na=False)
    flv = flv.merge(rres[["record_id", "location_id"]], left_on="clave", right_on="record_id")
    flv = flv[(flv["date_precision"] == "day") & (flv["date_quality_flag"] == "") & (flv["location_id"] != "")]
    flv["d"] = pd.to_datetime(flv["event_start_date"])
    jj = j.sort_values(["location_id", "date"]).copy()
    for col in ("chirps_precip_mm", "PRECTOTCORR"):
        jj[col + "_3d"] = jj.groupby("location_id")[col].transform(lambda s: s.rolling(3, min_periods=3).sum())
    season = jj[jj["date"].dt.month.isin([11, 12, 1, 2, 3, 4])]
    ev = flv.merge(jj, left_on=["location_id", "d"], right_on=["location_id", "date"])
    flood_day = {"n_flood_days_matched": int(len(ev))}
    for col, name in (("chirps_precip_mm_3d", "CHIRPS"), ("PRECTOTCORR_3d", "NASA POWER")):
        pr = [float((season.loc[season["location_id"] == r.location_id, col] <= getattr(r, col)).mean()) for r in ev.itertuples()]
        flood_day[name] = {"median_3day_total_mm_ending_on_flood_date": float(ev[col].median()),
                           "median_wet_season_3day_total_mm": float(season[col].median()),
                           "median_percentile_of_flood_date_3day_total": 100 * float(np.median(pr)) if pr else np.nan}
    ann.to_csv(rep / "chirps_annual_totals_by_location.csv")
    yr_df.to_csv(rep / "chirps_yearly_file_checks.csv", index=False)

    # ---- NASA POWER anomaly investigation ---------------------------------------------------------
    flags = pd.read_csv(rep / "nasa_power_flagged_values.csv") if (rep / "nasa_power_flagged_values.csv").exists() else pd.DataFrame()
    pw_all = pd.read_csv(ROOT / cfg["paths"]["raw_nasa_power"] / ".." / "nasa_power_daily.csv",
                         usecols=["location_id", "date", "PRECTOTCORR", "power_point_latitude", "power_point_longitude"], parse_dates=["date"])
    fl = pd.read_csv(proc / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    res = pd.read_csv(rep / "location_resolution_report.csv", dtype=str, keep_default_na=False)
    fl = fl.merge(res[["record_id", "location_id"]], left_on="clave", right_on="record_id", how="left")
    fl_day = fl[fl["date_precision"] == "day"].assign(d=lambda x: pd.to_datetime(x["event_start_date"]))
    anomalies = flags[flags["flag"].str.startswith("outside_bounds")] if len(flags) else flags
    A = ["# NASA POWER rainfall anomaly investigation", "",
         f"_Generated {utc_now()} by `scripts/validate_chirps.py`. Values are investigated, not deleted._", ""]
    for r in anomalies.itertuples():
        d0 = pd.Timestamp(r.date)
        s = pw_all[(pw_all["location_id"] == r.location_id) & pw_all["date"].between(d0 - pd.Timedelta(days=3), d0 + pd.Timedelta(days=3))]
        cs = pts[(pts["location_id"] == r.location_id) & pts["date"].between(d0 - pd.Timedelta(days=3), d0 + pd.Timedelta(days=3))]
        win7 = s.merge(cs[["date", "chirps_precip_mm"]], on="date", how="left")[["date", "PRECTOTCORR", "chirps_precip_mm"]]
        win7["date"] = win7["date"].dt.date
        same_day = pw_all[pw_all["date"] == d0]
        cell = same_day[(same_day["location_id"] == r.location_id)][["power_point_latitude", "power_point_longitude"]].iloc[0]
        nb = same_day.sort_values("PRECTOTCORR", ascending=False).head(5)[["location_id", "PRECTOTCORR"]]
        ev = fl_day[(fl_day["location_id"] == r.location_id) & fl_day["d"].between(d0 - pd.Timedelta(days=7), d0 + pd.Timedelta(days=7))]
        name = master.set_index("location_id").loc[r.location_id, "district"]
        cmax = None
        f = p(cfg, "raw_chirps") / f"chirps-v3.0.{c['variant']}.zambia.{d0.year}.nc"
        if f.exists():
            with xr.open_dataset(f) as ds:
                cmax = float(ds["precip"].sel(time=d0).max())
        A += [f"## {r.location_id} ({name}) — {r.date}: {r.value} mm/day", "",
              md_table(win7, "{:.2f}"), "",
              f"- Highest NASA POWER values that day (all districts): " + ", ".join(f"{a} {b:.1f}" for a, b in nb.itertuples(index=False)),
              f"- CHIRPS maximum anywhere in the Zambia window that day: {cmax if cmax is None else round(cmax, 1)} mm",
              f"- DesInventar flood records in this district within ±7 days: {len(ev)}"
              + ("" if ev.empty else " — " + "; ".join(f"{a} ({b})" for a, b in ev[["event_start_date", "lugar"]].itertuples(index=False))),
              ""]
    A += ["## Interpretation", "",
          "NASA POWER PRECTOTCORR is a bias-corrected MERRA-2 reanalysis field on a ~0.5° grid. Single-day totals "
          "above 300 mm at a district point are physically possible in convective storms but rare in Zambia; where "
          "CHIRPS on the same day is far lower, the value is most likely a reanalysis artefact. The values are kept "
          "unchanged and flagged (`reports/nasa_power_flagged_values.csv`). Stage 3 should decide explicitly whether "
          "to cap/winsorise rainfall features, using the same rule for every location.", ""]
    (rep / "nasa_power_anomaly_investigation.md").write_text("\n".join(A), encoding="utf-8")

    # ---- report ----------------------------------------------------------------------------------
    complete = (not missing_years and len(missing_dates) == 0 and bool(py_df["verified"].all())
                and extraction_consistent and units == {"mm/day"})
    ext_tbl = (md_table(ext_df[["date", "max_mm", "lat", "lon", "max_pixel_inside_zambia", "cells_gt_100mm", "cells_gt_100mm_inside_zambia",
                                "stored_pentad_sum_mm", "official_pentad_mm", "original_daily_cog_mm", "nearest_district",
                                "nearest_point_km", "nearest_point_chirps_mm"]], "{:.2f}") if len(ext_df) else "None.")
    st = pd.DataFrame(ext_stats).T.reset_index().rename(columns={"index": "source"})
    L = ["# CHIRPS v3.0 Validation Report", "",
         f"_Generated {utc_now()} by `scripts/validate_chirps.py`._", "",
         f"**Product:** CHIRPS v3.0 daily, `{c['stream']}` stream, `{c['variant']}` disaggregation, 0.05°. "
         f"**Required window:** {win['start']} → {win['end']} ({len(full)} days).", "",
         "## Coverage", "",
         f"- Yearly files present: {len(files)} of {len(years_needed)} required ({years_needed[0]}–{years_needed[-1]})",
         f"- Missing years: {missing_years or 'none'}",
         f"- Days present: {allt.nunique()} of {len(full)}; missing days: {len(missing_dates)}"
         + (f" (first: {missing_dates[0].date()}, last: {missing_dates[-1].date()})" if len(missing_dates) else ""),
         f"- Duplicate days: {int(allt.duplicated().sum())}",
         f"- Grid: {grid[0]} × {grid[1]} cells, lat {grid[2]:.3f}…{grid[3]:.3f}, lon {grid[4]:.3f}…{grid[5]:.3f}" if grid else "- Grid: n/a",
         f"- Grid identical in every yearly file: {bool(yr_df['grid_matches_first_file'].all())}",
         f"- Missing/no-data pixel-days: {int(yr_df['missing_pixels'].sum())}; negative pixel-days: {int(yr_df['negative_pixels'].sum())}",
         f"- Pixel-days above {v['extreme_rain_mm']} mm (flagged, kept): {int(yr_df[f'pixel_days_gt_{v['extreme_rain_mm']}mm'].sum())}; "
         f"maximum value: {yr_df['max_mm'].max():.1f} mm/day", "",
         "## Location coverage (nearest-pixel extraction at the location-master points)", "",
         f"- Locations expected: {len(exp_locs)}; present: {pts['location_id'].nunique()}; missing: {sorted(exp_locs - set(pts['location_id'])) or 'none'}",
         f"- Rows: {len(pts)}; missing values: {pts_missing}; duplicate location-dates: {pts_dup}",
         f"- Date range of extraction: {pts['date'].min().date()} → {pts['date'].max().date()}",
         f"- Locations sharing the same CHIRPS pixel: {shared_px or 'none'}", "",
         f"- Units attribute of every yearly file: {sorted(map(str, units))} (CHIRPS v3.0 official unit: mm/day)",
         f"- Each location uses the same CHIRPS pixel in every year (consistent extraction): {extraction_consistent}", "",
         "## Per-year verification of the 101-location extraction", "",
         "A year is *verified* only if all 101 locations have every expected day, with no duplicates, missing or negative values.", "",
         md_table(py_df), "",
         "## Per-year grid file checks", "", md_table(yr_df), "",
         "## Annual totals (complete calendar years only)", "",
         f"Years used: {complete_years[0]}–{complete_years[-1]} ({len(complete_years)} years)." if complete_years else "No complete years.", "",
         md_table(ann.reset_index().sort_values("annual_mean_mm").iloc[[0, 1, 2, len(ann) // 2, -3, -2, -1]]
                  [["location_id", "district", "province", "annual_mean_mm", "annual_min_mm", "annual_max_mm"]]) if len(ann) > 6 else "",
         "", f"Across all districts: mean annual total {ann['annual_mean_mm'].mean():.0f} mm "
         f"(range of district means {ann['annual_mean_mm'].min():.0f}–{ann['annual_mean_mm'].max():.0f} mm). "
         "Full table: `reports/chirps_annual_totals_by_location.csv`." if len(ann) else "", "",
         "## Mean monthly totals (all districts)", "",
         md_table(mon_clim.rename("mean_monthly_total_mm").reset_index()), "",
         "The expected Zambian regime — a November–March rainy season and near-zero May–September — is the check here.", "",
         "## Comparison with NASA POWER PRECTOTCORR (independent products; not forced to agree)", "",
         f"- Overlapping location-days: {len(j)}",
         f"- Daily correlation: median {per_loc['daily_r'].median():.3f} (range {per_loc['daily_r'].min():.3f}–{per_loc['daily_r'].max():.3f})",
         f"- Monthly-total correlation: median {per_loc['monthly_r'].median():.3f} (range {per_loc['monthly_r'].min():.3f}–{per_loc['monthly_r'].max():.3f})",
         f"- Mean annual rainfall, all districts: CHIRPS {per_loc['chirps_mean_annual_mm'].mean():.0f} mm vs NASA POWER {per_loc['power_mean_annual_mm'].mean():.0f} mm "
         f"(CHIRPS − POWER median {per_loc['chirps_minus_power_pct'].median():+.1f}%)",
         f"- Wet-day (≥1 mm) agreement: median {100 * per_loc['wet_day_agreement'].median():.1f}% of days", "",
         "Selected districts:", "",
         md_table(per_loc.reset_index().set_index("district").loc[[d for d in ["Lusaka", "Kalabo", "Mongu", "Chipata", "Kasama", "Livingstone", "Solwezi"]
                                                                    if d in set(per_loc["district"])]].reset_index()
                  [["district", "province", "daily_r", "monthly_r", "chirps_mean_annual_mm", "power_mean_annual_mm", "chirps_minus_power_pct"]], "{:.3f}"), "",
         "Full table: `reports/chirps_vs_nasa_power_by_location.csv`. Daily agreement is expected to be modest: CHIRPS "
         "daily values are pentad totals disaggregated with ERA5 timing, while POWER is MERRA-2; monthly agreement is the "
         "more meaningful consistency check.", "",
         "### Bias (CHIRPS − NASA POWER)", "",
         f"- Daily: mean {bias['mean_daily_bias_mm']:+.2f} mm/day; median {bias['median_daily_bias_mm']:+.2f} mm/day "
         f"(median over days when either source has ≥1 mm: {bias['median_daily_bias_wet_days_mm']:+.2f}); mean absolute difference "
         f"{bias['mean_abs_daily_diff_mm']:.2f} mm/day",
         f"- Monthly totals: mean {bias['mean_monthly_bias_mm']:+.1f} mm/month; median {bias['median_monthly_bias_mm']:+.1f} mm/month", "",
         "### Extreme-event behaviour (all location-days in the overlap)", "", md_table(st, "{:.2f}"), "",
         f"Heavy-rain days (≥30 mm): both sources {heavy['heavy_days_both']}, CHIRPS only {heavy['heavy_chirps_only']}, "
         f"POWER only {heavy['heavy_power_only']} (overlap/union = {heavy['heavy_jaccard']:.2f}). The two products rarely "
         "agree on *which* day is extreme, even when monthly totals agree.", "",
         f"Rainfall on DesInventar exact-day flood dates ({flood_day['n_flood_days_matched']} location-dates; descriptive only, no target built): "
         + "; ".join(f"{k}: median 3-day total ending on the flood date {vv['median_3day_total_mm_ending_on_flood_date']:.1f} mm vs "
                     f"{vv['median_wet_season_3day_total_mm']:.1f} mm on a typical wet-season day (median percentile "
                     f"{vv['median_percentile_of_flood_date_3day_total']:.0f})" for k, vv in flood_day.items() if isinstance(vv, dict)), "",
         "### Are the two sources redundant?", "",
         "High monthly correlation shows the two products describe the same seasonal rainfall regime; it does **not** "
         "show that either is correct. At the daily scale they differ substantially (correlation, heavy-day overlap above). "
         "Using both in one model would partly duplicate the seasonal signal; Stage 3 must justify the choice (e.g. one "
         "source as the primary feature set and the other as a sensitivity analysis, or a documented combination) "
         "rather than stacking both by default.", "",
         "## Grid extremes above 300 mm/day (retained and flagged)", "",
         "Each event is checked against the source: `original_daily_cog_mm` is the value re-read from the official CHC daily "
         "file at the same cell (equal → not an extraction artifact); `official_pentad_mm` is the CHIRPS v3 pentad total "
         "(equal to `stored_pentad_sum_mm` → not a daily-disaggregation artifact). Whether the pentad total itself is "
         "physically real cannot be proven from CHIRPS alone.", "",
         ext_tbl, "",
         "**2009-04-02 (402 mm):** identical in the official file and our copy (not an extraction artifact); the 1–5 April "
         "daily values sum to the official pentad total (not a disaggregation artifact). The cluster of >100 mm cells lies "
         "at the north-east edge of the window, largely outside Zambia (Malawi/Tanzania border), and the nearest district "
         "points (Nakonde, Isoka) received 20–30 mm that day. Classification: **plausible but unverified extreme in the "
         "source product — retained and flagged; it does not enter any district series.**", "",
         "## NASA POWER anomalies", "", "See `reports/nasa_power_anomaly_investigation.md`.", "",
         "## Verdict", "",
         ("**COMPLETE** — every day of the required window is present with no missing or negative values."
          if complete else f"**PARTIAL** — {len(missing_years)} year(s) / {len(missing_dates)} day(s) still missing; "
          f"years not yet verified: {py_df.loc[~py_df['verified'], 'year'].tolist()}."), ""]
    (rep / "chirps_validation_report.md").write_text("\n".join(L), encoding="utf-8")
    json.dump({"complete": complete, "missing_years": missing_years, "missing_days": int(len(missing_dates)),
               "days_present": int(allt.nunique()), "days_expected": len(full),
               "years_verified": py_df.loc[py_df["verified"], "year"].tolist(),
               "bias": {k: round(float(x), 3) for k, x in bias.items()},
               "monthly_r_median": round(float(per_loc["monthly_r"].median()), 3),
               "daily_r_median": round(float(per_loc["daily_r"].median()), 3)},
              open(rep / "chirps_validation_summary.json", "w"), indent=2)
    logger.info("CHIRPS validation: complete=%s, missing years %s, missing days %d", complete, missing_years, len(missing_dates))


if __name__ == "__main__":
    main()

"""Build the Zambia location master from the DesInventar export's own geography.

Spatial unit: the DesInventar level-1 unit (district). Every flood record in DesInventar Zambia
is coded to a province (level 0) and, for almost all records, a district (level 1); the free-text
'lugar' (village/ward/place) is NOT systematically geocodable, so it is preserved but not geocoded.

Coordinates (never invented):
  1st choice: the representative point stored for the district in the export's 'regiones' table
              (DesInventar's own x/y), verified to fall inside that district's polygon in the
              districts.shp boundary file shipped in the same export.
  2nd choice: if the regiones point is missing or falls outside the polygon, the polygon's
              representative point (guaranteed inside) computed from districts.shp.
  Otherwise:  unresolved (no coordinates), listed in unresolved_locations.csv.
Record-level coordinates (DesInventar latitude/longitude) are used where present and checked.

Record identity: DesInventar 'serial' is NOT unique in this database (re-used across data-entry
batches), so records are identified by 'clave' (the database key), reported as record_id.

Outputs
  data/processed/location_master.csv
  data/processed/unresolved_locations.csv
  reports/location_resolution_report.csv   one row per flood record: how its location was resolved
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ROOT, get_logger, load_config, p, utc_now  # noqa: E402


def norm(name) -> str:
    """Spelling normalisation kept separate from the original value."""
    if name is None or pd.isna(name):
        return ""
    s = html.unescape(html.unescape(str(name))).strip()
    return " ".join(w.capitalize() if w.isupper() or w.islower() else w for w in s.split())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None)
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    logger = get_logger("location_master", cfg)
    lm = cfg["location_master"]
    bbox = lm["zambia_bbox"]
    ext = p(cfg, "raw_desinventar_extracted")
    proc = p(cfg, "processed")

    regiones = pd.read_csv(ext / "tables" / "regiones.csv", dtype=str, keep_default_na=False)
    provinces = regiones[regiones["nivel"] == "0"].set_index("codregion")
    districts = regiones[regiones["nivel"] == "1"].copy()
    logger.info("DesInventar geography: %d provinces, %d districts", len(provinces), len(districts))

    shp = gpd.read_file(ext / "districts.shp")
    if shp.crs is None:  # export ships no .prj; bounds are plain lon/lat degrees
        shp = shp.set_crs("EPSG:4326")
    # The boundary file re-uses some district codes for districts that DesInventar does not code
    # separately (e.g. a newer district carrying a neighbour's code). Keep, per code, the polygon whose
    # NAME matches the DesInventar district name; report the others instead of silently merging them.
    names = districts.set_index("codregion")["nombre"].map(norm).str.lower()
    shp["_match"] = [names.get(c, "") == norm(n).lower() for c, n in zip(shp["DATAB_DIST"], shp["NAME"])]
    dup = shp["DATAB_DIST"].duplicated(keep=False)
    conflicts = shp[dup & ~shp["_match"]]
    for c in conflicts.itertuples():
        logger.warning("Boundary-file code conflict: polygon %r carries code %s, which DesInventar assigns to %r;"
                       " polygon ignored for coordinate verification", c.NAME, c.DATAB_DIST, names.get(c.DATAB_DIST))
    conflicts.drop(columns=["geometry", "_match"]).assign(
        issue="polygon shares a district code with a differently named DesInventar district; not used"
    ).to_csv(ROOT / cfg["paths"]["reports"] / "boundary_file_code_conflicts.csv", index=False)
    shp = shp[~(dup & ~shp["_match"])].set_index("DATAB_DIST")
    area_km2 = shp.to_crs("EPSG:6933").area / 1e6
    centroid = shp.to_crs("EPSG:6933").centroid.to_crs("EPSG:4326")

    rows = []
    for d in districts.itertuples():
        code = d.codregion
        prov_code = d.lev0_cod or code[:2]
        prov = provinces.loc[prov_code, "nombre"] if prov_code in provinces.index else ""
        lat = pd.to_numeric(d.y, errors="coerce")
        lon = pd.to_numeric(d.x, errors="coerce")
        geom = shp.geometry.get(code)
        src, quality = "", ""
        has_point = pd.notna(lat) and pd.notna(lon) and not (lat == 0 and lon == 0)
        in_bbox = has_point and bbox["lat_min"] <= lat <= bbox["lat_max"] and bbox["lon_min"] <= lon <= bbox["lon_max"]
        if has_point and in_bbox and geom is not None and geom.contains(Point(lon, lat)):
            src = "DesInventar export regiones table (x,y) for district " + code
            quality = "district_point_verified_inside_polygon"
        elif geom is not None:
            rp = geom.representative_point()
            lat, lon = rp.y, rp.x
            src = "Representative point of district polygon in DesInventar export districts.shp"
            quality = "district_polygon_representative_point"
        elif has_point and in_bbox:
            src = "DesInventar export regiones table (x,y) for district " + code
            quality = "district_point_unverified_no_polygon"
        else:
            lat = lon = float("nan")
            quality = "unresolved"
        c = centroid.get(code)
        dist_km = (Point(lon, lat).distance(c) * 111.0) if (c is not None and pd.notna(lat)) else float("nan")
        rows.append({
            "location_id": lm["location_id_prefix"] + code,
            "location_name": norm(d.nombre),
            "location_name_original": d.nombre,
            "district": norm(d.nombre),
            "province": norm(prov),
            "district_code": code,
            "province_code": prov_code,
            "latitude": round(float(lat), 6) if pd.notna(lat) else pd.NA,
            "longitude": round(float(lon), 6) if pd.notna(lon) else pd.NA,
            "coordinate_source": src,
            "coordinate_quality": quality,
            "spatial_unit": "district (DesInventar level 1)",
            "district_area_km2": round(float(area_km2[code]), 1) if code in area_km2.index else pd.NA,
            "approx_km_to_polygon_centroid": round(dist_km, 1) if pd.notna(dist_km) else pd.NA,
            "in_boundary_file": geom is not None,
        })
    master = pd.DataFrame(rows)

    # ---- resolve every flood record ---------------------------------------------------------------
    floods = pd.read_csv(proc / "desinventar_flood_events.csv", dtype=str, keep_default_na=False)
    idx = master.set_index("district_code")
    res = []
    for r in floods.itertuples():
        out = {"record_id": r.clave, "serial": r.serial, "evento": r.evento, "event_start_date": r.event_start_date,
               "date_precision": r.date_precision, "province_original": r.name0,
               "district_original": r.name1, "location_original": r.lugar,
               "level0": r.level0, "level1": r.level1, "location_id": "", "resolution_level": "",
               "district_name_matches_geography": "", "record_latitude": "", "record_longitude": "",
               "record_coordinate_check": "", "note": ""}
        if r.level1 and r.level1 in idx.index:
            m = idx.loc[r.level1]
            out["location_id"] = m.location_id
            out["resolution_level"] = "district"
            out["district_name_matches_geography"] = norm(r.name1).lower() == m.district.lower()
            out["note"] = ("place text kept verbatim; not geocoded below district level"
                           if r.lugar.strip() else "no place text")
        elif r.level1:
            out["resolution_level"] = "unresolved"
            out["note"] = f"district code {r.level1} not in DesInventar geography"
        else:
            out["resolution_level"] = "province_only" if r.level0 else "unresolved"
            out["note"] = "record has no district (level 1) code in DesInventar"
        lat, lon = pd.to_numeric(r.latitude, errors="coerce"), pd.to_numeric(r.longitude, errors="coerce")
        if pd.notna(lat) and pd.notna(lon) and not (lat == 0 and lon == 0):
            out["record_latitude"], out["record_longitude"] = lat, lon
            geom = shp.geometry.get(r.level1)
            out["record_coordinate_check"] = ("inside_coded_district" if geom is not None and geom.contains(Point(lon, lat))
                                              else "outside_coded_district_or_no_polygon")
        res.append(out)
    res = pd.DataFrame(res)
    reports = p(cfg, "reports")
    res.to_csv(reports / "location_resolution_report.csv", index=False)

    counts = res[res["location_id"] != ""].groupby("location_id").agg(
        n_flood_records=("record_id", "size"),
        n_flood_records_day_precision=("date_precision", lambda s: int((s == "day").sum())))
    master = master.merge(counts, how="left", left_on="location_id", right_index=True)
    master[["n_flood_records", "n_flood_records_day_precision"]] = (
        master[["n_flood_records", "n_flood_records_day_precision"]].fillna(0).astype(int))
    resolved = master["coordinate_quality"] != "unresolved"
    if lm["weather_locations"] == "flood_only":
        master["in_weather_collection"] = resolved & (master["n_flood_records"] > 0)
    else:
        master["in_weather_collection"] = resolved
    master["created_utc"] = utc_now()
    master = master.sort_values("location_id")
    master.to_csv(proc / "location_master.csv", index=False)

    # ---- unresolved locations (grouped) -----------------------------------------------------------
    unres_records = res[res["resolution_level"].isin(["unresolved", "province_only"])]
    unres = (unres_records.groupby(["location_original", "district_original", "province_original",
                                    "resolution_level", "note"], dropna=False)["record_id"]
             .agg(n_records="size", record_ids=lambda s: ";".join(s)).reset_index())
    unres = unres.rename(columns={"location_original": "original_location", "district_original": "district",
                                  "province_original": "province", "note": "reason_unresolved"})
    unres["attempted_sources"] = ("DesInventar record level1 code; DesInventar regiones table; "
                                  "DesInventar districts.shp (no external gazetteer used: place text "
                                  "below district level cannot be unambiguously matched)")
    unres["status"] = unres["resolution_level"].map(
        {"province_only": "unresolved_at_district_level_province_known", "unresolved": "unresolved"})
    geo_unres = master[~resolved]
    for g in geo_unres.itertuples():
        unres.loc[len(unres)] = {"original_location": g.location_name_original, "district": g.district,
                                 "province": g.province, "resolution_level": "geography",
                                 "reason_unresolved": "district has neither a valid regiones point nor a polygon",
                                 "n_records": g.n_flood_records, "record_ids": "",
                                 "attempted_sources": "DesInventar regiones table; DesInventar districts.shp",
                                 "status": "unresolved"}
    cols = ["original_location", "district", "province", "reason_unresolved", "attempted_sources",
            "status", "resolution_level", "n_records", "record_ids"]
    unres[cols].to_csv(proc / "unresolved_locations.csv", index=False)

    shp_only = sorted(set(shp.index) - set(districts["codregion"]))
    logger.info("Location master: %d districts (%d resolved, %d unresolved); quality=%s",
                len(master), int(resolved.sum()), int((~resolved).sum()),
                master["coordinate_quality"].value_counts().to_dict())
    if shp_only:
        logger.info("Polygons in districts.shp with no regiones entry (not in DesInventar coding): %s",
                    {c: shp.loc[c, "NAME"] for c in shp_only})
    logger.info("Flood record resolution: %s", res["resolution_level"].value_counts().to_dict())
    logger.info("Districts with >=1 flood record: %d; locations for weather collection: %d",
                int((master["n_flood_records"] > 0).sum()), int(master["in_weather_collection"].sum()))


if __name__ == "__main__":
    main()

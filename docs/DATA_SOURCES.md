# FloodShield-Zambia — Data Sources and Provenance (Stage 1)

This document covers the **Stage 1 raw-data pipeline** (`scripts/`, `config/data_sources.yaml`, `data/`).
It supersedes nothing in the older `docs/DATA-SOURCES.md`, which describes the previous pipeline. No dataset,
label, model or metric from that earlier pipeline is used here.

Retrieval date for all sources below: **2026-10-06** (exact timestamps are stored with every raw file).

| Source | Role | Geographic scope of the *product* | What was taken |
|---|---|---|---|
| DesInventar Zambia | Flood events | **Zambia-specific** national disaster database | Full national export |
| NASA POWER | Daily weather | **Global** gridded product | 101 Zambian district points |
| CHIRPS v3.0 | Daily rainfall | **Quasi-global** (60°N–60°S) gridded product | Zambia bounding-box window |

---

## 1. DesInventar Sendai — Zambia

| Item | Detail |
|---|---|
| Source name | DesInventar Sendai disaster loss database, Zambia (UNDRR; data entered by Zambian national authorities — the records cite the Disaster Management and Mitigation Unit (DMMU) and provincial coordinators) |
| Official URLs | Country profile: https://www.desinventar.net/DesInventar/country_profile.jsp?countrycode=zmb&lang=EN · Database: https://www.desinventar.net/DesInventar/ · Downloads: https://www.desinventar.net/download.html |
| File retrieved | https://www.desinventar.net/DesInventar/download/DI_export_zmb.zip (the official full-database export linked from the download page) |
| Data type | Event-level disaster records ("datacards") with location, date, cause, comments and loss/consequence fields; plus the database's own geography (province/district codes, representative points, boundary shapefiles) |
| Geographic coverage | Zambia: 10 provinces, 101 districts (DesInventar level 0 / level 1) |
| Temporal coverage | Flood records 2000–2026 (exact-day dates 2000-04-13 → 2026-01-23); all hazard types 2,239 records |
| Variables collected | All fields of all records (kept verbatim). Flood subset = event types `FLOOD` and `FLASH FLOODS` |
| Access method | Single HTTPS download of the public export ZIP (no credentials). `scripts/collect_desinventar.py` |
| Raw storage | `data/raw/desinventar/original/DI_export_zmb.zip` (untouched) + `.provenance.json` (URL, timestamp, HTTP headers, size, SHA-256). Unzipped members in `data/raw/desinventar/extracted/` (XML, `districts.shp`, `Provinces.shp`) |
| Processing performed | (1) Every XML table written to `extracted/tables/*.csv` with values unchanged. (2) Records joined to their extension fields on `clave`. (3) Flood subset written to `data/processed/desinventar_flood_events.csv` with *added* columns: parsed start date, date precision, date-quality flag, end date from `duracion` only where stated. (4) Event-type inventory and keyword review list. Nothing is corrected, imputed or deleted. |
| Known limitations | 37% of flood records give only a year (no month/day); reporting intensity varies strongly by year (data-entry campaigns, e.g. 2009–2014); `serial` numbers are re-used (use `clave`); only 1 flood record has its own coordinates; place text below district level is free text; some non-flood categories (STORM, HAILSTORM, ANIMAL INCIDENT…) contain records describing flood damage; the shipped `districts.shp` has no `.prj` file (coordinates are plain WGS84 degrees) and two polygons re-use another district's code (Mulobezi→1001, Chikankanta→0911). Consequence fields are post-event and must never be predictors. |
| Citation | UNDRR (2026). *DesInventar Sendai — Zambia national disaster loss database.* United Nations Office for Disaster Risk Reduction. https://www.desinventar.net/ (accessed 2026-10-06). |

## 2. NASA POWER — Daily API

| Item | Detail |
|---|---|
| Source name | NASA Prediction Of Worldwide Energy Resources (POWER), NASA Langley Research Center |
| Official URLs | https://power.larc.nasa.gov/ · Daily API docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/ · Endpoint used: https://power.larc.nasa.gov/api/temporal/daily/point |
| Data type | Daily gridded meteorology (MERRA-2 / GEOS-IT based; the API reports its sources as GEOSIT, MERRA2, POWER) sampled at a point |
| Geographic coverage | **Global product.** Extracted for the 101 Zambian district points in `data/processed/location_master.csv` |
| Temporal coverage | 1999-04-14 → 2026-01-30 (the collection window; see below) |
| Variables collected | `PRECTOTCORR`, `T2M`, `T2M_MAX`, `T2M_MIN`, `RH2M`, `WS10M` — community `AG`, time standard `LST`, API v2.10.0 |
| Access method | Automated HTTPS GET, one request per location covering the whole window (the API supports multi-decade daily ranges), sequential with a 1 s pause, exponential back-off retries. `scripts/download_nasa_power.py` |
| Raw storage | `data/raw/nasa_power/daily_weather/<location_id>/<location_id>__<start>_<end>.json` (verbatim response) + `.meta.json` (full request URL, parameters, HTTP status, timestamp, SHA-256, API header/messages/parameter metadata) |
| Processing performed | Flattened into `data/raw/nasa_power/nasa_power_daily.csv` (long format). The only transformation: fill value −999 written as empty (missing). The CSV can be rebuilt from the JSON at any time (`--rebuild-only`). |
| Known limitations | Coarse native grid (~0.5° × 0.625° for MERRA-2 meteorology): 8 groups of neighbouring districts receive identical series; reanalysis precipitation is a model product, not a gauge observation, and can produce extreme values (2 days > 300 mm flagged); dates are local solar time. |
| Citation | NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science/Applied Science Program. Data obtained from the POWER Project's Daily API v2.10.0 on 2026-10-06. https://power.larc.nasa.gov/ |

## 3. CHIRPS v3.0 — daily

| Item | Detail |
|---|---|
| Source name | Climate Hazards Center InfraRed Precipitation with Stations, version 3.0 (Climate Hazards Center, UC Santa Barbara) |
| Official URLs | https://www.chc.ucsb.edu/data/chirps3 · Data root: https://data.chc.ucsb.edu/products/CHIRPS/v3.0/ · Files used: `daily/final/rnl/cogs/<YYYY>/chirps-v3.0.rnl.<YYYY.MM.DD>.cog` |
| Data type | Gridded daily precipitation, 0.05°, satellite + station blend. Daily values are CHIRPS v3 pentads disaggregated to days |
| Geographic coverage | **Quasi-global product (60°N–60°S).** Extracted window lon 21.9–33.8°E, lat 18.2–8.1°S (238 × 202 pixels), which contains all of Zambia |
| Temporal coverage | 1999-04-14 → 2026-01-30 (same window as NASA POWER) |
| Variables collected | `precip` (mm/day; unit from the official CHIRPS v3.0 NetCDF metadata) |
| Variant choice | `final` stream, **`rnl`** disaggregation (daily ratios from ERA5). The alternative `sat` (IMERG-based) starts only in 1998 and the CHC readme notes either may be preferable depending on the application; `rnl` was chosen because it covers the whole window with one consistent method. Configurable in `config/data_sources.yaml` (`chirps.variant`). |
| Access method | Cloud-Optimised GeoTIFF window reads over HTTPS range requests (only the ~4 tiles covering Zambia per day), 8 parallel workers, retries with back-off. This avoids downloading 17 MB global GeoTIFFs per day or 3.6 GB global NetCDFs per year. `scripts/download_chirps.py` |
| Raw storage | `data/raw/chirps/daily_rainfall/chirps-v3.0.rnl.zambia.<YYYY>.nc` — pixel values copied unchanged, per-day source URL and retrieval timestamp stored inside; consolidation is verified bit-for-bit before temporary per-day clips are removed. `data/raw/chirps/chirps_manifest.csv` logs every day |
| Processing performed | None to the values. Separately, `data/processed/chirps_daily_at_locations.csv` holds the nearest-pixel value at each location point (no interpolation, no aggregation). No 3/7/14-day totals were computed. |
| Known limitations | Daily values are a disaggregation of pentadal totals (day-to-day timing comes from ERA5, not directly from satellite/stations); a single pixel represents a district point; station density in Zambia affects quality; `final` data lag ~3 weeks behind real time. |
| Citation | Funk, C., Peterson, P., Landsfeld, M., et al. (2015). The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes. *Scientific Data* 2, 150066. https://doi.org/10.1038/sdata.2015.66 — and Climate Hazards Center (2025), *CHIRPS v3.0*, UC Santa Barbara, https://www.chc.ucsb.edu/data/chirps3 (accessed 2026-10-06). |

---

## Derived geographic information

`data/processed/location_master.csv` — 101 districts. Coordinates come **only** from the DesInventar export:
the district point in its `regiones` table, verified to lie inside the district polygon in `districts.shp`
(96 districts); for the 5 whose point lies outside the polygon, the polygon's representative point (always
inside) from the same shapefile. No external geocoder and no invented coordinates. Free-text sub-district
places are not geocoded. `data/processed/unresolved_locations.csv` lists the 4 flood records that have only a
province.

## Collection window

`data/processed/collection_window.json`: start = earliest valid flood date (2000-04-13) − 365 days;
end = latest valid flood date (2026-01-23) + 7 days. Configurable (`collection_window` in the config).

## Reproducing Stage 1

```bash
python scripts/collect_desinventar.py
python scripts/build_location_master.py
python scripts/download_nasa_power.py
python scripts/download_chirps.py
python scripts/validate_raw_data.py
python scripts/generate_data_report.py
```

Every downloader is restartable: it checks what is already on disk and requests only missing
locations/periods/days. Failures are appended to `reports/failed_requests.csv` and the run continues.
Logs go to `reports/collection.log`.

---

# Stage 2 additions (retrieved 2026-10-07)

| Source | Role (class) | Geographic scope of the *product* | What was taken |
|---|---|---|---|
| HydroSHEDS v1 | Static terrain/drainage (A) | Global; Africa archives | DEM 15″, HydroRIVERS, HydroBASINS L4/L6 → Zambia subset |
| ESA WorldCover 2021 v200 | Static land cover (A opt./context) | Global | Tiles intersecting Zambia, read at the 1/4 internal overview (~40 m) |
| NASA POWER soil wetness | Optional experiment (A opt.) | Global | GWETTOP/GWETROOT/GWETPROF at the 101 district points |
| NOAA CPC ONI & Niño 3.4; NOAA PSL DMI; BoM weekly IOD | Seasonal context (A opt.) | Ocean-basin indices | Full published series |
| WorldPop wpic1km (people per pixel, not UN-adjusted) | Exposure (C) | Country product (Zambia) | Yearly 1 km grids 2000–2020 |
| Dartmouth Flood Observatory archive | Validation (B) | Global event list | Spreadsheet; Zambia rows extracted |

## 4. HydroSHEDS v1

| Item | Detail |
|---|---|
| Source name | HydroSHEDS — Hydrological data and maps based on SHuttle Elevation Derivatives at multiple Scales (WWF, McGill University, USGS) |
| Official URLs | https://www.hydrosheds.org/ · https://www.hydrosheds.org/hydrosheds-core-downloads · https://www.hydrosheds.org/products |
| Files | `hyd_af_dem_15s.zip` (void-filled DEM, 15″), `HydroRIVERS_v10_af_shp.zip`, `hybas_af_lev04_v1c.zip`, `hybas_af_lev06_v1c.zip` from https://data.hydrosheds.org/file/… |
| Versions | **HydroSHEDS v1** — the DEM archive contains `HydroSHEDS_TechDoc_v1_4.pdf` ("Data Version 1.1, Technical Documentation Version 1.4, April 2022"); HydroRIVERS v1.0; HydroBASINS v1c. v2 not used. DEM: void-filled, int16, no-data 32767, metres above the EGM96 geoid, WGS84 |
| Coverage | Global products; Africa archives downloaded; Zambia window (bbox + 0.25°) subset |
| Variables | elevation (m); river reaches with `UPLAND_SKM` (upstream area, km²), `DIS_AV_CMS` (modelled long-term mean discharge, m³/s); basin polygons with `HYBAS_ID`, `MAIN_BAS`, `UP_AREA` |
| Access | `scripts/download_hydrosheds.py` — resumable HTTPS download; original ZIPs kept with SHA-256 provenance. Integrity: each archive's size equals the server's Content-Length (DEM 170,986,111 B; HydroRIVERS 107,873,468 B; L4 5,945,213 B; L6 17,945,918 B) and ZIP CRC checks pass |
| Processing | Window subset (values unchanged); slope derived from the DEM (`data/processed/derived_rasters/slope_15s_zambia.tif`); district/point statistics in `data/processed/district_terrain_hydrology.csv` (`scripts/extract_district_environment.py`) |
| Not collected | Flow-direction and flow-accumulation rasters: HydroRIVERS already holds the upstream area derived from them |
| Limitations | SRTM-based (~2000) elevation; 15″ (~460 m) smooths small channels; `DIS_AV_CMS` is modelled, not observed; static |
| Citation | Lehner, B., Verdin, K., Jarvis, A. (2008). New global hydrography derived from spaceborne elevation data. *Eos* 89(10): 93–94. Lehner, B., Grill, G. (2013). Global river hydrography and network routing. *Hydrological Processes* 27(15): 2171–2186. |

## 5. ESA WorldCover 2021 v200

| Item | Detail |
|---|---|
| Official URLs | https://esa-worldcover.org/en/data-access · tiles: `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_<tile>_Map.tif` |
| Coverage / time | Global 10 m land cover for calendar year 2021 (one snapshot) |
| Variables | 11 classes: tree cover, shrubland, grassland, cropland, built-up, bare/sparse, snow/ice, permanent water, herbaceous wetland, mangroves, moss/lichen |
| Access | `scripts/download_worldcover.py` — HTTP range reads of each tile's internal 1/4 overview (~40 m); class codes kept as published |
| Processing | District % per class (cells weighted by cos latitude) and class at the location point → `data/processed/district_landcover.csv` |
| Limitations | 2021 snapshot applied to a 1999–2026 history (static/slow-changing; optional); 40 m overview within 0.14–0.52 percentage points of 10 m at six contrasting test sites (`reports/worldcover_overview_bias_test.csv`) — a check of the reading method, not of WorldCover's accuracy; less reliable for classes < 1 % |
| Licence / citation | CC BY 4.0. Zanaga, D., et al. (2022). *ESA WorldCover 10 m 2021 v200*. https://doi.org/10.5281/zenodo.7254221 |

## 6. NASA POWER soil wetness (optional experiment)

Same API, provenance chain and storage pattern as §2 (`data/raw/nasa_power/daily_soil_moisture/`, flattened to
`data/raw/nasa_power/nasa_power_daily_soil_moisture.csv`). Parameters: `GWETTOP` (surface, 0–5 cm), `GWETROOT`
(root zone, 0–100 cm), `GWETPROF` (whole profile) — soil wetness as a fraction 0–1 (MERRA-2). Collected with
`python scripts/download_nasa_power.py --dataset soil`. ERA5-Land (0.1°) was evaluated but needs a Copernicus
CDS account; see `data/raw/era5_land/README.md`.

## 7. Climate indices

| Index | Source / URL | Resolution | Notes |
|---|---|---|---|
| ONI | NOAA CPC — https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt | 3-month running mean, monthly step, 1950– | ERSST.v5; season centred on the month |
| Niño 3.4 | NOAA CPC — https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii | Monthly, 1950– | Anomaly vs 1991–2020 |
| DMI | NOAA PSL — https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data | Monthly, 1870– | HadISST1.1; latest months marked preliminary by PSL |
| IOD (weekly) | Australian Bureau of Meteorology — https://www.bom.gov.au/clim_data/IDCK000072/iod_1.txt (index page https://www.bom.gov.au/climate/enso/indices.shtml) | Weekly, 2008– | Too short to be the sole IOD source; kept as context |

Raw text files in `data/raw/climate_indices/` (with provenance); tidy tables `data/processed/climate_indices_monthly.csv`
and `climate_iod_weekly_bom.csv` (`scripts/download_climate_indices.py`). These are basin-scale indices, not local
weather; the lag rules are in `docs/DATA_REQUIREMENTS_MATRIX.md` §4.

## 8. WorldPop

| Item | Detail |
|---|---|
| Official URLs | https://www.worldpop.org/ · API https://www.worldpop.org/rest/data/pop/wpic1km?iso3=ZMB |
| Product | "Unconstrained individual countries 2000-2020 (1km resolution)": estimated people per ~1 km cell (`zmb_ppp_<year>_1km_Aggregated.tif`), not UN-adjusted, one GeoTIFF per year |
| Access | `scripts/download_worldpop.py`; the API record (title, DOI, citation, licence) is saved with each file's provenance |
| Processing | District totals (cells whose centre is inside the polygon) and density → `data/processed/exposure/worldpop_district_exposure.csv` (separate exposure folder) |
| Role | **Exposure layer only** — not an occurrence predictor |
| Limitations | Modelled (census + covariates), not counted; 1 km cells split by district borders are assigned by centre |
| Licence / citation | Licence: https://hub.worldpop.org/data/licence.txt (CC BY 4.0). WorldPop (www.worldpop.org — School of Geography and Environmental Science, University of Southampton; Department of Geography and Geosciences, University of Louisville; Département de Géographie, Université de Namur) and CIESIN, Columbia University (2018). Global High Resolution Population Denominators Project. https://dx.doi.org/10.5258/SOTON/WP00670 |

## 9. Dartmouth Flood Observatory archive

Global Active Archive of Large Flood Events (G.R. Brakenridge, University of Colorado), https://floodobservatory.colorado.edu/ —
`FloodArchive.xlsx`, event list 1985– with start/end dates, centroid and affected area. Validation only.
**Status: not collected** — the server refused connections (port 443) throughout 6–7 Oct 2026 while all other
sources were reachable. `scripts/download_flood_observations.py` is ready to run when access returns.
Classification: OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL. Citation: Brakenridge, G.R. *Global Active Archive of Large Flood Events*,
Dartmouth Flood Observatory, University of Colorado.

## 10. Evaluated, not collected

River gauges (GRDC/WARMA/ZRA): `data/raw/hydrology/README.md`. ERA5-Land: `data/raw/era5_land/README.md`.
Sentinel-1, Global Flood Database, Copernicus EMS: `data/raw/satellite_flood/README.md`.

## Reproducing Stage 2

```bash
python scripts/download_hydrosheds.py
python scripts/download_worldcover.py
python scripts/download_nasa_power.py --dataset soil
python scripts/download_climate_indices.py
python scripts/download_worldpop.py
python scripts/download_flood_observations.py
python scripts/extract_district_environment.py
python scripts/validate_chirps.py
python scripts/validate_environmental_data.py
python scripts/audit_data.py
```

## Stage 2 QC additions

- `scripts/assess_flood_date_reliability.py` → `data/processed/desinventar_flood_date_reliability.csv`,
  `reports/flood_date_reliability.md`: flags whether each DesInventar date is plausibly the flood onset (season,
  same-date batches, administrative text; rainfall is not used).
- `scripts/test_worldcover_overview.py` → `reports/worldcover_overview_bias_test.csv`.
- `scripts/validate_chirps.py` → per-year 101-location verification, bias/extreme statistics, source re-reads of
  grid extremes (`reports/chirps_extreme_events.csv`), NASA POWER anomaly investigation.
- WorldPop exposure moved to `data/processed/exposure/worldpop_district_exposure.csv` (fields: location_id,
  population_year, population, population_density_per_km2, source, version with DOI 10.5258/SOTON/WP00670).

---

# Final Stage 2 additions (retrieved 2026-10-07)

## 11. GloFAS — Global Flood Awareness System (Copernicus Emergency Management Service)

| Item | Detail |
|---|---|
| Products examined (official EWDS catalogue, read via its public API) | `cems-glofas-historical` (DOI 10.24381/cds.a4fdd6b9): LISFLOOD forced by ERA5, daily, 1979 → 2026-10-04, versions 4.0 (operational) and 5.0 (pre-operational). `cems-glofas-reforecast` (DOI 10.24381/cds.2d78664e): ECMWF-ENS reforecasts, twice-weekly issues, leads 24–1104 h; v4.0 covers 2003-03 → 2023-11. `cems-glofas-forecast` (DOI 10.24381/cds.ff1aef77): operational ensemble forecasts 2019-11 → present, leads 24–720 h, control + perturbed members; system version changes over the archive (v2.1, v3.1, operational) |
| Official URLs | https://ewds.climate.copernicus.eu/datasets/cems-glofas-historical · https://ewds.climate.copernicus.eu/datasets/cems-glofas-reforecast · https://ewds.climate.copernicus.eu/datasets/cems-glofas-forecast |
| Variables (historical v4.0) | `average_river_discharge_in_the_last_24_hours` (time_mean), `runoff_water_equivalent` (time_mean), `soil_wetness_index` (instantaneous, root zone), snow depth water equivalent (irrelevant for Zambia); ancillary upstream area and elevation |
| Resolution / grid | 0.05° (3 arc-min) global grid, WGS84; daily |
| Access | EWDS API only; requires a personal ECMWF account, a personal access token in `~/.cdsapirc` and acceptance of the CEMS-FLOODS licence. **Not collected**: no credentials exist on this machine and creating accounts is the researcher's action. `scripts/download_glofas.py` is ready (requests validated against the official constraints file; resumable; provenance per file) |
| Version decision | v4.0 for historical **and** reforecasts (same model version for training-period reanalysis and forecast experiments); v5.0 is pre-operational |
| Spatial context | Area N −7.85, W 21.65, S −18.45, E 34.05 (Zambia + 0.25°). Discharge is routed, so a cell's value already integrates all upstream runoff (including Angola/DRC); cropping does not remove upstream information |
| Extraction | Discharge at each district's main-river cell (largest upstream area), nearest-significant-river cell as sensitivity; runoff and soil wetness as district means (`reports/glofas_extraction_method_comparison.md`) |

### GloFAS v4 river-network static maps (collected)

| Item | Detail |
|---|---|
| Source | European Commission JRC — "LISFLOOD static and parameter maps for GloFAS", dataset version 1.1.1 (for OS-LISFLOOD v4.x = GloFAS v4.0); PID http://data.europa.eu/89h/68050d73-9c06-499c-a441-dc5053cb0c86 |
| URL | https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/LISFLOOD_static_and_parameter_maps_for_GloFAS/v1.1.1_OS-LISFLOOD-v4.x/Catchments_morphology_and_river_network/ |
| Files | `upArea_repaired.nc` (upstream area, m²), `ldd_repaired.nc` (local drain direction), `chan_Global_03min.nc` (channel mask); global 0.05°; Zambia subsets with values unchanged |
| Licence / citation | CC BY 4.0. Choulga, M., Beck, H., Moschini, F., Mazzetti, C., Disperati, J., Grimaldi, S., Salamon, P., Prudhomme, C. (2023): LISFLOOD static and parameter maps for GloFAS. EC JRC [Dataset] |
| Check | Upstream area at the Zambezi near Victoria Falls 517,768 km² (published ≈ 507,000 km²); Kafue near Kafue town 152,789 km² (basin ≈ 155,000 km²) |

## 12. JRC Global Surface Water (collected, optional static)

| Item | Detail |
|---|---|
| Source | EC JRC / Google — Global Surface Water Explorer, version 1.4 (2021), `occurrence` layer; https://global-surface-water.appspot.com/download |
| Files | 4 tiles (`occurrence_{20E_0N,30E_0N,20E_10S,30E_10S}v1_4_2021.tif`, 30 m) from Google Cloud Storage |
| Variable | Share of valid Landsat observations 1984–2021 in which the cell was water (%) |
| Processing | District % of area ever water, intermittent (1–74 %) and permanent (≥75 %), mean occurrence → `data/processed/environmental/district_surface_water.csv` (`scripts/download_global_surface_water.py`) |
| Limitation | Aggregate includes years after many events (static susceptibility only) |
| Citation | Pekel, J.-F., Cottam, A., Gorelick, N., Belward, A.S. (2016). High-resolution mapping of global surface water and its long-term changes. *Nature* 540, 418–422 |

## 13. Evaluated, not collected (with reason)

| Candidate | Access checked 2026-10-07 | What it would add | Decision |
|---|---|---|---|
| TAMSAT v3.1 daily rainfall | open (no login) | a third rainfall estimate | OPTIONAL — not collected (two independent rainfall sources already) |
| NASA GPM IMERG | Earthdata login | third rainfall estimate | NOT COLLECTED (login; redundant) |
| ESA CCI soil moisture | open (CEDA) | observation-based soil moisture, 0.25° | OPTIONAL — not collected (coarse, gaps under woodland; GloFAS SWI + POWER cover the need) |
| NOAA GEFSv12 reforecasts | open (AWS) | archived weather forecasts 2000–2019 | OPTIONAL — not collected (GloFAS reforecasts preferred: hydrological, same model family) |
| GloFAS / ISRIC soil hydraulic properties | open | static infiltration capacity | OPTIONAL — not collected (static; partly captured by terrain/land cover) |
| ERA5 / ERA5-Land | CDS account | reanalysis rainfall/soil moisture | NOT COLLECTED (account; GloFAS already ERA5-forced) |
| Sentinel-1 / CEMS Global Flood Monitoring / Global Flood Database | accounts / Earth Engine | observed flood extent (post-event) | VALIDATION — future work |
| DFO archive | server unreachable all of 6–7 Oct | independent event dates | VALIDATION — not collected |
| GRDC gauges | portal unreachable; request-only | observed discharge | VALIDATION — data access limited |

## Reproducing the final additions

```bash
python scripts/download_glofas_static.py
python scripts/build_glofas_extraction_points.py
python scripts/download_global_surface_water.py
python scripts/download_glofas.py --product historical      # needs the researcher's ~/.cdsapirc
python scripts/download_glofas.py --product reforecast      # optional forecast experiment
python scripts/extract_glofas.py
python scripts/assess_flood_date_reliability.py
python scripts/build_leakage_register.py
python scripts/check_forecast_horizon_readiness.py
python scripts/second_audit.py
python scripts/build_quality_scorecard.py
python scripts/build_final_inventory.py
```

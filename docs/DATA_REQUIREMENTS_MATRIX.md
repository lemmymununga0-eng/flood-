# FloodShield-Zambia — Data Requirements Matrix (Stage 2)

Research question: *Can historical meteorological and environmental conditions be used to estimate the
probability that a flood event will occur at a Zambian location within the next 7 days?*

Spatial unit: the 101 DesInventar districts (`data/processed/location_master.csv`). Time unit: day.
Status values are those verified on disk in `docs/DATA_AUDIT_REPORT.md` — a script existing is never
counted as a dataset being complete.

## 1. Three kinds of data — kept separate

| Class | Meaning | May enter the 7-day occurrence model as a feature? |
|---|---|---|
| **A. CORE PREDICTIVE** | Conditions known on or before prediction date *t* that plausibly drive flooding in (t, t+7] | Yes |
| **B. VALIDATION / CONTEXT** | Used to build/check labels, explain, compare or sanity-check | No (labels come from DesInventar; the rest only validates) |
| **C. RISK / EXPOSURE** | Who/what would be hit if a flood occurs | **No** — combined *after* the occurrence probability, e.g. risk = P(flood) × exposure |

Optional experiments (marked *opt.*) are class-A candidates to be tested in Stage 3 against the core set,
not included by default.

**Classification (QC):** CORE candidates = DesInventar (labels), NASA POWER, CHIRPS, HydroSHEDS terrain/hydrology ·
OPTIONAL = soil wetness, climate indices, land cover · EXPOSURE (separate) = WorldPop · VALIDATION = satellite/DFO
flood observations, river gauges (if ever obtained). Rationale: `docs/METHODOLOGICAL_DATA_DECISIONS.md`.

## 2a. Research-requirement matrix (Stage 2 final)

Forecast horizons: H+1, H+3, H+7 (primary), H+14, H+30. "Status" = verified on disk (`docs/DATA_AUDIT_REPORT.md`,
`reports/second_audit_report.md`).

| Research requirement | Dataset | Variable | Why needed | Temporal coverage | Spatial coverage | Forecast horizon supported | Leakage risk | Status | Validation status | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| Know when/where floods happened (labels) | DesInventar Zambia | event type, date, date precision, district, date-confidence class | Defines the future target | 2000–2026 (exact day 2000-04-13 → 2026-01-23) | 82 of 101 districts with ≥1 event | H+3…H+30 (H+1 not defensible: day-level date error) | Consequence fields = POST-EVENT | COMPLETE | 2nd audit: raw XML = processed (0 mismatches) | LABEL SOURCE; positives = HIGH-CONFIDENCE dates (82 district-days), UNCERTAIN as sensitivity; never negatives from uncertain/unlikely |
| Rain that causes floods | NASA POWER | PRECTOTCORR | Main flood driver | 1999-04-14 → 2026-01-30, daily | 101 points | all (days ≤ t) | LEAKAGE if after t | COMPLETE | 2nd audit: CSV = raw JSON; lag-0 alignment with CHIRPS | CORE |
| Rain that causes floods (independent) | CHIRPS v3.0 | precip | Second, gauge-blended source; robustness | same, daily | 101 points (0.05° grid kept) | all (days ≤ t) | LEAKAGE if after t | COMPLETE | 2nd audit: recomputed from NetCDF; 5 days re-read from CHC | CORE (one primary + one sensitivity, decided in Stage 3) |
| Atmospheric state | NASA POWER | T2M, T2M_MAX, T2M_MIN, RH2M, WS10M | Evaporation/convection context | same | 101 points | all | LEAKAGE if after t | COMPLETE | 2nd audit | CORE |
| River/hydrological state | GloFAS v4.0 historical | river discharge (main-river pixel), runoff & soil wetness (district mean) | Floods are river responses; discharge integrates upstream rain (incl. Angola/DRC) | 1979–2026 (product), daily | Zambia window, river-network pixels defined | all (days ≤ t) | Observed discharge after t = LEAKAGE | **DEFERRED** (researcher decision 2026-10-08; no EWDS credentials) | download script dry-run validated against official constraints | DEFERRED (was CORE); scripts ready |
| Honest forecast information | GloFAS v4.0 reforecasts | ensemble discharge at leads 1–46 d | Lets a historical experiment use only forecasts issued ≤ t | issues 2003-03 → 2023-11, twice weekly | Zambia window | H+1…H+30 (lead ≤ 46 d) | FORECAST VARIABLE: issue date must be ≤ t | DEFERRED with GloFAS historical | script dry-run validated | DEFERRED (optional forecast experiment) |
| Where water collects | HydroSHEDS v1 | elevation stats, slope, flat fraction, river distance (point + district-wide), max upstream area, river density | Terrain controls flood susceptibility | static | 101 districts | all | none | COMPLETE | 2nd audit: subset = original ZIP window | CORE (static) |
| River network for extraction | GloFAS static maps v1.1.1 | upArea, ldd, chan | Choose river pixels for discharge | static | 0.05° Zambia window | all | none | see audit | upArea checked vs known basins (Zambezi at Victoria Falls 517,768 km² vs ~507,000 published) | CORE support |
| Antecedent wetness | NASA POWER | GWETTOP, GWETROOT, GWETPROF | Wet soils turn rain into runoff | 1999-04-14 → 2026-01-30 | 101 points | all (days ≤ t) | LEAKAGE if after t | COMPLETE | 2nd audit | OPTIONAL (Spearman 0.83–0.90 with 30–90-day rainfall) |
| Observed floodplains | JRC Global Surface Water | occurrence → % intermittent / permanent water per district | Empirical flood-proneness | 1984–2021 aggregate | 101 districts | all | mild (aggregate includes later years) | see audit | 2nd audit | OPTIONAL (static) |
| Land surface | ESA WorldCover 2021 | % built-up, cropland, tree, grass, water, wetland | Runoff/exposure context | 2021 snapshot | 101 districts | all | mild anachronism | COMPLETE | 6-site overview test; 2nd audit | OPTIONAL (static) |
| Seasonal climate state | NOAA CPC/PSL, BoM | ONI, Niño 3.4, DMI | ENSO/IOD modulate wet seasons | 1950/1870 → 2026, monthly | one value nationally | H+14, H+30 most relevant | POTENTIAL LEAKAGE unless lagged | COMPLETE | 2nd audit: tidy = raw text | OPTIONAL (lagged) |
| Who would be affected | WorldPop | population, density | Impact ranking after P(flood) | 2000–2020 yearly | 101 districts | — | EXPOSURE ONLY | COMPLETE | 2nd audit | EXPOSURE (separate folder) |
| Independent event check | DFO archive | event dates | Validate labels | 1985– | events | — | POST-EVENT | NOT COLLECTED (server unreachable) | — | VALIDATION, optional |
| Observed river flow | GRDC gauges | discharge | Validate hydrology | — | few stations | — | low | NOT COLLECTED (request-only) | — | VALIDATION, optional / data access limited |

Evaluated and not collected (would add little beyond the set above): TAMSAT and NASA IMERG rainfall (a third
rainfall product; IMERG also needs Earthdata login), ESA CCI / SMAP satellite soil moisture (0.25° or 2015-onward;
GloFAS soil wetness + POWER cover the need), NOAA GEFSv12 reforecasts (weather forecast archive 2000–2019 on AWS;
GloFAS reforecasts are the hydrological equivalent and preferred), GloFAS/SoilGrids soil hydraulic properties
(static, partly captured by terrain/land cover), ERA5-Land (CDS account), Sentinel-1 / Global Flood Database /
CEMS flood maps (post-event, account-gated). Details: `docs/DATA_COLLECTION_FINAL_COMPLETION_REPORT.md` §4.

## 2. Matrix

| # | Dataset | Source | Purpose | Required? | Class | Temporal coverage | Spatial coverage | Resolution | Main variables | Join method to the 101 districts | Core model? | Validation? | Exposure? | Action |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | DesInventar Zambia | UNDRR DesInventar (Zambia DMMU data) | Flood events → future target; audit | **Required** | B (label source) | 2000–2026 (exact day: 2000-04-13 → 2026-01-23) | Zambia, district-coded | Event records | event type, date, district, place, consequences | District code (`level1`) → `location_id`; 4 province-only records unresolved | No (target only) | Yes | Consequence fields are historical impact, audit only | None for collection; decisions in §5 |
| 2 | NASA POWER daily | NASA LaRC POWER API v2.10 | Daily weather | **Required** | A | 1999-04-14 → 2026-01-30 | 101 district points | ~0.5° × 0.625° (MERRA-2) | PRECTOTCORR, T2M, T2M_MAX, T2M_MIN, RH2M, WS10M | Point at location-master coordinate | **Yes** | — | — | Complete |
| 3 | CHIRPS v3.0 daily (rnl, final) | UCSB Climate Hazards Center | Independent rainfall | **Required** | A | 1999-04-14 → 2026-01-30 (9,789/9,789 days; 28/28 years verified) | Zambia window, 0.05° | 0.05° (~5.5 km) | precip (mm/day) | Nearest pixel at the location-master point; raw grid kept for zonal means later | **Yes** — but partly redundant with POWER (monthly r ≈ 0.90); Stage 3 must justify using one or both | Yes (vs POWER) | — | Complete |
| 4 | HydroSHEDS v1 — data version 1.1 (void-filled DEM 15″, HydroRIVERS v1.0, HydroBASINS v1c L4/L6) | WWF / McGill / USGS | Terrain & drainage | Recommended | A (static) | Static (SRTM-era, ~2000) | Africa archives; Zambia subset | DEM 15″ (~460 m); vectors | elevation, slope, flat fraction, distance to river, upstream area, river density, basin IDs | Both point value and district zonal statistic (see §3) | **Yes** (static) | — | — | Complete |
| 5 | ESA WorldCover 2021 v200 | ESA / Copernicus | Land cover | Optional | **Static / slow-changing — OPTIONAL** (context) | 2021 snapshot | Zambia tiles | 10 m product, read at 40 m overview | % tree, shrub, grass, crop, built-up, bare, water, wetland | District % of area (cos-latitude weighted) + class at point | *Optional* — 2021 snapshot for a 1999–2026 history | Context | Built-up % doubles as exposure context | Complete |
| 6 | Soil moisture | NASA POWER GWETTOP/GWETROOT/GWETPROF (collected); ERA5-Land (not collected) | Antecedent wetness | Optional | A *opt.* | 1999-04-14 → 2026-01-30 (POWER) | 101 district points | ~0.5° | soil wetness 0–1 (surface / root zone / profile) | Point | **OPTIONAL EXPERIMENT** (Spearman 0.83–0.90 with trailing 30–90-day rainfall) | — | — | POWER soil wetness complete; ERA5-Land only with the researcher's CDS account |
| 7 | River gauges | GRDC / WARMA / ZRA | Hydrological state | Desirable, not available | B | Unknown without request | A few main-stem stations at most | Station | discharge, stage | Station → district/catchment (would need a mapping) | No | Would be | — | **OPTIONAL / DATA ACCESS LIMITED** — not available at sufficient coverage/quality for core modelling (request-only) |
| 8 | Satellite flood observations | DFO archive (collected if reachable); Sentinel-1, Global Flood Database, CEMS (evaluated) | Independent event evidence | Optional | B | DFO 1985–; S1 2014–; GFD 2000–2018 | Event polygons/centroids | Event | flood dates, extent | Event centroid/polygon → district (later spatial operation) | **No** (post-event) | Yes (DFO) | — | **OPTIONAL VALIDATION DATA — NOT REQUIRED FOR CORE MODEL** (DFO server unreachable throughout); S1/GFD = future work; CEMS = not practical |
| 9 | ENSO: ONI, Niño 3.4 | NOAA CPC (ERSST.v5) | Seasonal climate state | Optional | A *opt.* (seasonal) | 1950 → 2026 | Basin-scale index (same value for every district) | Monthly | ONI, Niño 3.4 anomaly | Calendar month, **lagged** (§4) — never merged as a daily local observation | *Opt. experiment* | Context | — | Complete |
| 10 | IOD / DMI | NOAA PSL (HadISST, monthly, full window); BoM weekly IOD (2008 →, context) | Seasonal climate state | Optional | A *opt.* (seasonal) | 1870 → 2026 (PSL) | Basin-scale index | Monthly / weekly | DMI | Calendar month, lagged (§4) | *Opt. experiment* | Context | — | Complete |
| 11 | WorldPop | WorldPop, Univ. of Southampton (wpic1km, people per pixel, not UN-adjusted) | Population exposure | Required for the decision-support layer | **C** | 2000–2020 yearly | Zambia, ~1 km | 30″ | people per cell → people per district, density | District sum of cells whose centre is inside the polygon → `data/processed/exposure/` | **No — never** | — | **Yes** | Complete |

## 3. Spatial join decisions (none chosen silently)

All environmental values are computed **both ways**, so Stage 3 chooses with evidence:

| Variable family | At the location point (`*_point_*`) | District zonal statistic (`*_district_*`) | Recommendation for Stage 3 |
|---|---|---|---|
| Elevation | DEM cell containing the point | mean, median, min, max, std, p10, p90 of cells whose centre lies in the polygon | District statistics: a single point in a 5,000 km² district says little about where water collects |
| Slope | slope cell at the point | mean, median, and fraction of cells with slope < 0.5° (flat, poorly drained land) | District flat fraction + mean slope |
| Rivers (HydroRIVERS) | distance to nearest reach with upstream area ≥100 / ≥1,000 / ≥10,000 km², and that reach's upstream area | max upstream area of any reach in the district (flow-accumulation proxy), max long-term discharge, river density (km/km², reaches ≥100 km²), fraction of district within 5 km of a river ≥1,000 km² | District statistics; point distances as sensitivity check |
| Basins (HydroBASINS) | level-4 and level-6 basin containing the point | dominant level-4 basin by area + its share | Context / grouping for spatial cross-validation, not a numeric predictor |
| Land cover (WorldCover) | class of the cell at the point | % of district area per class, cells weighted by cos(latitude) | District % for built-up, cropland, tree cover, grassland, water, wetland only |
| Population (WorldPop) | density of the 1 km cell at the point | district total and density per year | Exposure layer (class C), district totals |
| Weather (POWER, CHIRPS) | value at the point | CHIRPS district means are possible later from the kept raw grid | Point for both (POWER's ~50 km cells make zonal means meaningless) |

Geometry: district polygons are the DesInventar export's `districts.shp` (same source as the location master). Two
polygons (Mulobezi, Chikankanta) carry another district's code and are excluded. Areas and distances use
ESRI:102022 (Africa Albers Equal Area). **Flow direction / flow accumulation rasters were not downloaded:**
HydroRIVERS already carries each reach's upstream area derived from them, which is what a district join needs.

**WorldCover overview decision.** Reading full 10 m tiles for Zambia would mean 17 × ~138 MB (≈2.3 GB) over a
~0.5 MB/s link. The tiles' internal 1/4 overview (~40 m) was compared with full 10 m resolution at **six contrasting
~30 × 30 km sites** (Lusaka urban, Barotse floodplain, Bangweulu swamps, Copperbelt, Eastern farmland, Northern
miombo; `reports/worldcover_overview_bias_test.csv`): the largest class difference per site was 0.14–0.52
percentage points (e.g. Lusaka built-up 34.5 % vs 34.0 %; Chipata cropland 36.8 % vs 36.3 %). The 1/8 overview
was rejected (up to 1.46 points). This is a **computational check of the reading method at six sites, not a
nationwide accuracy assessment of WorldCover.** The representation is sufficient because district shares are
computed over 431–40,000 km² (hundreds of thousands to millions of 40 m cells); it is reliable for major classes and
indicative only for classes under ~1 %.

## 4. Temporal leakage audit of every candidate variable

Prediction at the end of day *t*; target = a qualifying flood starting in (t, t+7].

| Variable | Known by end of day *t*? | Leakage risk | Rule for Stage 3 |
|---|---|---|---|
| POWER / CHIRPS daily weather for days ≤ t | Yes (historical reanalysis/analysis) | Low | Use only days ≤ t; never t+1…t+7 rainfall. Operational note: CHIRPS *final* lags ~3 weeks, *prelim* ~2 days; POWER lags a few days. |
| Rolling sums (3/7/14/30-day) | Yes if windows end at t | Medium (easy to centre a window by mistake) | Trailing windows only (`[t−k+1, t]`). Not built yet. |
| Soil wetness ≤ t | Yes | Low | Same as weather |
| Elevation, slope, rivers, basins | Static | None | Allowed |
| WorldCover 2021 | Static snapshot taken **after** most events (2000–2020) | Low–medium (built-up and cropland grow over time) | Treat as quasi-static context; state the anachronism; test with/without |
| ONI (3-month season centred on month *m*) | Only after month *m+1* ends | **High if aligned naïvely** | For date *t* use the season centred on month(t) − 2 at the latest |
| Niño 3.4 / DMI monthly for month *m* | After month *m* ends (published early *m+1*) | Medium | For date *t* use month(t) − 1 at the latest |
| WorldPop year *y* | Modelled for mid-year *y* | Low (but it is exposure) | Not an occurrence feature; for impact use year ≤ year(t) |
| Past DesInventar floods (e.g. days since last flood in district) | Yes if strictly before t | Medium (must use event dates < t, and reporting is uneven) | Allowed only with strict `< t` filtering |
| DesInventar deaths, injured, missing, affected, victims, evacuated, relocated, houses destroyed/damaged, crops (ha), livestock, roads, losses (local/USD), schools/hospitals affected, sector flags, `duracion`, `di_comments`, `fuentes` | **No — produced by the event** | **Direct leakage** | **Never predictors.** Audit/validation only |
| `event_end_date_from_duration` | No | Direct leakage | Never a predictor |
| Emergency response / relief (`socorro`, relief-food text), disaster declarations, assessment reports | No — issued after the flood | Direct leakage | Never predictors |
| DFO deaths, displaced, severity, affected area | No | Direct leakage | Validation only |
| DFO / satellite flood extent | No — observed after the flood | Direct leakage | Validation only |
| River gauge stage/discharge ≤ t | Would be yes | Low | Not available |
| GloFAS historical discharge/runoff/soil wetness ≤ t | Yes (reanalysis) | Low | Days ≤ t only. Note: reanalysis is forced by ERA5 *analysis* rain — in real time only forecasts exist, so a reanalysis-based model is an upper bound on operational skill |
| GloFAS historical discharge after t | — | **Direct leakage** | Never — it is the flood itself |
| GloFAS reforecast/forecast issued on date i for lead L | Yes if i ≤ t | Low if i ≤ t | Use the latest issue ≤ t; lead = target day − issue date; never mix with reanalysis after t |
| Global Surface Water occurrence (1984–2021) | Static aggregate incl. later years | Low–medium | Optional static descriptor; state the anachronism |

## 5. Methodological decisions for the researcher (do not block collection)

0. **Flood-date reliability (most important).** Many exact-day DesInventar dates are assessment/repair/report dates,
   not onset dates: onset_plausible 91, onset_uncertain 102, onset_unlikely 83 (`reports/flood_date_reliability.md`).
   Choose which may be positives; the rest must be excluded from both classes.
1. **Seven non-flood-category records describe flood damage** (`reports/desinventar_flood_keyword_hits.csv`, filter
   `matched_keywords` containing flood/inundat/overflow/submerg). Include as floods or not? Default: excluded.
2. **168 flood records lack an exact day** (163 year-only, 3 month-only, 2 invalid years). They cannot be placed
   in a 7-day window: Stage 3 must exclude them from *both* classes (mark the district-period "uncertain").
3. **Reporting is uneven over time** (e.g. 2009–2014 peaks): absence of a record is not proof of no flood.
4. **NASA POWER > 300 mm/day values** (Mwinilunga 2020-02-23: 338 mm vs CHIRPS 10.8 mm; Siavonga 2023-12-22: 304 mm
   vs CHIRPS 29.5 mm — probable reanalysis artefacts): keep, cap or winsorise — one rule for all locations
   (`reports/nasa_power_anomaly_investigation.md`).
5. **ERA5-Land** only if the soil-moisture experiment proves useful with POWER soil wetness first.

# FloodShield-Zambia — Methodological Data Decisions (Stage 2 QC)

This document records *why* each dataset exists in the project, what role it may play, and which decisions are
still open. Numbers are taken from the validation outputs in `reports/` (cited inline); nothing here is a model
result — no target, features or model have been built.

Research question: *Can historical meteorological and environmental conditions be used to estimate the
probability that a flood event will occur at a Zambian location within the next 7 days?*

---

## 1. Why each dataset was collected, and its role

| Dataset | Why collected | Role | Core predictor? | Reason |
|---|---|---|---|---|
| DesInventar Zambia | The only national, district-coded historical flood record | **Label source** (+ audit) | No — it defines the target | Consequence fields are post-event (§6) |
| NASA POWER daily weather | Daily rainfall, temperature, humidity, wind at every district point, 1999–2026, no gaps | **CORE** | Yes | Directly answers "meteorological conditions"; complete, gap-free, consistent |
| CHIRPS v3.0 daily rainfall | An independent, higher-resolution (0.05°), gauge-blended rainfall source | **CORE (rainfall)** | Yes — but see §4 on redundancy with POWER | Rainfall is the main flood driver; a second independent source tests robustness |
| HydroSHEDS terrain/hydrology | Floods depend on where water collects: elevation, slope, river proximity, upstream area | **CORE (static)** | Yes | "Environmental conditions" in the question; static, so no temporal leakage |
| ESA WorldCover 2021 | Land cover changes runoff and exposure | **OPTIONAL (static/slow-changing context)** | No by default | One 2021 snapshot for a 1999–2026 history (§5); test in Stage 3 with/without |
| Soil wetness (NASA POWER GWET*) | Antecedent wetness changes how rain becomes runoff | **OPTIONAL EXPERIMENT** | No by default | Model-derived from the same reanalysis rainfall forcing; overlap with antecedent rainfall (§3) |
| Climate indices (ONI, Niño 3.4, DMI) | ENSO/IOD modulate Zambia's seasonal rainfall | **OPTIONAL (seasonal)** | No by default | Basin-scale, monthly, publication-lagged; same value for all districts |
| WorldPop | Who would be affected | **EXPOSURE (separate layer)** | **Never** | Population does not cause floods; used only to rank impact *after* P(flood) |
| DFO flood archive | Independent event dates | **VALIDATION** | No | Post-event; server unreachable during collection |
| River gauges (GRDC/WARMA/ZRA) | Observed river state | **OPTIONAL / DATA ACCESS LIMITED** | No | Request-only; would cover few districts |
| Satellite flood extent (Sentinel-1, GFD, CEMS) | Independent mapped floods | **VALIDATION — FUTURE WORK** | No | Post-event; needs accounts and heavy processing |

The core candidate set for Stage 3 is therefore: **DesInventar (labels) + NASA POWER + CHIRPS + HydroSHEDS terrain/
hydrology.** Optional features (soil wetness, climate indices, land cover) enter only as declared experiments.
Exposure (WorldPop) is kept in its own folder, `data/processed/exposure/`, so it cannot drift into the occurrence
dataset by accident.

## 2. How spatial aggregation will work

The spatial unit is the DesInventar district (101 units). Two representations were computed for every static
variable so the choice is evidence-based rather than silent (`data/processed/district_terrain_hydrology.csv`,
`district_landcover.csv`):

| Variable | A. Location point (district point) | B. District-wide zonal statistic | Evidence | Recommendation |
|---|---|---|---|---|
| Elevation | cell value at the point | mean, median, min, max, std, p10, p90 | point vs district mean r = 0.93, median |Δ| 25 m | **B** (p10/min capture low-lying land where water collects) |
| Slope | cell value at the point | mean, median, share < 0.5° | point vs district mean r = 0.64 | **B** — a single 460 m cell is a poor proxy for district drainage |
| River proximity | distance from the point to nearest river (≥100 / ≥1,000 / ≥10,000 km² upstream) | min distance (0 if a river crosses), mean and median distance from a ~2 km grid of points covering the district; share of district within 5 km of a ≥1,000 km² river | point vs district-mean distance (≥1,000 km²) r = 0.56 | **B** (district mean/median distance + share near river) |
| Flow accumulation | upstream area of the nearest river reach | **max upstream area of any reach in the district** (largest river passing through) | — | **B (max)** — a centroid flow-accumulation value is essentially random |
| Basin | level-4/6 HydroBASINS at the point | dominant level-4 basin + share | — | Grouping for spatial cross-validation, not a numeric predictor |
| Land cover | class at the point | % of district per class (cos-latitude weighted) | — | **B** |
| Weather (POWER, CHIRPS) | point series | (CHIRPS district means possible later from the stored grid) | POWER's ~50 km cells make zonal means meaningless | **A** for both, for consistency |

Rules: a raster cell belongs to a district when its centre lies inside the polygon; areas and distances in
ESRI:102022 (Africa Albers Equal Area); polygons from the DesInventar export (two code-conflict polygons, Mulobezi
and Chikankanta, excluded and documented).

## 3. Specific evaluations requested in QC

**HydroSHEDS version.** The files are **HydroSHEDS v1** — the archive ships `HydroSHEDS_TechDoc_v1_4.pdf`
("Data Version 1.1, Technical Documentation Version 1.4, April 2022"). DEM = void-filled DEM, 15 arc-second,
int16, no-data 32767, metres above the EGM96 geoid, WGS84. HydroRIVERS v1.0, HydroBASINS v1c. v2 was not used: a
stable, documented v1 product covering Zambia was preferred. Integrity: every archive's byte size equals the
server's declared size, ZIP CRC checks pass, SHA-256 recorded. Not over-collected: flow-direction and flow-
accumulation rasters were skipped because HydroRIVERS already carries the upstream area derived from them.

**WorldCover overview method.** Product: ESA WorldCover 2021 v200 (tile metadata `product_version V2.0.0`),
EPSG:4326, 10 m. Read at the tiles' internal 1/4 overview (~40 m). This was tested as a *computational* check —
overview vs full 10 m at six contrasting sites (urban Lusaka, Barotse floodplain, Bangweulu swamps, Copperbelt,
Eastern farmland, Northern miombo; `reports/worldcover_overview_bias_test.csv`): the largest class difference was
0.14–0.52 percentage points per site (1/8 overview: up to 1.46 points, rejected). The residual pattern (dominant
class slightly over-represented) is typical of mode resampling. **This tests the reading method at six sites; it is
not a nationwide accuracy assessment of WorldCover**, and it is reliable for district shares of major classes,
indicative only for classes < ~1 %. The overview was chosen because district shares over 431–40,000 km² need
millions of samples, not 10 m detail — not merely because it is smaller.

**Soil wetness.** Variables (NASA POWER parameter manager): `GWETTOP` "Surface Soil Wetness" (upper 5 cm),
`GWETROOT` "Root Zone Soil Wetness" (~upper 1 m), `GWETPROF` "Profile Soil Moisture" (surface to bedrock); unitless
0 (dry) – 1 (saturated); daily; MERRA-2 grid (~0.5° × 0.625°); 1999–2026. It is a *land-surface-model* quantity
driven by reanalysis precipitation, not an observation. Classification: **OPTIONAL EXPERIMENT** — physically
relevant (antecedent wetness), but largely a smoothed memory of the same rainfall the core set already contains.
Overlap with antecedent rainfall is quantified in `reports/environmental_data_validation_report.md`.

**WorldCover temporal limitation.** WorldCover describes 2021. Applying it to 1999–2020 assumes land cover is
quasi-static; built-up area and cropland grew over the period. Because it is one value per district, it also acts
partly as a district identifier in a 101-district model. → **Static/slow-changing context; OPTIONAL**, not core.

## 4. CHIRPS vs NASA POWER — independence and redundancy

Over the full overlap (101 districts × 9,789 days; `reports/chirps_validation_report.md`):

| Measure | Value |
|---|---|
| Correlation, monthly totals (median over districts) | 0.90 |
| Correlation, daily (median over districts) | 0.52 |
| Mean bias CHIRPS − POWER | +0.20 mm/day; +5.9 mm/month |
| Median bias | +0.00 mm/day (+0.56 on wet days); +0.11 mm/month |
| Mean absolute daily difference | 2.35 mm/day |
| Extremes | POWER has heavier daily tails (mean annual maximum ≈ 48 vs 38 mm; days > 50 mm ≈ 0.59 vs 0.15 per location-year) |
| Heavy days ≥ 30 mm | the two sources coincide on only ~4 % of days that either calls heavy |
| Coverage | both complete for 1999-04-14 → 2026-01-30 at all 101 points | High monthly correlation means both
describe the same seasonal regime; **it is not evidence that either is correct.** On the heaviest days (≥30 mm) the two
products rarely agree on *which* day it was. Using both as features would partly duplicate the seasonal signal.
Decision deferred to Stage 3 with a stated justification, e.g. one source as primary, the other as sensitivity
analysis. Neither dataset was adjusted towards the other.

## 5. Temporal limitations

| Dataset | Temporal nature | Limitation |
|---|---|---|
| DesInventar | Events 2000–2026; exact-day dates 2000-04-13 → 2026-01-23 | Uneven reporting; 168 records without exact day; **many exact dates are not onset dates (§7)**; almost no exact-day records 2018–2021 |
| NASA POWER, CHIRPS, soil wetness | Daily, 1999-04-14 → 2026-01-30 | Operational latency (CHIRPS final ≈ 3 weeks; POWER a few days) matters for deployment, not for historical study |
| HydroSHEDS | Static (~2000 SRTM) | Rivers/terrain assumed unchanged |
| WorldCover | 2021 snapshot | Anachronistic for 1999–2020 |
| Climate indices | Monthly, published after the month (ONI needs the following month) | Must be lagged (§6) |
| WorldPop | Yearly 2000–2020 | 2021–2026 not covered by this product; exposure only |

## 6. Leakage risks — prohibited predictive uses

Never to be used as predictors (they exist only because a flood happened, or are recorded after it):
deaths, injured, missing; affected population, victims, evacuated, relocated; houses damaged/destroyed; crops,
livestock, roads, bridges, schools, hospitals and other infrastructure damage; economic losses (local currency/
USD); sector-affected flags; relief/emergency response; event duration and end date; record comments and sources;
disaster declarations; post-event flood extent (DFO, satellite); DFO deaths/displaced/severity.

Allowed with care: weather and soil wetness for days ≤ t (trailing windows only); static terrain/hydrology; land
cover (quasi-static, flagged); ONI up to the season centred on month(t) − 2 and Niño 3.4/DMI up to month(t) − 1;
counts of *past* floods strictly before t. WorldPop is exposure, not a predictor.

## 7. Known data-quality issues

1. **Flood dates are often not onset dates (most important).** Of 276 exact-day flood records, 117 fall in the dry
   season (May–Oct), 69 share a date with ≥4 other records (e.g. 20 on 2013-06-06, 15 on 2017-05-03), and 122 have
   administrative text ("assessment report", "repairing of multiple bridges", "request for funds for rehabilitation",
   "construction of classroom block"). Classification without using rainfall (`data/processed/desinventar_flood_date_
   reliability.csv`): **onset_plausible 91, onset_uncertain 102, onset_unlikely 83, no exact date 168.** An
   independent check shows the flags are meaningful: the 7-day CHIRPS rainfall before *onset_plausible* dates is at the
   73rd wet-season percentile (median 56.5 mm), versus the 4th percentile (0.3 mm) for *onset_unlikely* dates
   (`reports/flood_date_reliability.md`).
2. 168 records have only a year/month (or an invalid year).
3. 4 records have only a province.
4. Reporting intensity varies by year (data-entry campaigns), so "no record" ≠ "no flood".
5. Two NASA POWER days > 300 mm (Mwinilunga 2020-02-23: 338 mm; Siavonga 2023-12-22: 304 mm). CHIRPS at the same
   points recorded 10.8 and 29.5 mm, and nowhere in Zambia exceeded 55 / 47 mm those days → **probable reanalysis
   artefacts**; retained and flagged (`reports/nasa_power_anomaly_investigation.md`).
6. CHIRPS grid maxima > 300 mm on 2009-04-02 (402 mm) and 2022-04-27 (336 mm): identical to the official CHC daily
   files (not extraction artefacts) and consistent with the official pentad totals (not disaggregation artefacts);
   both clusters lie at the north-east edge of the window, essentially outside Zambia (1 and 0 cells > 100 mm inside),
   next to the very wet Malawi/Tanzania border highlands. Physical reality cannot be proven from CHIRPS alone →
   **retained and flagged; they affect no district series** (nearest points received 30 and 14 mm).
7. 8 groups of neighbouring districts share an identical NASA POWER series (same grid cell).
8. 7 records in non-flood categories describe flood damage — excluded pending the researcher's decision.

## 8. Known missing sources and why they do not stop the study

| Missing | Why missing | Why the study can proceed |
|---|---|---|
| River gauge series | GRDC data only via a personal request form; WARMA has no public portal | Gauges would cover a handful of main-stem rivers, not 101 districts; the question is about meteorological/environmental conditions, which are fully covered |
| ERA5-Land soil moisture | Needs a Copernicus CDS account (researcher's credentials) | Soil moisture is optional; a no-credential substitute (POWER GWET*) is available for the experiment |
| Satellite flood extent | Account-gated, heavy processing; post-event | Validation only, never a predictor |
| DFO archive | Server unreachable from this machine throughout collection | Optional validation; does not affect predictors or labels |
| WorldPop after 2020 | Not in this product series | Exposure layer only; nearest year can be used, documented |

## 9. Decisions the researcher must make before Stage 3

1. **Label rule given date reliability (§7.1)** — e.g. positives = `onset_plausible` (± `onset_uncertain`), all other
   exact-day records and year-only records *excluded from both classes* for their district-period. With 91 (or 193)
   usable events, consider whether a 7-day window is still viable or whether to widen it.
2. Whether the 7 keyword-matched non-flood records count as floods.
3. Rainfall source policy: POWER, CHIRPS, or one as sensitivity analysis (§4).
4. A single rule for extreme rainfall values (keep / cap / winsorise), applied to all locations.
5. Whether to run the optional experiments (soil wetness, climate indices, land cover).


---

## 10. Final Stage 2 additions (GloFAS, Global Surface Water, second audit)

| Dataset | Why collected / evaluated | Role | Reason |
|---|---|---|---|
| GloFAS v4.0 historical (discharge, runoff, soil wetness) | Floods are river responses; routed discharge carries upstream rain from Angola/DRC that local rainfall cannot | **CORE — pending the researcher's EWDS credentials** | Highest added value of any remaining source; pipeline ready |
| GloFAS v4.0 reforecasts | Only archive allowing an honest *forecast* experiment (issues 2003–2023, leads 1–46 d) | OPTIONAL (forecast experiment) | Needed to show real-time skill rather than reanalysis skill |
| GloFAS v4 static maps (upArea, ldd, chan) | Locate each district's main river on the GloFAS grid | CORE support | River-network extraction; cross-checked with HydroRIVERS (log-r 0.981) |
| JRC Global Surface Water occurrence | Observed (Landsat) floodplain frequency 1984–2021 | OPTIONAL (static) | Empirical flood-proneness; aggregate includes post-event years |

Spatial aggregation for GloFAS: discharge at the district's main-river cell (largest upstream area), nearest
significant river as sensitivity; runoff and soil wetness as district means. District centroids lie on a
≥1,000 km² river in only 9 % of districts, so centroid extraction is rejected for discharge
(`reports/glofas_extraction_method_comparison.md`). Note: the GloFAS `chan` mask flags every cell as channel, so
upstream area — not `chan` — identifies rivers.

Additional quality findings: NASA POWER soil wetness is published to 2 decimals (GWETPROF ~42 distinct values per
district, plateaus up to ~200 days) — another reason it stays optional. The second independent audit
(`reports/second_audit_report.md`) passed 48 of 50 checks; the FAIL is the missing GloFAS series and the WARN is the
soil-wetness quantisation.

Why the study can still proceed if GloFAS is never obtained: a weather + terrain model answers the research question
as originally stated; GloFAS would strengthen it (hydrological state, upstream signal, honest forecast test). The
Stage 2 gate is nevertheless held open because GloFAS was designated the highest-priority source.

**Decision record (2026-10-08):** no EWDS credentials could be set up, so the researcher chose to close Stage 2
without the GloFAS time series. GloFAS historical and reforecasts are **DEFERRED** (not rejected): the static river
maps, extraction design and scripts are in place, and `glofas.collection_status` in `config/data_sources.yaml`
records the decision. Consequence for Stage 3: hydrological state is represented only indirectly (antecedent
rainfall, soil wetness, terrain, floodplain occurrence), and no forecast archive is available, so any skill
reported is reanalysis/observation-based skill.

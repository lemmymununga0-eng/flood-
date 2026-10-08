# GloFAS extraction-method comparison

_Generated 2026-10-07T20:11:41+00:00 by `scripts/build_glofas_extraction_points.py` from the official GloFAS v4 static maps (upArea, chan)._

| Method | What it samples | Median upstream area (km²) | Notes |
|---|---|---:|---|
| A centroid | cell at the district point | 61 | on a river with ≥1,000 km² upstream in only 9% of districts — usually a minor stream cell |
| B zonal | all 203 (median) cells in the district | — | mixes river and hillslope cells: meaningless for discharge, appropriate for runoff and soil wetness |
| C main river | largest-upstream cell in the district | 34,603 | the river that carries the district's (and upstream) flood water |
| D nearest river ≥1,000 km² | nearest significant river to the point | 1,770 | median 12.4 km away; inside the district in 86% of cases |

## Decision

- **River discharge → C (main river in district)**, with D as a sensitivity variant. Discharge exists only on the river network; a centroid cell is rarely a river cell, and averaging discharge over a district is physically meaningless.
- **Runoff water equivalent and soil wetness index → B (district zonal mean)** — areal fluxes/states.
- A is recorded only for transparency.
- Note: the GloFAS channel mask (`chan`) marks 100% of cells in the window as channel (LISFLOOD routes water through a channel in every cell), so it cannot separate rivers from hillslopes; upstream area is used instead.

## Cross-check against HydroRIVERS (independent river network)

- log10 correlation of GloFAS upstream area at C vs HydroRIVERS' largest upstream area in the district: **0.981**
- Districts where the two agree within a factor of 2: **95%**
- Disagreements are expected where a district only touches a large river at its boundary (grid cells vs vector lines) — see `C_vs_hydrorivers_ratio` in the CSV.

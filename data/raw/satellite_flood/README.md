# Satellite / independent flood observations

| Source | Coverage | Classification | Status |
|---|---|---|---|
| Dartmouth Flood Observatory (DFO) Global Active Archive of Large Flood Events — https://floodobservatory.colorado.edu/ | Global event list 1985–, dates + centroid + area; compiled from news, governments and MODIS | **OPTIONAL VALIDATION** | `scripts/download_flood_observations.py` (server was intermittently unreachable) |
| Copernicus Emergency Management Service — Rapid Mapping | On-demand activations only; no Zambia flood activation was found (one Zambia drought/water monitoring product, EMSN196) | **NOT PRACTICAL** as a systematic source | Not collected |
| Sentinel-1 SAR (Copernicus) | 2014–, 6–12 day revisit, 10 m | **FUTURE WORK** — needs Copernicus Data Space / Earth Engine accounts and per-event SAR processing | Not collected |
| Global Flood Database (Tellman et al. 2021, MODIS) | 2000–2018, 913 large events worldwide, Earth Engine only | **FUTURE WORK / OPTIONAL VALIDATION** | Not collected |

Satellite products observe flood *extent after* it happens: they can only validate or explain events,
never be predictors for a 7-day-ahead model.

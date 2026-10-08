# ERA5-Land — evaluated, not collected

- Product: ERA5-Land hourly/daily reanalysis (ECMWF / Copernicus Climate Change Service), 0.1° (~9 km), 1950–present.
- Official source: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land
- Relevant variables: `volumetric_soil_water_layer_1` (0–7 cm) … `_layer_4` (100–289 cm), m³ m⁻³.
- Access: requires a personal Copernicus Climate Data Store account, acceptance of the licence, and an API
  key. Creating accounts or entering credentials is something only the researcher can do, so nothing was
  downloaded.
- Decision (see docs/DATA_REQUIREMENTS_MATRIX.md): soil moisture is an **OPTIONAL EXPERIMENT**, not a core
  predictor. A no-credential stand-in from the same provider chain as the core weather data was collected
  instead: NASA POWER `GWETTOP`, `GWETROOT`, `GWETPROF` (MERRA-2 soil wetness, daily, 101 district points) in
  `data/raw/nasa_power/daily_soil_moisture/`.
- To add ERA5-Land later: create a CDS account, accept the ERA5-Land licence, put the key in `~/.cdsapirc`,
  then request daily statistics for the Zambia bounding box in config/data_sources.yaml.

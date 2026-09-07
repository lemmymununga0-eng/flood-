# Data Sources — FloodShield Zambia

Status: Phase 0/1. **No data has been downloaded yet.** This document records candidate
sources and what needs to be verified before any of them is relied on — nothing below is
a confirmed integration.

## Candidate historical source: NASA POWER

- **What it is:** NASA's Prediction Of Worldwide Energy Resources project — a free,
  global, daily (and sub-daily for some variables) meteorological/solar reanalysis
  dataset, commonly used in agricultural and hydrological research.
- **Candidate variables:** precipitation, temperature, humidity, wind, and soil-moisture-
  related variables where available.
- **Status: TO VALIDATE.** This project has not yet made a live request against the NASA
  POWER API this session. Before Phase 2 ingestion code is written, confirm: current base
  URL and endpoint structure, whether an API key is required, rate limits, actual
  temporal resolution available for the candidate Zambian coordinates, and current terms
  of use for research/derivative-product use.

## Candidate supplementary sources

- **CHIRPS** (Climate Hazards Group InfraRed Precipitation with Station data) —
  satellite + station-blended rainfall estimates, commonly used in African hydrological
  studies. **TO VALIDATE**: coverage and resolution for Zambia, access method.
  Every dataset added here must earn its place with a documented reason (governing
  prompt, section 6) — not added merely to look sophisticated.
- **ERA5 / ERA5-Land** — ECMWF reanalysis, hourly, global. **TO VALIDATE**: access
  complexity (Copernicus Climate Data Store account/API), and whether its resolution
  offers something NASA POWER doesn't for this project's variables.

## Candidate near-real-time source

- **OpenWeather** (or an equivalent legitimate provider) for operational/near-real-time
  observations and forecasts. **TO VALIDATE**: current free-tier limits, variables
  available, and whether it can be a viable operational data path within a
  cost-controlled student project (section 55).

## Flood ground-truth / label sources (see also ML-METHODOLOGY.md)

Not yet identified. Candidates to investigate in Phase 1: Zambian disaster-management
authority reports, ReliefWeb/UN OCHA situation reports for Zambia, remote-sensing flood-
extent products (e.g. from satellite-derived flood mapping services), and peer-reviewed
literature on rainfall-accumulation flood thresholds applicable to the Zambian/Southern
African context. None have been located or verified yet.

## Data source principle (non-negotiable)

Real data is never silently replaced with fabricated data. Synthetic data may only be
used for unit tests, pipeline-mechanics tests, or a documented dev-only fallback when an
external API is temporarily unavailable — and must always be labelled
`SYNTHETIC / DEVELOPMENT ONLY` wherever it appears, including in code comments, logs, and
any UI that might render it. It must never be presented as real Zambian weather
observations, validation data, research evidence, or final model performance.

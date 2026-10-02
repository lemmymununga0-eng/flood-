# Data Sources — FloodShield Zambia

Status: updated 2026-10-01. **Data has since been downloaded and used.** NASA POWER now
provides 1,099,374 daily rows across 82 Zambian districts (1990-01-01 to 2026-09-15);
flood events come from DesInventar, the Dartmouth Flood Observatory and a hand-compiled
DMMU/WARMA/ReliefWeb/International-Charter log. See `ml/labels/LABEL_PROVENANCE.md`.
The assessments below record candidate
sources and what needs to be verified before any of them is relied on — nothing below is
a confirmed integration.

## Candidate historical source: NASA POWER

- **What it is:** NASA's Prediction Of Worldwide Energy Resources project — a free,
  global, daily (and sub-daily for some variables) meteorological/solar reanalysis
  dataset, commonly used in agricultural and hydrological research.
- **Candidate variables:** precipitation, temperature, humidity, wind, and soil-moisture-
  related variables where available.
- **VERIFIED (from official docs, checked 2026-09-07):** the Daily API's point endpoint
  takes `longitude`, `latitude`, `start`, `end`, and `format` as required parameters and
  `parameters` (up to 20 per request), `community` (e.g. `AG`), `time-standard`,
  `site-elevation`, and `wind-elevation` as optional ones. Data is available from
  1981-01-01 to near-real-time. Formats offered: NetCDF, ASCII, ICASA, JSON, CSV. The
  docs do not state an API key is required (consistent with NASA POWER's longstanding
  reputation as a keyless public API, but this project has not yet independently
  confirmed that with a live request — see below). Docs source:
  [NASA POWER Daily API docs](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).
- **Rate-limit caution (VERIFIED, from official docs):** the docs explicitly warn that an
  application making repeated requests for the same location can be blocked — the
  ingestion client (Phase 2) must cache/dedupe requests per coordinate rather than
  re-fetching the same point repeatedly.
- **RESOLVED 2026-09-09 — live request succeeded from the developer's real machine.**
  Earlier sessions (2026-09-07/08) ran in sandboxed cloud environments where two
  independent blockers prevented verification: (1) an egress proxy rejecting the direct
  `curl` CONNECT to `power.larc.nasa.gov`, and (2) a web-fetch tool refusing the URL
  per NASA's `robots.txt` (a crawler policy, not applicable to an application calling
  its own documented API with `requests`/`httpx`, but respected by that tool regardless).
  **Both were properties of those specific sandboxes, not of NASA POWER or this
  project's code.** On 2026-09-09, from the actual developer machine this project runs
  on, `NASAPowerIngestor.download()` (`ai-engine/src/ingestion/nasa_power_ingestor.py`)
  was run for real — no code changes, the same client written back in Phase 2 — and
  succeeded on the first attempt: `GET https://power.larc.nasa.gov/api/temporal/daily/point`
  for Lusaka (-15.4167, 28.2833), 2000-01-01 through 2023-12-31, returned a real 8,766-row
  daily dataset (`ai-engine/data/raw/nasa_power_zambia.csv`) in ~14 seconds, no retries
  needed. This is now the first real, independently-verified success of this
  integration anywhere in this project's history — recorded exactly as it happened, not
  retroactively upgraded from "coded correctly" to "works" without evidence.
  **Still true and worth keeping in mind:** this was a single point (Lusaka) — Zambia's
  real flood events span many provinces, so a production system would need either
  multiple monitored points (the ingestor already supports `download_multiple_locations()`
  for this) or an accepted single-point-as-national-proxy limitation, stated explicitly
  wherever predictions are shown. Current terms of use for derivative/research products
  have also not been independently re-confirmed.

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

**VERIFIED, checked 2026-09-07 (web research, not yet a data integration):**

- **Disaster Management and Mitigation Unit (DMMU)**, Office of the Vice President of
  Zambia, is the national authoritative disaster-management body, confirmed as the
  requesting/coordinating authority for the January 2023 floods (Southern, Central, and
  Lusaka provinces; worst-hit districts named as Luapula, Kabompo, Lukulu, Senanga,
  Kitwe, Mambwe, and Solwezi) via
  [UN-SPIDER's Zambia floods page](https://www.un-spider.org/advisory-support/emergency-support/13047/floods-zambia)
  and [ReliefWeb's DMMU/OVP profile](https://www.preventionweb.net/organization/disaster-management-and-mitigation-unit).
  DMMU publishes situation reports (e.g. a drought response situation report was found
  on [ReliefWeb](https://reliefweb.int/report/zambia/republic-zambia-disaster-management-and-mitigation-unit-drought-response-situation-report-no-1-19th-april-2024)),
  which is a plausible path to real historical flood-event records (approach 1/2 in
  `ML-METHODOLOGY.md`). **TO VALIDATE:** DMMU's own site (dmmu-ovp.gov.zm) was
  unreachable this session (redirect loop) — retry later or contact DMMU directly for
  historical flood situation reports/data.
- **Water Resources Management Authority (WARMA)** issues Zambia's flood early warnings
  alongside DMMU (same UN-SPIDER source) — a second potential authoritative contact.
- **International Charter Space and Major Disasters, Activation #796 (Jan–Feb 2023)**
  produced 10 real satellite-derived flood-extent products for Zambia from Sentinel-2B
  imagery, covering the Luapula, Kafue, and Zambezi river systems and Mkushi district,
  requested by UNOOSA/UN-SPIDER on DMMU's behalf
  ([Charter activation page](https://disasterscharter.org/activations/flood-large-in-zambia-activation-796-)).
  This is a concrete example of approach 3 (remote-sensing-derived flood extent) — a
  real, citable precedent, though this project has not yet obtained the underlying
  products or confirmed a public access path to them.
- **Documented flood-prone informal settlements in Lusaka**, per peer-reviewed and
  graduate research: **Kanyama compound** (flooding effects on onsite sanitation,
  [UNZA dspace thesis](https://dspace.unza.zm/items/7e1d043b-57bc-41e8-bda5-cbb85e15b091)
  and [journal article](https://journals.eanso.org/index.php/ajccrs/article/view/1861))
  and **Ng'ombe settlement** ([ResearchGate paper](https://www.researchgate.net/publication/387084120_Urban_Flooding_A_Case_of_Ng'ombe_Settlement_in_the_City_of_Lusaka_Zambia)),
  plus general unplanned-settlement flood risk in Lusaka
  ([Flood risk in unplanned settlements in Lusaka](https://www.researchgate.net/publication/229045504_Flood_risk_in_unplanned_settlements_in_Lusaka)).
  This upgrades Kanyama specifically from "named in the governing prompt" to
  **VERIFIED via independent academic literature** as a documented flood-affected area —
  the first location in this project with that status. Ng'ombe is a credible addition
  to the candidate location list.

**Still not identified:** a downloadable, ready-to-use historical flood-event *dataset*
(as opposed to narrative situation reports and one-off satellite products). Building the
actual label will most likely require either (a) manually compiling event dates/locations
from DMMU/ReliefWeb/Charter situation reports into a small hand-built event table, or
(b) falling back to a documented rainfall-accumulation proxy threshold — see
`docs/ML-METHODOLOGY.md` for how this decision will be made.

## Data source principle (non-negotiable)

Real data is never silently replaced with fabricated data. Synthetic data may only be
used for unit tests, pipeline-mechanics tests, or a documented dev-only fallback when an
external API is temporarily unavailable — and must always be labelled
`SYNTHETIC / DEVELOPMENT ONLY` wherever it appears, including in code comments, logs, and
any UI that might render it. It must never be presented as real Zambian weather
observations, validation data, research evidence, or final model performance.

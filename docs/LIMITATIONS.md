# Known Limitations — FloodShield Zambia

Status: Phase 0. This file will grow substantially once real data is ingested; these are
the limitations already knowable before any data has been pulled.

## Current-state limitations (true today, 2026-09-07)

- **No data has been ingested yet.** Every downstream claim about dataset availability,
  quality, or coverage in this project is currently unverified.
- **No flood-event ground truth has been located or verified for Zambia.** Until Phase 1
  research is done, it is unknown whether a defensible non-proxy label is achievable at
  all; the project may end up relying on a documented rainfall-accumulation proxy, which
  is a materially weaker claim than "observed flooding" and must always be labelled as
  such in every document, API response, and UI surface.
- **No model has been trained.** No accuracy, precision, recall, F1, ROC-AUC, or PR-AUC
  figures exist. Any number resembling a metric anywhere in this repository before
  Phase 7 is a documentation error, not a result.
- **Prediction horizon is undetermined.** It depends on the temporal resolution of
  whichever historical source is selected (most public reanalysis/meteorological
  datasets are daily) and cannot be assumed to be hourly or sub-daily until tested.
- **Geographic scope is undecided.** Named Zambian locations in the governing prompt
  (Lusaka, Kanyama, Misisi, etc.) are candidate examples, not confirmed monitored areas.

## Structural limitations expected to persist

- **No physical sensors.** The system depends entirely on external meteorological data
  sources and their coverage/latency/accuracy for the Zambian region, which may be
  coarser than ground-based instrumentation would provide.
- **Decision-support only.** This system does not and will not claim guaranteed
  prediction, guaranteed evacuation outcomes, or official government warning status
  unless a competent authority formally adopts it.
- **Free/low-cost infrastructure constraint.** Hosting, database, and API choices are
  constrained to free or student-accessible tiers, which may limit uptime, storage, or
  request-rate compared to a funded operational deployment.

This document must be updated (not just appended to indefinitely — condense as it grows)
at the end of every phase with what was actually learned.

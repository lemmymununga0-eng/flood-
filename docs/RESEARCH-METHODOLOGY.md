# Research Methodology — FloodShield Zambia

## Research question

Can historical and near-real-time meteorological information be used, via machine
learning, to produce useful advance flood-risk predictions for selected regions of
Zambia?

This is treated as a genuinely open question. The project is designed to report whatever
answer the evidence supports — including "not with the currently available data at a
useful horizon" — rather than to confirm a predetermined conclusion (governing prompt,
section 59).

## Variables under investigation

Rainfall, accumulated rainfall, temperature, humidity, soil moisture/wetness (where
available), wind, other atmospheric conditions, temporal patterns, and geographic/
location information, as predictors of a flood-risk outcome (see
`docs/ML-METHODOLOGY.md` for the target/label design, which is the project's central
open methodological question).

## Data vs. predictions

Meteorological observations are inputs. Model output is a prediction. The system —
in code, database schema, API responses, documentation, and UI — must never represent a
prediction as an observed fact. A `Prediction` and a `WeatherObservation` are distinct
entities with distinct provenance.

## Evidence classification

Every factual claim made in this project's documentation is classified as one of:

- **VERIFIED** — supported by authoritative documentation, a real API response, or
  research actually checked during this project.
- **ASSUMED** — a stated engineering assumption made because information was
  unavailable at decision time.
- **RESEARCH HYPOTHESIS** — a question the project is investigating, not yet answered.

Zambian geographic claims specifically follow this same three-way split: a location is
never described as "officially flood-prone" without a citable authoritative source; it
may be described as a "candidate area of interest" or "research hypothesis" pending that.

## Reproducibility

Random seeds, package versions, model configuration, dataset versions, and feature
configuration will be recorded per experiment once training begins (see
`docs/ML-METHODOLOGY.md` and the experiment-tracking convention in
`ai-engine/experiments/`). `requirements.txt` pins the Python environment.

## Scientific integrity commitments

- No fabricated data, metrics, predictions, or model comparisons, under any
  circumstance, including to make interim progress look more complete.
- Poor or mixed results are reported as such — they are more valuable to this research
  project than fabricated strong results.
- Every model is evaluated on genuinely unseen (chronologically held-out) data before any
  performance claim is made about it.

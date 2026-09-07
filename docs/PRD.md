# Product Requirements Document — FloodShield Zambia

Status: draft, Phase 0. See `docs/PROJECT-MEMORY.md` for decision rationale and
`docs/LIMITATIONS.md` for what is not yet known.

## 1. Problem statement

Communities in flood-prone areas of Zambia often have limited advance warning of
flooding driven by rainfall accumulation and related meteorological conditions. FloodShield
Zambia investigates whether historical and near-real-time meteorological data, combined
with machine learning, can produce a usable flood-risk estimate ahead of an event — and
delivers that estimate as decision-support intelligence, not a guarantee.

## 2. Users and stakeholders

- **Citizens and communities** in monitored areas — need a plain-language current risk
  level and, where relevant, an alert.
- **Farmers** — need risk trends relevant to agricultural planning.
- **Disaster-management personnel and local authorities** — need a dashboard with
  risk history, model confidence, and explanations to support decisions, plus the
  ability to review citizen reports.
- **Emergency-response organizations** — same as above, plus location/geospatial context.
- **Researchers / academic reviewers** — need reproducible methodology, honest metrics,
  and documented limitations (this is an academic research project first).

## 3. Scope (MVP)

In scope:
- Historical meteorological data ingestion from a documented, real source (Phase 1–2).
- A validated, documented flood-risk target/proxy (Phase 1).
- A baseline model comparison (Logistic Regression, Decision Tree, Random Forest,
  Gradient Boosting, XGBoost) evaluated on chronologically held-out data (Phase 5, 7).
- An LSTM candidate evaluated on the same basis, kept only if it earns its complexity
  (Phase 6, 7).
- Explainability for predictions (SHAP / feature importance) (Phase 8).
- A FastAPI backend serving predictions from a saved model artifact, with a PostgreSQL
  database as the source of truth for observations, predictions, and alerts (Phase 10–11).
- A React + TypeScript dashboard showing only real, database- or API-backed data, with
  explicit loading/empty/error states (Phase 12).
- An alert pathway (e.g. SMS) isolated behind an Alert Service so its failure never takes
  down prediction serving (Phase 13).

Explicitly out of scope for MVP:
- Physical IoT sensors / hardware of any kind.
- Guaranteed-accuracy claims or official-government-warning status.
- Any feature that requires fabricated or placeholder data to appear "complete."

## 4. Success criteria

This project succeeds if it produces an honest answer to the core research question
(`docs/RESEARCH-METHODOLOGY.md`) — including a negative or mixed answer — backed by a
working, tested, end-to-end pipeline from real data to a served prediction. It does not
succeed by hitting a specific accuracy number; a well-documented model that performs
modestly is a valid and reportable outcome (governing prompt, sections 42, 59).

## 5. Constraints

- Free/low-cost infrastructure only; paid services (SMS, hosting) must be optional and
  isolated (cost control, section 55).
- No physical sensor dependency.
- All scientific claims must be reproducible and traceable to real data or a documented,
  labelled proxy.

## 6. Requirements traceability

Detailed functional requirements will be added to `docs/SRS.md` once Phase 1 (data/label
strategy) is settled — writing detailed functional specs before the data and label
strategy are known would risk requirements that don't match what the data can actually
support.

# Project Memory

The source of truth for why FloodShield Zambia is built the way it is. Every major
decision is recorded here when made, with its rationale and status. When a decision
changes, the entry is updated in place with the new decision, the reason for the change,
and the date — the history is not deleted.

Status tags used throughout this document and the rest of `/docs`:
- **VERIFIED** — supported by authoritative documentation or research we have checked.
- **ASSUMED** — an engineering assumption made because information was unavailable; safe
  to act on but should be revisited.
- **TO VALIDATE** — an open research question that must be checked before being relied on.

---

## 2026-09-07 — Project initialization (Phase 0)

**Decision:** Start FloodShield Zambia from an empty repository as a fresh build, not a
migration of prior work.

**Why:** The working directory contained no existing code, data, models, or
documentation (confirmed by direct filesystem inspection — see the initialization
report delivered this session). There is nothing to preserve or migrate; Master Prompt
01's "do not delete existing work without justification" rule is therefore satisfied
trivially — there is no existing work.

**Status:** VERIFIED (directory contents directly inspected).

---

## 2026-09-07 — Governing prompt recorded

**Decision:** The full governing prompt ("Master Prompt 01 — Initiation, Research
Discovery & AI System Blueprint") is kept verbatim in
`prompts/MASTER-PROMPT-01-initiation-research-blueprint.md` as the development record.
This file (`PROJECT-MEMORY.md`) records decisions *made in response to* that prompt, not
the prompt's requirements themselves.

**Status:** VERIFIED.

---

## 2026-09-07 — Documentation-first, no premature code

**Decision:** This session scaffolds the repository structure and writes the
documentation foundation only. No data ingestion, model training, backend, or frontend
code is written yet.

**Why:** Master Prompt 01 section 61 explicitly requires an initialization analysis and
documentation foundation before implementation begins, and section 56 permits autonomous
continuation *after* a phase is understood and scoped — Phase 1 (Research & Data) has not
yet been scoped in detail (data source availability and the flood-label methodology are
both still TO VALIDATE — see below), so writing ingestion code now would risk being
built against assumptions that turn out to be wrong.

**Status:** VERIFIED (project-management decision, not a factual claim).

---

## 2026-09-07 — Backend/frontend/database stack

**Decision:** FastAPI (Python) backend, React + TypeScript frontend, PostgreSQL
database, as specified by Master Prompt 01 sections 25–27.

**Why:** Specified directly by the governing prompt; also a reasonable, well-supported,
free-tier-friendly stack for a student research project (FastAPI gives free OpenAPI
docs; PostgreSQL and React have large free-hosting footprints — see section 55, cost
control).

**Status:** ASSUMED to be the right fit until backend/frontend implementation begins;
no code exists yet to validate this against.

---

## 2026-09-07 — Candidate model set

**Decision:** Compare Logistic Regression, Decision Tree, Random Forest, Gradient
Boosting, and XGBoost as baselines, with LSTM evaluated afterward as a time-series
candidate — no model is assumed to win in advance.

**Why:** Specified directly by Master Prompt 01 sections 11–13, 59, and rule 9/10.
Reiterated here because it is the single most important anti-bias guard for this
project: nothing in this document should be read as pre-deciding that XGBoost or LSTM
will be the final model. That will be decided in Phase 7 (Model Evaluation) from actual
metrics on held-out data.

**Status:** VERIFIED as the plan; the outcome is TO VALIDATE by definition — that's the
research question.

---

## OPEN — Data source selection (Phase 1, not yet decided)

**Status:** TO VALIDATE. NASA POWER is the prompt's suggested primary historical source
(section 6) because it's free, global, does not require an API key for standard use, and
provides daily precipitation/temperature/humidity/wind/soil-moisture-proxy variables —
but this has not yet been re-verified against NASA POWER's current API terms and
documented in `docs/DATA-SOURCES.md` with an actual test request. CHIRPS/ERA5-Land and a
near-real-time provider (OpenWeather or equivalent) are candidates to investigate, not
commitments. No data has been downloaded yet.

## OPEN — Flood label / target methodology (Phase 1, not yet decided)

**Status:** TO VALIDATE. This is flagged by the governing prompt itself as the single
most important and highest-risk decision in the project (section 10). No target
variable has been defined. See `docs/ML-METHODOLOGY.md` for the candidate approaches and
`docs/RESEARCH-METHODOLOGY.md` for how this will be resolved. Do not proceed to feature
engineering or modelling before this is settled and documented here.

## OPEN — Prediction horizon (Phase 1/6, not yet decided)

**Status:** TO VALIDATE. The achievable horizon depends entirely on the temporal
resolution of whichever historical dataset is selected (daily NASA POWER data does not
support an hourly-horizon claim). No horizon is committed to yet — see
`docs/LIMITATIONS.md`.

## OPEN — Geographic scope (Phase 1, not yet decided)

**Status:** TO VALIDATE. Candidate areas named in the governing prompt (Lusaka, Kanyama,
Misisi, other flood-prone settlements, agricultural/riverine districts) are *examples*
from the prompt, not verified flood-prone designations. None of these should be
presented in any UI or document as "officially flood-prone" without a citable
authoritative source.

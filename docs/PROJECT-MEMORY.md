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

## OPEN — Data source selection (Phase 1, partially validated 2026-09-07)

**Status:** TO VALIDATE, updated. NASA POWER's Daily API endpoint, required/optional
parameters, format options, and rate-limit caution were confirmed against NASA's own
current documentation this session (see `docs/DATA-SOURCES.md`). A live JSON request for
a Zambian coordinate was attempted but blocked by this environment's fetch-approval gate
— that step still needs to be completed (either with the fetch approved, or by a human
running the request and sharing the response) before ingestion code is written. CHIRPS/
ERA5-Land and a near-real-time provider (OpenWeather or equivalent) remain candidates to
investigate, not commitments. No data has been downloaded yet.

## OPEN — Flood label / target methodology (Phase 1, advanced further 2026-09-07)

**Status:** TO VALIDATE, updated again. This is flagged by the governing prompt itself
as the single most important and highest-risk decision in the project (section 10). A
first real artifact now exists: `ai-engine/data/external/zambia_flood_events_log.csv`,
eleven sourced flood events across Zambia (Jan 2020 – Jan 2026), compiled from FloodList,
UN-SPIDER, and International Charter activation reporting. This is not yet a finished
label — it has no negative examples, is media-derived rather than pulled from a primary
government dataset, is a small sample (11 events), and contains one unresolved date
discrepancy (documented in the file itself). DMMU's own site remains unreachable from
this session, so it has not yet been used as a primary cross-check. See
`docs/ML-METHODOLOGY.md` and `docs/LIMITATIONS.md` for the implications. **Decision not
yet made:** whether this event log becomes the primary label (supplemented with a
constructed negative class) or is used only to validate a rainfall-accumulation proxy
built independently. Do not proceed to feature engineering or modelling before this is
settled and documented here.

## OPEN — NASA POWER live verification (Phase 1/2, blocked in this environment,
2026-09-07)

**Status:** TO VALIDATE, blocked. Two independent live-request attempts against NASA
POWER's Daily API this session failed for different reasons: this sandbox's egress
policy blocks a direct `curl` to `power.larc.nasa.gov`, and the session's web-fetch tool
declines the same URL because NASA's `robots.txt` disallows automated fetching of `/api/`
paths. The endpoint shape, parameters, and formats are still confirmed from NASA's own
documentation (see `docs/DATA-SOURCES.md`), so Phase 2 ingestion code can be written
against that specification — but its first real run, in an environment that can reach
NASA POWER directly, is the actual verification step and has not happened yet.

## OPEN — Prediction horizon (Phase 1/6, not yet decided)

**Status:** TO VALIDATE. The achievable horizon depends entirely on the temporal
resolution of whichever historical dataset is selected (daily NASA POWER data does not
support an hourly-horizon claim). No horizon is committed to yet — see
`docs/LIMITATIONS.md`.

## DECIDED (partially) — Geographic scope (Phase 1, updated 2026-09-07)

**Decision so far:** Kanyama compound, Lusaka, is upgraded from "named in the governing
prompt" to a **VERIFIED, independently-sourced candidate location** — it is documented
as flood-affected in peer-reviewed/graduate research (a University of Zambia thesis and
a journal article on flooding's effect on sanitation there), not merely asserted by the
prompt. Ng'ombe settlement, Lusaka, is added as a second credible candidate on the same
basis. The January 2023 flood event additionally documents real, dated flooding in
Southern, Central, and Lusaka provinces, with district-level detail for Luapula,
Kabompo, Lukulu, Senanga, Kitwe, Mambwe, and Solwezi (DMMU/WARMA via UN-SPIDER/Charter
sources — see `docs/DATA-SOURCES.md`).

**Why:** The governing prompt explicitly requires that no location be called
"officially flood-prone" without a citable authoritative source (section 3). Kanyama and
Ng'ombe now have one; the rest of the prompt's example list (Misisi, and "agricultural/
riverine regions" generally) still does not and remains an unverified example, not a
decision.

**Still TO VALIDATE:** final selection of which 1–3 locations the MVP will actually
model (a scope decision, not just an evidence question), and confirmation that NASA
POWER's grid resolution meaningfully distinguishes these Lusaka-compound-level locations
from each other (they are geographically close together).

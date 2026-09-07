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

## 2026-09-07 — Full backend implementation & end-to-end integration build

**Decision:** In response to a third, 79-section master prompt, built out real auth
(JWT + bcrypt + 5-role RBAC), Alembic migrations, an expanded schema (users, roles,
citizen reports, data-source catalog, audit log), new endpoints (citizen reports,
model registry, data-source health checks), standardized error responses, pagination,
rate limiting, a 42-test pytest suite against a real Postgres test database, and
frontend integration for all of it (real login/signup, RBAC-gated alert creation,
citizen reports and AI-model/data-source screens rebuilt from stubs/static content
into real API-backed screens). Followed the prompt's own required order: an audit
(`docs/backend/frontend-integration-matrix.md`) was written and committed *before* any
backend code changed, inspecting the existing skeleton's models/schemas/API/services
and every frontend page's real data needs.

**Why:** Explicit user request (the full master prompt), continuing this project's
established pattern of building real functionality against real data and documenting
honestly what is and isn't done, rather than fabricating completeness.

**Notable decisions made along the way:**
- **Alert creation now requires authentication** (previously anonymous). An
  unauthenticated public dashboard should not be able to issue flood alerts to a
  citizen audience — this is a deliberate behavior change, recorded here rather than
  silently shipped.
- **Roles implemented as a real `roles` table**, not a hardcoded Python enum, so the
  schema genuinely reflects the "Roles" entity the prompt specifies — at the cost of
  needing a human/script to grant elevated roles (no admin UI for it yet).
- **Password hashing switched from the spec's implied passlib+bcrypt to the `bcrypt`
  library used directly.** passlib 1.7.4's bcrypt backend threw a real
  `AttributeError: module 'bcrypt' has no attribute '__about__'` against
  `bcrypt>=4.1` — a genuine dependency incompatibility, not a design choice avoided
  for convenience. Verified real bcrypt hashing still happens (hashes start with
  `$2b$`, round-trip correctly, 72-byte truncation handled) via
  `backend/tests/unit/test_security.py`.
- **One baseline Alembic migration**, not an incremental history matching the
  skeleton's build order. The dev database was dropped and recreated from empty before
  autogenerating it, since no data existed yet worth preserving through incremental
  migrations — this is a one-time exception; all schema changes from here on get their
  own migration.
- **Explicitly not built this round** (see `docs/backend-architecture.md`, "Not yet
  built" and `docs/ROADMAP.md`'s note on this build, for the full list): SHAP
  explanations (no trained model exists to explain — building this now would mean
  fabricating explanations against nothing), alert delivery to an external channel (no
  SMS/email provider configured, unchanged from before), an admin role-management UI,
  a `/auth/refresh` consumer (refresh tokens are issued but nothing exchanges them
  yet), and a Playwright suite committed to the repo (QA was real — Playwright against
  the real running stack — but the script lived in the session scratchpad, not
  `frontend/tests/`).

**Status:** VERIFIED (built and tested this session — 42/42 backend pytest tests
passing against a real separate Postgres test database, frontend `tsc -b --noEmit`
clean, full login→create-alert→sign-out→signup→submit-citizen-report flow verified
end-to-end with a real headless-Chromium Playwright run against the real backend, no
horizontal overflow at 1440px/390px on every touched screen). Full detail in
`docs/backend-architecture.md`, `docs/api-inventory.md`, `docs/database-schema.md`,
and `docs/verified-screens.md`.

---

## 2026-09-07 — Dark design system + multi-screen UI built against a reference spec

**Decision:** Implemented the user-supplied UI specification (dark navy/blue/green/gold
palette, risk color scale, persistent app shell, ~20 of 26 named screens) as real,
data-backed React screens rather than static mockups matching the reference image
pixel-for-pixel.

**Why:** The spec itself (its own sections 28, 29, 48, 54) prohibits fabricating
metrics, predictions, model accuracy, or system health to "fill the page" — which is
exactly what a literal pixel-for-pixel recreation of the reference mockup would require,
since that mockup shows invented KPI numbers, a populated model-comparison table, and
fake alerts. Resolved this by keeping the mockup's visual language (colors, layout
rhythm, component shapes) while sourcing every value from a real API call, and using
the spec's own required empty/error states (sections 30–32) wherever no real data
exists yet — which is most analytics/prediction surfaces, since no model is trained.
Added a real `alerts` table + endpoints so Alerts/Create Alert are genuinely functional,
not just styled to look that way.

**Status:** VERIFIED (built and tested this session — typecheck clean, no horizontal
overflow at 1440px/390px, end-to-end alert-creation flow tested with Playwright, one
real mobile bug found and fixed). Full screen coverage against the spec's 26-screen
checklist and remaining gaps are recorded in `docs/UI-UX.md`.

---

## 2026-09-07 — Backend/frontend skeleton built out of phase order

**Decision:** Stood up a minimal but real FastAPI backend (PostgreSQL 16, provisioned
locally) and a React+TypeScript dashboard — Phases 10–12 — before Phase 1's flood-label
decision was resolved.

**Why:** Explicit user request ("run the app"). When asked to clarify since nothing was
buildable yet, the user chose to see a minimal real system now rather than wait for the
phase order. This is a deliberate, requested exception to the project's own default
sequencing (governing prompt §61's "do not build the entire system yet"), not a
reversal of that principle — the skeleton only exposes data that already exists (the
seeded locations and the 11-row flood-event log) plus honest empty/error states for
everything that doesn't exist yet (predictions, weather observations). No fabricated
data was introduced to make it "look more done." `docs/ROADMAP.md` records that Phases
10–12 are "skeleton only," not complete, and that Phase 2+ substantive work should still
wait on the Phase 1 label decision.

**Status:** VERIFIED (built and manually tested this session — curl against every
endpoint, headless-browser screenshots at desktop and mobile widths, one real bug found
and fixed: error-message overflow causing horizontal scroll).

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

# Roadmap — FloodShield Zambia

Phases as defined by the governing prompt (`prompts/MASTER-PROMPT-01-...md`, section 48).
Each phase is only marked complete once implemented **and** tested (Definition of Done,
section 41) — not merely scaffolded.

| Phase | Name | Status |
|---|---|---|
| 0 | Discovery | **Complete** — repository was empty; scaffold + documentation foundation created 2026-09-07. |
| 1 | Research & Data | **In progress** (started 2026-09-07). NASA POWER endpoint/params confirmed from docs (live request confirmed blocked in this environment — needs an environment that can reach the API directly, e.g. Phase 2 development). A first hand-compiled, sourced flood-event log (11 events, 2020–2026) now exists at `ai-engine/data/external/zambia_flood_events_log.csv`. Kanyama and Ng'ombe upgraded to independently-verified candidate locations. Flood-label decision (event-log-based vs. proxy) and final geographic scope still open. |
| 2 | Data Ingestion | Not started |
| 3 | Preprocessing | Not started |
| 4 | Feature Engineering | Not started |
| 5 | Baseline Models | Not started |
| 6 | Time-Series Model (LSTM) | Not started |
| 7 | Model Evaluation | Not started |
| 8 | Explainable AI | Not started |
| 9 | Model Packaging | Not started |
| 10 | Backend | **Skeleton only** (built 2026-09-07, out of normal order, at explicit user request — see below). Not "done" against §41. |
| 11 | Database | **Skeleton only**, same caveat. Real PostgreSQL 16, matching the target architecture. |
| 12 | Frontend | **Skeleton only**, same caveat. One dashboard screen. |
| 13 | Alerts | Not started |
| 14 | Testing | Ongoing per-phase from Phase 1 onward, plus a dedicated system-testing pass. Skeleton was manually verified (curl + headless-browser screenshots at two viewport widths) but has no automated test suite yet. |
| 15 | Deployment | Not started |

## Note: full UI redesign built (2026-09-07, same day, second request)

The user then supplied a detailed UI specification (dark design system, 26-screen
list) asking to recreate a reference dashboard mockup as a real, functional app. Built:
the full design-token system, a persistent/collapsible app shell, and ~20 of the 26
named screens — every one that could be backed by real data or an honest empty state.
Added real backend support for it: an `alerts` table with working create/list (verified
end-to-end: a form submission produces a real row that appears immediately), and a
`/system-status` endpoint that computes each component's status at request time (DB
ping, real row counts) rather than hardcoding "Operational." Deferred: Signup, separate
How-It-Works/Methodology pages (folded into About), Prediction/Citizen-Report detail
pages (no data yet to show), Data Quality, a React error boundary, and role-based
permissions. See `docs/UI-UX.md` for the full screen-by-screen account, including one
real responsive bug found (mobile tables had no card fallback rendered) and fixed
during QA.

## Note: Phases 10–12 built early (2026-09-07)

The user explicitly asked to "run the app" and, when asked to clarify given nothing was
buildable yet, chose to have a minimal real backend+frontend stood up immediately rather
than wait for the full phase order. What exists now: a FastAPI backend against a real
local PostgreSQL 16 database, seeded with the real location list and the real 11-row
flood-event log (no synthetic data), a `/weather/{id}/ingest` endpoint that makes a
genuine NASA POWER request and reports honest success/failure, a `/predictions` endpoint
that correctly returns empty (no model exists), and a React+TypeScript dashboard
rendering all of it with real loading/success/empty/error states — screenshotted via
headless Chromium to confirm it actually runs. See `docs/API.md`, `docs/DATABASE.md`,
and `docs/UI-UX.md` for exactly what is and is not implemented. This does **not**
retroactively satisfy the Definition of Done for Phases 10–12 (no auth, no tests, no
alerts, no citizen reports, no trained model to predict from) and does not change the
fact that Phase 1's flood-label decision is still open — Phase 2+ ingestion/modelling
work should still wait on that decision per the note below.

## Progress log (Phase 1)

**2026-09-07:**
1. ~~Verify NASA POWER API access~~ — **as far as this environment allows, done.**
   Confirmed endpoint pattern, required/optional parameters, formats, and rate-limit
   behavior against NASA's own docs. Two independent attempts at a live JSON request
   both failed structurally (sandbox egress policy, then robots.txt) rather than
   transiently — this cloud session cannot complete this step. **Still needed:** the
   actual live verification, which now belongs to Phase 2 (first real ingestion run in
   an environment that can reach `power.larc.nasa.gov` directly).
2. ~~Investigate flood-event ground truth~~ — **turned into a real artifact.**
   DMMU (Office of the Vice President) and WARMA are Zambia's confirmed authoritative
   bodies (DMMU's own site remains unreachable — retry or contact directly); a
   hand-compiled log of 11 sourced flood events (2020–2026) now exists at
   `ai-engine/data/external/zambia_flood_events_log.csv`, built from FloodList,
   UN-SPIDER, and Charter-activation reporting. **Still needed:** decide whether this
   becomes the primary label (with a constructed negative class) or a validation check
   against a rainfall-accumulation proxy instead — see `docs/ML-METHODOLOGY.md`.
3. ~~Narrow geographic scope~~ — **partially done.** Kanyama compound and Ng'ombe
   settlement (both Lusaka) are now independently verified via peer-reviewed/graduate
   research as flood-affected, not just named by the prompt. **Still needed:** commit to
   the final 1–3 MVP locations and confirm NASA POWER's grid resolution can usefully
   distinguish them.

## Remaining steps (Phase 1)

4. Write `docs/DATA-DICTIONARY.md` once a source and variable set are confirmed.
5. Decide the flood-label methodology and record the decision (not just the candidates)
   in `docs/PROJECT-MEMORY.md`.
6. Commit to final geographic scope.

Do not begin Phase 2 (ingestion code) until item 5 has a documented working answer —
building ingestion around the wrong target variable would waste the phase.

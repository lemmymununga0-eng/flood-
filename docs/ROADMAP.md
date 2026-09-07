# Roadmap — FloodShield Zambia

Phases as defined by the governing prompt (`prompts/MASTER-PROMPT-01-...md`, section 48).
Each phase is only marked complete once implemented **and** tested (Definition of Done,
section 41) — not merely scaffolded.

| Phase | Name | Status |
|---|---|---|
| 0 | Discovery | **Complete** — repository was empty; scaffold + documentation foundation created 2026-09-07. |
| 1 | Research & Data | **In progress** (started 2026-09-07). NASA POWER endpoint/params confirmed from docs (live request still blocked — see below); real DMMU/WARMA/Charter ground-truth candidates identified; Kanyama and Ng'ombe upgraded to independently-verified candidate locations. Flood-label decision and final geographic scope still open. |
| 2 | Data Ingestion | Not started |
| 3 | Preprocessing | Not started |
| 4 | Feature Engineering | Not started |
| 5 | Baseline Models | Not started |
| 6 | Time-Series Model (LSTM) | Not started |
| 7 | Model Evaluation | Not started |
| 8 | Explainable AI | Not started |
| 9 | Model Packaging | Not started |
| 10 | Backend | Not started |
| 11 | Database | Not started |
| 12 | Frontend | Not started |
| 13 | Alerts | Not started |
| 14 | Testing | Ongoing per-phase from Phase 1 onward, plus a dedicated system-testing pass |
| 15 | Deployment | Not started |

## Progress log (Phase 1)

**2026-09-07:**
1. ~~Verify NASA POWER API access~~ — **partially done.** Confirmed endpoint pattern,
   required/optional parameters, formats, and rate-limit behavior against NASA's own
   docs. A live JSON test request was attempted but blocked by this environment's fetch-
   approval gate (direct `curl` is blocked by egress policy; the fetch tool's request for
   the live API URL needs explicit approval that wasn't given in time). **Still needed:**
   get that live request approved and run, or have a human run it and share the response,
   before Phase 2 ingestion code is written.
2. ~~Investigate flood-event ground truth~~ — **real candidates found, not yet a
   dataset.** DMMU (Office of the Vice President) and WARMA are Zambia's confirmed
   authoritative bodies; DMMU publishes situation reports (its own site was unreachable
   this session — retry or contact directly); International Charter Activation #796
   produced real Sentinel-2B flood-extent products for Jan–Feb 2023 Zambia flooding.
   **Still needed:** turn these into an actual event table, or make the documented call
   to fall back to a rainfall-accumulation proxy instead.
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

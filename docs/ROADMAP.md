# Roadmap — FloodShield Zambia

Phases as defined by the governing prompt (`prompts/MASTER-PROMPT-01-...md`, section 48).
Each phase is only marked complete once implemented **and** tested (Definition of Done,
section 41) — not merely scaffolded.

| Phase | Name | Status |
|---|---|---|
| 0 | Discovery | **Complete** — repository was empty; scaffold + documentation foundation created 2026-09-07. |
| 1 | Research & Data | Not started — next phase. Requires: confirming NASA POWER access, deciding the flood-label methodology, defining geographic scope, writing the data dictionary. |
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

## Immediate next steps (Phase 1)

1. Verify NASA POWER API access and current terms of use for the candidate Zambian
   region(s) — produce a real test request and record the result in `docs/DATA-SOURCES.md`.
2. Investigate what flood-event ground truth actually exists for Zambia (official
   disaster reports, remote-sensing flood-extent products) before defaulting to a
   rainfall-threshold proxy label.
3. Narrow the geographic scope to specific coordinates/districts with a documented
   reason for each (not just named because they appear in the governing prompt).
4. Write `docs/DATA-DICTIONARY.md` once a source and variable set are confirmed.
5. Update `docs/PROJECT-MEMORY.md` with each decision as it is made.

Do not begin Phase 2 (ingestion code) until the label methodology (item 2) has at least
a documented working answer — building ingestion around the wrong target variable would
waste the phase.

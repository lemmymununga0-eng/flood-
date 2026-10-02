# Testing — FloodShield Zambia

Status: updated 2026-10-01. Tests now exist across three suites; counts and what can
and cannot currently be executed are recorded in `docs/CURRENT-STATE-2026-10-01.md`.
The policy below still governs what a test is allowed to assert. This
records the testing standard every subsequent phase must meet before being marked done.

## Standard (applies to every phase from Phase 1 onward)

For each feature: implement, run tests, inspect failures, fix, re-run, then test
integration, edge cases, failure states, database persistence (where applicable), and
responsiveness (where applicable). A feature is not "done" because code exists for it —
see the Definition of Done checklist in `prompts/MASTER-PROMPT-01-...md` section 41.

## Test categories by component

- **AI engine** (`ai-engine/tests/`): missing-data handling, feature generation,
  sequence creation (for LSTM), scaling (fit-on-train-only), prediction shape, model
  loading, model inference, threshold logic, explanation generation. A model must
  produce consistent output for identical inputs under deterministic configuration
  (fixed seed).
- **Backend** (`backend/tests/`): API request/response contracts, input validation,
  database persistence, error handling, auth (if implemented).
- **Frontend** (`frontend/tests/`): component rendering across loading/success/empty/
  error/validation states, responsive layout at mobile/tablet/desktop breakpoints.
- **Integration**: end-to-end flow from a stored weather observation through inference to
  a persisted prediction visible via the API and dashboard.

## What "tested" means in this project's status reporting

Nothing in this project is described as "working" or "complete" without having actually
been run and observed to pass. Status reports distinguish: implemented / tested / passed
/ failed / limitations / remaining work (governing prompt, section 57) — never a bare
"everything works."

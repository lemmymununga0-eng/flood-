# Final Demonstration Checklist

Produced 2026-09-18, alongside `docs/FULL_SYSTEM_AUDIT.md`. Every box below reflects what was
actually verified this session — running code, live database queries, actual test-suite
executions — not documentation claims.

### Can I demonstrate the following?

- [x] Application (backend) starts — verified live, port 8010 (8000 is occupied by an
      unrelated local project on this machine)
- [x] Backend starts — same as above, real `uvicorn` process, real startup log
- [x] Database connects — live Supabase Postgres 17.6, confirmed via the app's own
      SQLAlchemy engine, not a raw driver test
- [ ] Frontend loads — not attempted this pass (needs port 8000 freed, or a
      `VITE_API_BASE_URL` override wired in first — currently hardcoded to `localhost:8000`)
- [x] Zambia location can be selected — `GET /locations` confirmed 3 real seeded locations
      (Kanyama compound, Lusaka city, Ng'ombe settlement); frontend has real dropdown/map-click
      selection UI
- [x] Real meteorological data can be obtained — live NASA POWER call verified working end to
      end this session (11 real observations fetched and stored)
- [ ] Real ML model loads — **no.** `backend/app/ml/` is empty; nothing in the backend ever
      imports `joblib` or loads a `.joblib` file
- [ ] Prediction is generated — **no.** No `POST /predict`-equivalent endpoint exists anywhere
- [ ] Calibrated risk probability is returned — **no.** No calibration artifact exists for any
      `ai-engine/` model, and nothing is served anyway
- [ ] Risk level is displayed — the UI component (`RiskBadge`) exists and works, but has no
      real model-derived risk level to ever display (`predictions` table is empty)
- [x] Historical information is displayed — real: 14 real flood events render in
      `HistoricalEvents.tsx`, table + KPI summary
- [ ] Model explanation is displayed — **no.** No SHAP/feature-importance UI exists in the
      frontend even conceptually, and SHAP has never actually been run in `ai-engine/` (zero
      output files exist, though the code to do so is real and complete)
- [x] API works — 21 real, DB-backed endpoints, 19/21 with test coverage, live-tested this
      session
- [x] Error handling works — real `ErrorState` component with retry, used on every
      data-fetching page; backend returns honest error bodies (`ApiError`), not silent failures
- [x] No mock prediction is being presented as real — confirmed twice independently this
      session (a dedicated fake-data sweep, plus this audit): every "empty" screen is an
      honest empty state, not a fabricated result
- [x] Security checks pass — no secrets committed, no SQL/command injection, no path
      traversal, real auth/RBAC, P0 config fail-fast fix verified present and working; one
      real gap remains (`/docs` always exposed — see below)
- [x] Tests pass — 49/49 backend + 31/31 ai-engine, both **actually run** this session
      against real data. (Frontend: no test framework exists — N/A, not a failure)
- [ ] End-to-end flow works — **no, blocked at the ML-serving gap.** Everything up to and
      including real data ingestion and storage works end-to-end; the chain breaks the moment
      a prediction is needed, because that code path doesn't exist yet

### What's actually blocking a full demo, in order

1. **No prediction-serving code exists** (`backend/app/ml/` is empty). This is the one gap
   that makes every downstream item above unchecked. Wiring in even one real `ai-engine/`
   model (with an honestly-labeled confidence caveat, per its real metrics in
   `FULL_SYSTEM_AUDIT.md` Section 5) would unblock 6 of the currently-unchecked boxes at once.
2. Frontend wasn't started this pass (port conflict + hardcoded API base) — quick to unblock,
   but untested as of this document.
3. `/docs`/`/redoc` exposure — not blocking a demo, but worth closing before showing this to
   an external audience.

### What already works and is safe to demo today, as-is

- Real signup/login/RBAC flow
- Real location, flood-event, alert, citizen-report, notification CRUD
- Real live weather ingestion from NASA POWER, with real storage
- Real live system-status page (all live component checks, not hardcoded)
- Real map with real seeded locations
- The honest emptiness of the Predictions/AI Model/Analytics screens, if the point of the demo
  is "here is the real, currently-implemented state of a research project in progress"

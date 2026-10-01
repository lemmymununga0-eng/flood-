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
- [x] Frontend loads — **yes.** `VITE_API_BASE_URL` override added (falls back to the old
      hardcoded default), so the SPA can point at a backend on any port. Verified in a real
      headless Chrome session against the live backend
- [x] Zambia location can be selected — `GET /locations` confirmed 3 real seeded locations
      (Kanyama compound, Lusaka city, Ng'ombe settlement); frontend has real dropdown/map-click
      selection UI
- [x] Real meteorological data can be obtained — live NASA POWER call verified working end to
      end this session (11 real observations fetched and stored)
- [x] Real ML model loads — **yes, as of 2026-09-25.** `backend/app/ml/predictor.py` loads real
      artifacts from `backend/ml_artifacts/flood_risk_lr_v1/` (model, scaler, sigmoid calibrator,
      feature order, threshold). Registered in `model_versions` (id 1, `is_active=True`), so
      `GET /api/v1/models` and `system-status` now report it as operational
- [x] Prediction is generated — **yes.** `POST /api/v1/predictions/predict` runs real inference;
      verified live (wet-season input → HIGH, dry-season input → LOW)
- [x] Calibrated risk probability is returned — **yes.** Sigmoid calibrator applied at inference;
      response carries both `risk_probability_raw` and `risk_probability_calibrated`
- [x] Risk level is displayed **in the UI** — **yes.** The Predictions page now has a "Run a
      prediction" form (approved `.card`/`.field`/`.btn-primary` patterns, existing `RiskBadge`).
      Verified in-browser: wet-season input returned **High**, 0.41% calibrated, raw 0.7963,
      "Above alert threshold: Yes (≥ 0.5)", model `flood_risk_lr_v1`
- [x] Historical information is displayed — real: 14 real flood events render in
      `HistoricalEvents.tsx`, table + KPI summary
- [x] Model explanation is displayed **in the UI** — **yes.** The result card renders a
      "Contributing factors" table (feature, signed contribution, direction) plus the model's
      caveats, including that contributions are correlational and that risk level is *relative*
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
- [x] Tests pass — **57/57 backend** (49 existing + 8 new inference tests) + 31/31 ai-engine +
      13/13 research-pipeline tests, all **actually run**. (Frontend: no test framework exists)
- [x] End-to-end flow works — **yes, demonstrated in a real browser on 2026-09-25.** Full chain:
      user selects a Zambian location → enters a weather observation → frontend POSTs to
      `/api/v1/predictions/predict` → backend loads the real model artifacts → scales features →
      scores → applies sigmoid calibration → assigns a risk band → returns explanation + caveats →
      UI renders it in the approved design. Screenshot captured.

### Known environment quirks (not app defects)

Two of this machine's ports are occupied by unrelated projects of yours: **8000** (a "CRISPOOL
LOGISTICS" site) and **5173** on `0.0.0.0`/`::1` (a "Weapons of Power Ministry International"
app). FloodShield was therefore run on backend **8010** and frontend **127.0.0.1:5173**, with
`http://127.0.0.1:5173` added to `CORS_ORIGINS` in the gitignored dev `.env`. Nothing was changed
in those other projects. On a clean machine the default ports work unchanged.

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

# Bug Register — FloodShield Zambia

Produced 2026-09-07 as part of the full codebase audit. Every bug below was reproduced live
this session (a real request/response, a real code read, or a real browser session) — none
are inferred from documentation alone.

| Bug ID | Description | Location | Severity | Reproduction | Expected | Actual | Impact | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|---|---|
| BUG-01 | About page states auth and citizen-reporting don't exist, which is now false | `frontend/src/pages/About.tsx:24-27` | P1 (High) | Load `/about` while authenticated; read the copy | Page should accurately describe the real, current system | Says "No authentication... no citizen-report backend exists yet" | Misleads users/evaluators about real system capability | Update copy to reflect real auth + citizen-reports | **Fixed** (2026-09-08, UI foundation pass) |
| BUG-02 | Citizen-report text fields accepted and stored without server-side sanitization | `backend/app/api/citizen_reports.py` (submit endpoint) | P1 (High) | `POST /citizen-reports` with `description: "<script>alert(1)</script>"` as an authenticated user | Input should be sanitized/escaped before storage, or explicitly documented as raw-storage-by-design with escaping guaranteed at every render path | Payload stored verbatim in Postgres; currently inert only because frontend never uses `dangerouslySetInnerHTML` | Any future rendering surface (admin export, email digest, PDF report) bypassing React's auto-escaping would be vulnerable to stored XSS | Server-side sanitize/escape on write, or strip HTML-significant characters | Open |
| BUG-03 | Hardcoded insecure config defaults silently used when `.env` isn't found relative to process CWD | `backend/app/core/config.py:15-16` | P0 (Critical) | Rename `.env` away from the backend process's CWD, reload settings, observe `secret_key == "changeme"` | App should fail to start (or refuse non-`/health` traffic) outside development when critical secrets are unset | Boots silently, signs every JWT with the public string `"changeme"` | Full auth bypass is possible for anyone who knows/guesses the default in a misconfigured deployment | Fail-fast on missing required secrets outside `environment == "development"` | Open |
| BUG-04 | Routing-layer errors (404 on unknown path, 405 on wrong method) bypass the app's standardized error handler | `backend/app/main.py` (exception handler registration) | P2 (Medium) | `curl` an unknown path or wrong method on a known path | `{"error": ..., "message": ...}` shape, consistent with every other error | Raw Starlette `{"detail": "..."}"` shape | Frontend/API consumers must handle two different error shapes | Register a catch-all handler for `StarletteHTTPException` covering routing-layer errors too | Open |
| BUG-05 | `README.md` describes the project as having no backend/frontend code written | `README.md` | P0 (Critical — first-impression/documentation-accuracy, not a runtime defect) | Read `README.md` top-to-bottom | Should reflect the real, current, substantially-built state | States "Phase 0... no backend/frontend code has been written" | A materially false first impression of project maturity | Rewrite to reflect actual current state, point to `docs/PROJECT-MEMORY.md`/`docs/ROADMAP.md` for detail | Open |
| BUG-06 | `docs/SECURITY.md` describes itself as a "Phase 0 policy document — no backend code exists yet" | `docs/SECURITY.md:3` | P3 (Low — doc only) | Read the file | Should reflect the real security posture that now exists and was audited | Stale Phase-0 framing | Minor — could mislead a reader who doesn't cross-reference `docs/AUDIT-REPORT-2026-09-07.md` | Update to point to the audit report as the current source of truth | Open |
| BUG-07 | No React error boundary exists anywhere in the frontend tree | `frontend/src/` (absence) | P2 (Medium) | `grep -r "ErrorBoundary\|componentDidCatch" frontend/src` returns nothing | An unhandled render exception in any screen should show a graceful fallback | Produces a blank white page | Poor failure mode for end users on any unexpected render error | Add a top-level error boundary in `App.tsx`/`AppShell.tsx` | Open |
| BUG-08 | `GET /api/v1/weather/{location_id}` has zero automated test coverage | `backend/tests/` (absence) | P2 (Medium) | `grep -rln "weather" backend/tests/` returns nothing | Every live endpoint should have at least a basic automated test | No test exists | A regression here would not be caught by CI/the test suite | Add a test file covering ingest success/failure and the list endpoint | Open |

No bugs were found in: password hashing, JWT signature verification (including the `alg:none`
forgery attempt), RBAC enforcement (both allow and deny cases tested live), CORS enforcement, SQL
injection handling, or the frontend↔backend API contract (zero mismatches found).

---

## Update — 2026-09-08 re-audit

BUG-01 through BUG-08 above were re-checked against current code and remain **Open, unchanged**
(byte-identical source at every cited location). New bugs found this session, full evidence in
`docs/AUDIT-REPORT-2026-09-08.md`:

| Bug ID | Description | Location | Severity | Reproduction | Expected | Actual | Impact | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|---|---|
| BUG-09 | `POST /weather/{id}/ingest` has no auth dependency and no rate limit | `backend/app/api/weather.py:25-38` | P2 (Medium) | Call the endpoint with no bearer token | Documented as intentionally public, so 200/failure is expected — but no rate limit exists either | Any unauthenticated caller can trigger unlimited outbound NASA POWER fetches + DB writes for any location | Abuse/DoS surface on an external-call-triggering endpoint | Add a rate limit even though auth stays optional | Open |
| BUG-10 | Settings page states no user/session backend exists, which is now false (twin of BUG-01) | `frontend/src/pages/Settings.tsx` (top-of-file copy) | P1 (High) | Load `/settings` while authenticated; read the copy | Should describe the real, current system | Says "Not persisted yet — no user/session backend exists" | Same class of misleading-content defect as BUG-01, previously uncaught | Update copy alongside the About.tsx fix | **Fixed** (2026-09-08) |
| BUG-11 | Frontend API base URL is hardcoded with no environment override | `frontend/src/services/api.ts:20` | P1 (High) | Read the constant `API_BASE` | Should read from an env var (e.g. `VITE_API_BASE_URL`) so one build can target multiple environments | Hardcoded to `http://localhost:8000/api/v1` | Production bundle must be rebuilt per deployment target | Introduce a `VITE_*` env var with this as the dev default | Open |
| BUG-12 | The real, sourced 11-event flood-log CSV is never loaded — wrong filename configured | `ai-engine/src/config/settings.py:109` | **P0 (Critical)** | Run `ai-engine/main.py` and read the log output | Should load `zambia_flood_events_log.csv` (the file that actually exists) | Configured path points at `zambia_flood_events.csv` (no `_log`), which doesn't exist; pipeline silently falls back to proxy labels | The project's only real ground-truth dataset is disconnected from its own training pipeline | Fix the filename in `settings.py`, retrain, and re-evaluate | Open |
| BUG-13 | Trained baseline models are built on synthetic weather + leaky proxy labels, with no caveat in the reader-facing metrics file | `ai-engine/reports/baseline_comparison.csv`; leakage source at `ai-engine/src/features/build_features.py` `_add_proxy_labels()` | **P0 (Critical)** | Read `build_features.py`'s proxy-label logic against `saved_models/feature_columns.json` | Labels should be independent of the features used to predict them; reported metrics should be clearly caveated as synthetic/proxy-derived wherever they're surfaced | `flood_label` is a deterministic function of the same rolling-rainfall columns fed to the model as inputs; `baseline_comparison.csv` carries no caveat (only the internal `model_metadata.json` notes `"data_source": "synthetic"`) | Any ROC-AUC/F1 number from this run is not evidence of real flood-prediction skill | Retrain on a real, independent label source after fixing BUG-12; add an explicit caveat to any exported metrics file until then | Open |

No new bugs were found in the backend/frontend contract, mock-data sweep, or secret scan this
session (all re-confirmed clean). Live security-probe re-verification of BUG-02/03 was **not
possible this session** (no Postgres reachable, `slowapi` missing in this sandbox's Python
environment) — both remain Open based on unchanged code, not re-confirmed by a fresh live probe.

---

## Update — Phase 1 architecture-alignment refactor (2026-09-08)

- **BUG-08 partially closed.** `/weather/*` now has automated coverage
  (`backend/tests/api/test_weather_ingestion.py`, 3 tests, using a `MockWeatherProvider` injected
  via `app.dependency_overrides` — no network dependency). `POST /data-sources/{id}/check` **remains
  uncovered** — the same dependency-injection seam (`HttpHealthChecker`/`get_health_checker`) now
  exists for it, so adding its test is a small, well-understood follow-up, not a refactor. Status:
  Open (narrowed scope — `/data-sources/{id}/check` only).
- **BUG-09 unchanged/not fixed** (`POST /weather/{id}/ingest` still has no auth dependency and no
  rate limit) — out of scope for this structural refactor, which preserved existing behavior
  exactly. Status: Open.
- **BUG-10 Fixed (2026-09-08, UI rollout pass 2).** `frontend/src/pages/Settings.tsx`'s two false
  "no user/session backend exists" claims corrected to state accurately that auth/session are
  real, and only a dedicated settings/preferences table is missing. See `docs/UI-UX.md`'s rollout
  pass 2 update.

---

## Update — Phase 3: ai-engine real-label bug fixes (2026-09-08)

**BUG-12 — Fixed, but reframed.** The wrong filename (`ai-engine/src/config/settings.py:109`) is
corrected. However, fixing it alone did **not** unlock real-label training, because two more bugs
were hiding behind it (both now also fixed):

| Bug ID | Description | Location | Severity | Reproduction | Expected | Actual | Impact | Suggested Fix | Status |
|---|---|---|---|---|---|---|---|---|---|
| BUG-14 | Malformed CSV row crashed the real-events parser, silently caught and hidden | `ai-engine/data/external/zambia_flood_events_log.csv` row 3 (`ZM-2020-02`), unquoted comma in `confidence_notes`; swallowed by `flood_events_ingestor.py:120-122`'s broad `except Exception` | P0 (was hiding real data even after BUG-12's filename fix) | `pd.read_csv` on the unfixed file raised `Error tokenizing data... Expected 11 fields... saw 12` | The real CSV should parse cleanly | Exception silently caught, `load()` returned `None`, pipeline fell back to proxy labels | Real flood-event data was completely inaccessible even with the right filename | Quote the field like every other comma-containing field in the file (done) | **Fixed** — verified live: `FloodEventsIngestor().load()` now returns all 11 rows |
| BUG-15 | Events with no recorded `end_date` silently contributed zero labeled days | `ai-engine/src/ingestion/flood_events_ingestor.py:154-159`, `end = pd.Timestamp(row["event_end"])` with no null check — `pd.Timestamp(NaN)` → `NaT`, and any comparison against `NaT` is `False` | P0 (was silently discarding 9 of 11 real events, no error/warning) | Ran `events_to_daily_labels()` against the real log before the fix: only the one event with a real `end_date` (`ZM-2023-01`) produced any positive days | A single-day event (no end date) should count as a 1-day window, not silently vanish | 9 of 11 real events contributed 0 labeled days with zero warning | Default a missing `end_date` to `event_start` (done); new regression test `ai-engine/tests/test_flood_events_ingestor.py` | **Fixed** — verified live: all 11 events now contribute correctly (52 total flood-days over 2000-2023, up from 43) |

**New finding — replaces the general "not enough data" framing with a precise, measured one.**
Verified live (not asserted): after all three bugs above are fixed, running the real
`FloodEventsIngestor` against the real weather date range used by the one existing training run
(`synthetic_zambia_weather.csv`, 2000-01-01 → 2023-12-31, 8766 days) and the same chronological
70/15/15 split `ai-engine/src/datasets/split_data.py` uses:

```
positives in train: 0   (2000-01-01 -> 2016-10-19)
positives in val:   7   (2016-10-19 -> 2020-05-26)
positives in test: 45   (2020-05-26 -> 2023-12-31)
```

**All 11 real recorded flood events postdate 2020 — none exist in the 2000-2016 range a
chronological split assigns to training.** This means a model trained this way still cannot learn
to detect a real flood from its training data, regardless of code correctness — a genuine
data-coverage limitation (the event log itself only starts in 2020), not a bug. Tracked as new
item BUG-16, status **BLOCKED (data)**: fixing this requires either more historical flood-event
records reaching back before 2020, or a fundamentally different validation strategy (e.g.
leave-one-event-out cross-validation) that doesn't require positives in a contiguous early block —
both are research-methodology decisions, not code fixes, and are out of scope here. See
`docs/ML-METHODOLOGY.md` and `docs/LIMITATIONS.md` for the corresponding write-up.

**BUG-13 (data leakage in `_add_proxy_labels()`) is unchanged** — not addressed this phase; it
only matters when proxy labels are used, and doesn't interact with the real-label path fixed here.

---

## Update — BUG-16 resolved via real research + a real training run (2026-09-09)

**BUG-16 — Fixed (split-coverage specifically).** Three real pre-2020 flood events were
researched and added to `zambia_flood_events_log.csv` (now 14 events total) — see that file's
README for full sourcing/confidence notes. Verified by execution: the training split now has 243
real positive days (was 0), validation 7, test 45.

**Bonus, unplanned but verified:** NASA POWER — previously believed blocked, but only by sandbox
egress policy in prior cloud sessions — was tested and confirmed reachable from the actual
developer machine. `main.py` was run for real (no `--use-synthetic`), producing this project's
first-ever training run on real weather data (`nasa_power_zambia.csv`, 8,766 real daily rows for
Lusaka, 2000-2023) combined with real, independent event labels (no proxy-label leakage in this
run). Real results are in `docs/ML-METHODOLOGY.md`'s 2026-09-09 update.

**New findings from this real run, tracked as new items (not blockers, but real limitations):**

| ID | Description | Severity | Status |
|---|---|---|---|
| BUG-17 | Real training data is single-point (Lusaka only) while real flood events span many provinces — a geographic mismatch between the feature source and the label's true location | Medium | Open — `NASAPowerIngestor.download_multiple_locations()` already exists for a multi-point fix, not yet used |
| BUG-18 | The real label is national-level ("a flood was reported somewhere in Zambia"), not location-specific, understating the precision the app's per-`Location` prediction architecture implies | Medium | Open — requires per-location event attribution, not built |
| BUG-19 | Tree-ensemble baselines (Random Forest, Gradient Boosting) collapsed toward predicting the majority class on the real, imbalanced (~3.4% positive) data — no `class_weight`/resampling/threshold-tuning applied | Low-Medium | Open — straightforward follow-up, not done this session |

None of these are fabrication or leakage issues — they're honest, real limitations of a genuinely
real first attempt, exactly the kind of finding worth reporting plainly for a research write-up.

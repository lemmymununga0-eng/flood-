# Security — FloodShield Zambia

Status: updated 2026-10-01. The backend exists and has been audited against this policy;
findings and their current state are in `docs/CURRENT-STATE-2026-10-01.md` and
`docs/SYSTEM-FIX-PASS-2026-10-01.md`.
This records the requirements the implementation must meet from Phase 10 onward.

## Secrets

- No API keys, passwords, tokens, database credentials, or secret keys are ever
  hardcoded in source. All such values are read from environment variables via `.env`
  (local only, gitignored) with `.env.example` documenting every required variable
  without real values.
- `.env` must never be committed. `.gitignore` in this repository already excludes it.

## API security (Phase 10+)

- The backend validates every inbound payload: request bodies, location identifiers,
  dates, and numerical ranges — the frontend is never trusted as a validation layer.
- Authentication/authorization are added if the citizen-reporting or alert-management
  surfaces require them (to be decided in `docs/API.md` once those endpoints are
  designed).
- Rate limiting is applied to public-facing endpoints, particularly citizen report
  submission and any endpoint that triggers external API calls (weather providers, SMS).

## Data handling

- Uploaded citizen-report images are validated (type, size) before storage and never
  executed or served in a way that allows injection.
- Database credentials and any third-party API keys (weather providers, Twilio) are
  isolated to backend configuration and never exposed to the frontend bundle.

## Dependency and infrastructure hygiene

- `requirements.txt` (Python) and `frontend/package.json` (once created) pin versions
  for reproducibility, per `docs/RESEARCH-METHODOLOGY.md`'s reproducibility commitment.
- Free-tier infrastructure choices (section 55, cost control) do not exempt the project
  from these requirements — a free database still needs a real, non-default password.

This document will be expanded with concrete findings once the backend exists and can
actually be tested against it (see `docs/TESTING.md`).

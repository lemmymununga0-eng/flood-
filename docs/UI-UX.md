# UI/UX — FloodShield Zambia

Status: **early skeleton**, built 2026-09-07 ahead of the normal phase order (see
`docs/API.md`). One screen only: a single dashboard, React + TypeScript + Vite, styled
with plain CSS (no component library yet).

## Screen: dashboard (`frontend/src/App.tsx`)

Four panels, each independently fetched and each implementing its own loading / success
/ empty / error state (governing prompt §36):

- **Monitored locations** — real seeded locations with coordinates, confidence level,
  and a source link.
- **Historical flood-event log** — the 11 real, sourced events, explicitly labelled as
  "not a validated ground-truth label."
- **Weather data ingestion** — a button per location that triggers a real NASA POWER
  fetch attempt and displays the honest result (including the raw error when it fails,
  which it currently always does in this sandbox — see `docs/DATA-SOURCES.md`).
- **Flood-risk predictions** — always empty right now, with an explicit empty state
  explaining why (no model trained yet) rather than a blank panel or an invented number.

## Responsive testing performed

Screenshotted via headless Chromium (Playwright) at 1280×900 (desktop) and 390×844
(mobile, iPhone-sized). Found and fixed one real bug: long error text in the weather
panel overflowed its container and caused page-level horizontal scroll — fixed with
`overflow-wrap`/`word-break` on the message boxes and `overflow-x: hidden` on `html,
body`. Confirmed no horizontal scroll at either width after the fix (verified via
`document.documentElement.scrollWidth` === `clientWidth`). The flood-event table
scrolls horizontally *within its own container* on narrow viewports, which is the
correct pattern (per this project's own rule) rather than letting the whole page
overflow. Tablet-width and full cross-browser testing have not been done.

## Not yet implemented

Everything else in `docs/PRD.md`'s planned screen list (Risk Map, Analytics, Alerts,
Citizen Reports, Model Information, Settings), any design system/component library, and
any frontend automated tests (`frontend/tests/` is still empty).

# UI/UX — FloodShield Zambia

Status: **dark design system + multi-screen app**, built 2026-09-07 against the
project's UI specification (`prompts/` — recreation of a reference dashboard mockup).
Not a claim that Phase 12 (Frontend) is complete — see "Not yet implemented" below.

## Design system

CSS custom properties in `frontend/src/styles/tokens.css`, matching the spec's palette
exactly: Deep Navy (`#07111f`) background, Secondary Navy/Surface/Elevated Surface for
layering, Professional Blue/Environmental Green/Gold as brand accents, and a 4-level
risk scale (`--risk-low` green through `--risk-critical` red). Shared component classes
in `frontend/src/styles/components.css` (cards, KPI tiles, risk/status badges, buttons,
forms, tables with a mobile card fallback, loading/empty/error states). No inline
one-off colors — everything routes through the token file.

## App shell

`frontend/src/layouts/AppShell.tsx` — persistent sidebar (collapses to a slide-over
below 900px, toggled by a hamburger button) + top bar, shared by every authenticated
route via React Router's nested-route outlet. Landing, Login, and About render outside
the shell as public pages.

## Screens implemented

Dashboard, Risk Map (Leaflet, real location markers, no fake risk overlay), Location
Detail (real weather-ingestion demo), Predictions (real empty state), Analytics (honest
stub — nothing to show without real metrics), Historical Events + Historical Event
Detail (the real 11-event log), Alerts + Create Alert (real create/list against the
backend — verified end-to-end with Playwright: submitting the form creates a real DB
row that immediately appears on `/alerts`), Citizen Reports (honest stub — no backend
table), AI Model (honest stub), Data Sources, System Status (live, computed), Settings,
Profile, About, Notifications (honest stub), 404, plus Landing and Login.

## Not yet implemented

Signup, standalone How-It-Works/Methodology pages (folded into About instead),
Prediction Detail and Citizen Report Detail (no data to show yet), Data Quality, a
React error boundary, role-based permissions, and dark/light theme toggle (this build
is dark-only, matching the spec). Against the spec's 26-screen checklist this build
covers roughly 20, prioritizing every screen that could be backed by real data or a
real empty state over ones that would be pure static mockup.

## Verified

- Typechecked clean (`tsc -b --noEmit`).
- No horizontal overflow at 1440px, 390px (iPhone-sized), confirmed via
  `document.documentElement.scrollWidth === clientWidth` after Playwright screenshots
  of every implemented route at both widths.
- Found and fixed a real bug: the historical-events and predictions tables had a
  `.record-cards` mobile fallback class styled in CSS but never rendered in the
  component — on mobile the table (correctly hidden per the responsive table rule) had
  nothing to replace it, so the page was blank below the header. Fixed by actually
  rendering the card list; re-verified with a screenshot.
- The Leaflet map initializes and its controls/attribution render correctly, but OSM
  tile images do not load in this sandbox (same class of egress restriction as NASA
  POWER — see `docs/DATA-SOURCES.md`). The map is functionally correct code; tile
  loading is an environment constraint, not a code defect.

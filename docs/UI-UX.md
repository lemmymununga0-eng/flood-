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
backend, now RBAC-gated to ADMIN/ANALYST/OPERATOR — verified end-to-end with
Playwright, including the anonymous-denied case), Citizen Reports (rebuilt 2026-09-07:
real submit/list/moderate against `/citizen-reports`, no longer a stub), AI Model
(rebuilt 2026-09-07: fetches the real, empty `/models` registry instead of hardcoded
JSX), Data Sources (rebuilt 2026-09-07: fetches the real `/data-sources` catalog with
live-checked status instead of hand-written static content), System Status (live,
computed), Settings, Profile (rebuilt 2026-09-07: shows the real authenticated user),
Login (rebuilt 2026-09-07: real `POST /auth/login`, no longer a no-op form), Signup
(new 2026-09-07: real `POST /auth/register`), About, Notifications (honest stub), 404,
plus Landing. See `docs/verified-screens.md` for exactly how the 2026-09-07 changes
were re-verified.

## Not yet implemented

Standalone How-It-Works/Methodology pages (folded into About instead), Prediction
Detail and Citizen Report Detail single-item views (list views exist), Data Quality, a
React error boundary, an admin UI for granting roles (the backend has roles; nothing
in the frontend lets an ADMIN change another user's role yet), and dark/light theme
toggle (this build is dark-only, matching the spec). Against the spec's 26-screen
checklist this build covers roughly 22, prioritizing every screen that could be backed
by real data or a real empty state over ones that would be pure static mockup.

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

## Update — UI foundation pass (2026-09-08)

The user provided a full "Premium Professional Dark Mode" reference (23-screen mockup +
written token spec). Given the scope, a **foundation pass** was done first: design
tokens, the AppShell, and four flagship screens (Landing, Login/Signup, About,
Dashboard, Risk Map), with the remaining ~17 screens deferred to a follow-up pass.

**Tokens** (`frontend/src/styles/tokens.css`): the existing token system was already
very close to the spec. Added `--surface-highest` (4th elevation tier), `--brand-gold-2`/
`--brand-green-2` (secondary brand shades), refined `--risk-moderate` to the spec's gold,
promoted the one hardcoded hex (`components.css`'s button text color) to `--on-gold`.
Loaded **Inter** via a Google Fonts `<link>` in `frontend/index.html` — it was declared
first in the font stack from the start but never actually imported, so the app had been
silently falling back to system fonts.

**AppShell** (`frontend/src/layouts/DashboardLayout.tsx`, formerly `AppShell.tsx`,
renamed in the Phase 1 architecture pass): added a hand-authored inline-SVG icon set
(`frontend/src/components/ui/icons.tsx`, no new dependency) next to each nav label, and
a real user-initials avatar in the topbar (derived from the signed-in user's actual
name/email, not a placeholder image).

**Deliberate deviations from the reference, and why:**
- No hero/login photography — **zero image assets exist anywhere in this repo**; rather
  than source stock photos of unknown license and present them as "Zambia," the hero
  and login split-panel use CSS/SVG abstract contour-line graphics instead, in the same
  brand colors.
- No Rainfall Trend chart or Risk Distribution donut on the Dashboard — no charting
  library exists in this project and, more importantly, **no real data exists yet** to
  plot (weather ingestion is essentially unpopulated, no model has produced predictions).
  Adding either now would mean fabricating chart content, which this project's own rules
  forbid. Deferred until real data exists.
- No Risk Map "Layers" toggle for Rainfall/Weather/Historical Events/Prediction Points —
  none of those datasets are actually plotted on the map; toggles that switch nothing on
  would be dead UI.
- Login/Signup do not add "Remember me," "Forgot password," or social sign-in buttons —
  none of that has backend support, and non-functional controls are exactly the kind of
  thing this project's audits have repeatedly flagged as a problem when found elsewhere.

**Real functional additions made during this pass** (not just restyling): Dashboard
gained a "Recent Warnings" card backed by already-fetched real alert data (previously
only counted, never listed); Risk Map's marker interaction now opens a real React side
panel (reusing the same real fields the old Leaflet popup showed) instead of an HTML
popup string; `About.tsx`'s "no auth/alerts/citizen-report backend exists yet" claim
(the same class of staleness as the already-tracked `docs/bug-register.md` BUG-01) was
corrected while the file was open for restyling, since it was directly false by this
point.

Verified live via puppeteer-core + local Chrome at 1440px/800px/390px for Landing,
Login, Dashboard, and Risk Map (screenshots in `.run_shots/redesign/`) — no overflow or
clipping at any width, real seeded data rendering correctly throughout.

## Update — UI rollout pass 2, remaining screens (2026-09-08)

Rolled the same token system out to the other 15 screens (Predictions, Historical
Events + Detail, Alerts, Create Alert, Citizen Reports, AI Model, Data Sources, System
Status, Notifications, Settings, Profile, Location Detail, NotFound; Analytics was
left untouched — it's a pure shared-component stub with nothing bespoke to restyle).
Three Explore passes beforehand found every one of these pages already inherited the
new surface/text/border tokens automatically (all built on the same `.card`/
`.grid.grid-auto`/`.table-wrap`/shared-component foundation) — nothing was visually
broken. The real, consistent gap across all of them was additive: no icon usage
anywhere outside the AppShell/Dashboard, and no KPI-style summary chips despite several
pages having exactly the kind of categorical data (risk level, status) a KPI row would
summarize.

**Added this pass:**
- Icons (from the existing `icons.tsx` set, plus one new `bell` icon) on every page
  header, and on card headers where a page has multiple sub-cards (Historical Event
  Detail, Location Detail).
- Real KPI-strip summaries on Predictions (Total/High/Moderate/Low), Alerts (Total/
  Critical/High/Low+Moderate), Historical Events (Total events/Provinces affected/Date
  range), Citizen Reports (Pending/Verified/Rejected), Data Sources (Operational/
  Failed/Unknown), and System Status (Operational/Degraded/Unavailable) — every count
  computed client-side from the real already-fetched data, never a separate/fabricated
  number.
- Predictions' risk level was raw text in the table (`{p.risk_level}`); now uses
  `<RiskBadge>` like every other list page.
- Notifications' "Unread" indicator was a raw `<span className="status-badge">` that
  bypassed the shared component entirely; now uses the same `.status-dot` DOM shape as
  every other badge (new `.status-dot.unread` variant), and its "Mark read" button
  gained the `btn-secondary` modifier it was missing.
- AI Model's raw `metrics_json` `<pre>` dump now uses a new `.metrics-block` style
  (`--surface-highest` background) instead of unstyled monospace text.
- Profile gained an identity header: a large avatar (`.avatar-lg`, same real-initials
  logic as the topbar) next to the user's name/role.
- NotFound was previously bare `.page-content` with no card/surface treatment at all —
  now wrapped in a `.card` with an icon, matching every other page's chrome.
- **Settings.tsx fixed** (`docs/bug-register.md` BUG-10): corrected the false "no user/
  session backend exists" claim to the accurate one (auth/session are real; there's
  just no dedicated settings/preferences table yet) — same class of fix already applied
  to `About.tsx` in the foundation pass.

**Deliberately not built:** Prediction Detail, Citizen Report Detail, and Alert Preview
remain absent — the underlying data for the first two doesn't exist yet (no predictions,
and citizen reports already show their full detail inline in the list), so a dedicated
detail page would just be another empty shell.

Verified live via puppeteer-core + local Chrome at 1440px, logged in as the seeded dev
admin: Predictions, Alerts, System Status, Notifications, Profile, Citizen Reports, AI
Model, Data Sources, and NotFound all screenshot correctly with real data
(`.run_shots/redesign/`) — System Status's KPI counts (2 operational/1 degraded/2
unavailable) match its 5 real component rows exactly; Citizen Reports' KPI counts
reflect the real report created during Phase 2's notification testing.

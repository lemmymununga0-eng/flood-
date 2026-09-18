# Verified Components — FloodShield Zambia

Regression-protection ledger required by the audit's Section 59, covering shared/frontend
components and cross-cutting concerns (as distinct from `docs/verified-screens.md`, which covers
individual screens, and `docs/verified-endpoints.md`, which covers the API). **Retest whenever a
change touches**: routing, shared layout components, global styles/tokens, or state
management/auth-context.

Last full verification pass: 2026-09-07 (full codebase audit).

| Component | Verified how | Result |
|---|---|---|
| `AppShell` (persistent sidebar/top bar layout) | Playwright live navigation across all 14 authenticated routes | Renders consistently, no crash on any route |
| Auth context / session handling | Playwright: fresh login post-restart, sidebar shows real authenticated user, sign-out clears session and redirects to `/login` | Working as documented |
| Router (React Router v7) — protected routes | Playwright: authenticated routes reachable when logged in; unknown routes render the real 404 page | Working; anonymous-vs-authenticated gating verified for RBAC-sensitive screens (Create Alert, Citizen Reports submit) |
| `useFetch` hook (shared data-fetching) | Code read + observed correct loading/empty/error states across every screen that uses it | No shared-hook defect found |
| Error/empty/loading state components (`components/ui/States.tsx`) | Code read; observed live on Predictions, Analytics, Notifications, AI Model (all legitimately-empty screens) | Renders honest empty states, never fabricated placeholder data |
| Design tokens (`styles/tokens.css`) / shared component classes (`styles/components.css`) | Visual check across screens this and prior sessions; no inline one-off colors found bypassing the token system | Consistent |
| Responsive table → mobile card fallback | Re-confirmed present in Historical Events / Predictions tables (a real bug here was found and fixed in an earlier build round) | Working, no regression found |
| React error boundary | Searched for (`grep -r "ErrorBoundary\|componentDidCatch"`) | **Does not exist** — confirmed absent, not verified working (see BUG-07) |
| TypeScript build (`tsc -b --noEmit`) | Actually run this session | Clean, 0 errors |
| Production build (`npm run build`) | Actually run this session | Succeeds, working `dist/` output |
| Leaflet map component | Code read + live render check | Initializes and renders controls/attribution correctly; OSM tile images never load in this environment (BLOCKED — sandbox egress, not a component defect) |

No shared component was found to silently swallow errors, show fabricated data in place of a real
empty state, or diverge in behavior between authenticated and anonymous users beyond the
deliberately-designed RBAC/sign-in gates.

---

## Update — 2026-09-08 re-audit

No frontend source changed since 2026-09-07 (confirmed via byte-identical `npm run build` output),
so every row above still holds by non-regression. Re-run live this session: TypeScript build
(clean, 0 errors) and production build (succeeds, identical output). Not re-run this session (no
browser-automation tool available in this pass): the Playwright live-navigation checks — treat
those rows as carried forward from 2026-09-07's execution, not freshly re-confirmed today.

**New finding, not a regression:** no router-level route guard exists (`AppShell.tsx`'s `Outlet`
renders unconditionally) — this was always true, just not previously stated explicitly in this
ledger. See `docs/AUDIT-REPORT-2026-09-08.md` Section 4.

**New component-equivalent verification, different subsystem:** `ai-engine`'s 26-test unit suite
was run live this session (`python -m pytest ai-engine/tests -v`) — 26/26 passed. This isn't a
frontend/shared-component finding, but is recorded here since it's the same class of
regression-protection evidence for the newest part of the codebase.

---

## Update — Phase 1 architecture-alignment refactor (2026-09-08)

`AppShell` was renamed to `DashboardLayout` (`frontend/src/layouts/DashboardLayout.tsx`), with its
`NAV_PRIMARY`/`NAV_SECONDARY` arrays moved to a new `frontend/src/constants.ts` — no rendered-markup
change. Two new inert layout passthroughs (`PublicLayout`, `AuthLayout`) were introduced so the
route tree has a named slot per the governing MVP spec's three-layout shape; both are no-ops today.
`AuthContext.tsx`'s `canManageAlerts` now reads from `constants.ts`'s `ALERT_MANAGER_ROLES` instead
of a locally duplicated array literal. `services/api.ts` was split into `http.ts` + 9 domain-specific
files, kept as a re-export barrel so no page's imports needed to change.

**Re-verified:** `npm run build` (`tsc -b && vite build`) stayed clean throughout every step of the
refactor (verified incrementally, not just at the end). A live puppeteer-core + local-Chrome pass
re-logged in as the seeded dev admin and re-screenshotted Dashboard and Create Alert — both
pixel-identical to the pre-refactor screenshots taken earlier in the same session, confirming the
role-check and layout rename introduced no visual or functional regression.

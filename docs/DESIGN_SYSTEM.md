# FloodShield Zambia — Design System (Approved)

**This documents the design that already exists and is approved. It is a record, not a proposal.**
Every value below was read directly out of the codebase (`frontend/src/styles/tokens.css` and
`frontend/src/styles/components.css`) — nothing here is an approximation, a substitution, or a
redesign. When completing an unfinished page, reuse these exact tokens and classes.

Source of truth, in priority order:
1. `frontend/src/styles/tokens.css` — all color/structure tokens
2. `frontend/src/styles/components.css` — all component patterns (769 lines)
3. This document — a human-readable index of the above

**Do not add ad-hoc colors in component files.** `tokens.css`'s own header states this rule; if a
new value is genuinely needed, add a token rather than scattering a hex code.

## Colors (exact, from `tokens.css`)

### Surfaces
| Token | Value | Use |
|---|---|---|
| `--bg` | `#07111f` | Page background |
| `--bg-secondary` | `#0b1726` | Secondary background regions |
| `--surface` | `#101d2d` | Card / panel background |
| `--surface-elevated` | `#142337` | Raised surfaces, nav hover/active, default button background |
| `--surface-highest` | `#192a40` | Highest elevation (e.g. `.metrics-block`) |
| `--border` | `#1c2c40` | All borders and dividers |

### Brand
| Token | Value | Use |
|---|---|---|
| `--brand-blue` | `#1e5a7a` | Links, button hover border, blue KPI accent |
| `--brand-green` | `#2e8b68` | Green accent |
| `--brand-green-2` | `#3fa67c` | Brighter green accent |
| `--brand-gold` | `#c99a2e` | **Primary action color** — primary buttons, active nav indicator |
| `--brand-gold-2` | `#d8ac3a` | Brighter gold (unread indicator) |
| `--on-gold` | `#1a1400` | Text color on gold surfaces |

Gold is the primary action color — **not** blue. Primary buttons are gold with near-black text;
the active sidebar item is marked by a 3px inset gold bar, not a filled background.

### Risk / status
| Token | Value | Meaning |
|---|---|---|
| `--risk-low` | `#3fa67c` | Low risk; also `status-dot.operational` |
| `--risk-moderate` | `#d8ac3a` | Moderate risk; also `status-dot.degraded` |
| `--risk-high` | `#d97732` | High risk |
| `--risk-critical` | `#c94a4a` | Critical risk; also `status-dot.unavailable` |
| `--text-muted` | `#8292a3` | `status-dot.unknown` |

Risk is a **four-tier** scale (low / moderate / high / critical). Do not introduce a fifth tier or
remap these colors.

### Text
| Token | Value | Use |
|---|---|---|
| `--text-primary` | `#f4f7fa` | Headings, body text |
| `--text-secondary` | `#c2ccd6` | Supporting text, nav items at rest |
| `--text-muted` | `#8292a3` | De-emphasized/metadata text |

## Structure

| Token | Value |
|---|---|
| `--radius` | `10px` (cards, panels) |
| `--radius-sm` | `6px` (buttons, inputs, nav items) |
| `--shadow` | `0 1px 2px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.25)` |
| `--sidebar-w` | `248px` |
| `--topbar-h` | `60px` |

Pills (`.risk-badge`) use `border-radius: 999px`. `color-scheme: dark` is set globally — the app is
**dark-only by design**, not a dark variant of a light theme.

## Typography

Font stack: `Inter, Manrope, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`.

Real sizes in use: nav items `0.88rem`, buttons `0.85rem`, status badges `0.78rem`, risk badges
`0.75rem`. Button and badge weight is `600`.

## Component patterns (reuse these — do not rebuild)

| Pattern | Class | Key styling |
|---|---|---|
| Card | `.card` | `--surface` bg, 1px `--border`, `--radius`, `1.1rem 1.25rem` padding, `--shadow` |
| Auto grid | `.grid.grid-auto` | `repeat(auto-fit, minmax(280px, 1fr))`, `1rem` gap |
| KPI strip | `.kpi-grid` / `.kpi-card` | With `.kpi-icon.accent-{blue,green,gold,critical}` variants |
| Risk badge | `.risk-badge.{low,moderate,high,critical}` | Pill, colored dot via `::before`, background `color-mix(... 16%, transparent)` |
| Status badge | `.status-badge` + `.status-dot.{operational,degraded,unavailable,unknown,unread}` | 8px dot + secondary text |
| Default button | `.btn` | `--surface-elevated` bg, `--border`, hover → `--brand-blue` border |
| Primary button | `.btn.btn-primary` | `--brand-gold` bg, `--on-gold` text, hover `brightness(1.05)` |
| Secondary button | `.btn.btn-secondary` | Transparent bg, same border |
| Form field | `.field` | Label + input/select/textarea, focus ring shared with `.btn:focus-visible` |
| Table | `.table-wrap` | With `.record-cards`/`.record-card` as the narrow-viewport fallback |
| States | `.loading-state`, `.empty-state`, `.error-state` | Shared base styling |
| Metrics dump | `.metrics-block` | `--surface-highest`, monospace |
| Avatars | `.avatar`, `.avatar-lg` | Gradient initials |

## Layout & responsive

Shell is `.app-shell` = fixed `.sidebar` (248px) + `.topbar` (60px) + `.app-main` / `.page-content`.
Pages open with `.page-header` (h1 + supporting `p`).

Real breakpoints in `components.css`: **900px** (two rules — sidebar/layout collapse) and **480px**
(compact phone adjustments). There are no other breakpoints; match these rather than inventing new
ones.

## Explicitly out of scope for this design

The approved direction is *dark, professional, restrained*. The following are deliberately absent
and must not be introduced: purple/blue "AI" gradients, neon accents, glassmorphism, glowing cards,
decorative animation, heavy gradient fills, or oversized rounded containers. Charts and maps, when
built, take their colors from the risk and brand tokens above — the Leaflet map in
`pages/RiskMap.tsx` already follows this.

## Rule for completing unfinished pages

Inspect a finished page first (`Dashboard.tsx`, `Alerts.tsx`, and `SystemStatus.tsx` are the most
complete references), reuse its components and tokens, and extend. Do not style a page
independently — the application must read as one product.

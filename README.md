# FloodShield Zambia

AI-powered flood prediction and early-warning research system for the Zambian context.

FloodShield Zambia estimates flood risk from historical and near-real-time meteorological
data using machine learning, time-series modelling, and explainable AI, and communicates
that risk as decision-support intelligence for citizens, communities, farmers, disaster
management personnel, local authorities, and emergency-response organizations.

This is a research project with a functioning software implementation — not a static
mockup. It follows strict scientific-integrity rules documented in
[`docs/PROJECT-MEMORY.md`](docs/PROJECT-MEMORY.md): real data over synthetic, no fabricated
metrics, no fabricated predictions, no data leakage, and no unjustified flood labels or
prediction horizons.

## Project status

**Phase 0 (Discovery) complete — Phase 1 (Research & Data) not yet started.**
This repository was just scaffolded; no data has been ingested, no models have been
trained, and no backend/frontend code has been written. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the phase plan and
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) for what is not yet known.

## Repository structure

```text
ai-engine/       ML pipeline: data, preprocessing, features, models, evaluation, XAI
backend/         FastAPI service: prediction API, database access, alert orchestration
frontend/        React + TypeScript dashboard (planned)
database/        Schema and migrations
docs/            Source of truth for all project decisions and methodology
infrastructure/  Deployment configuration (planned)
prompts/         Governing prompts for this project (development record)
```

## Documentation

Start with [`docs/PROJECT-MEMORY.md`](docs/PROJECT-MEMORY.md) — it records every major
decision and why it was made, and is the project's source of truth. Then see:

- [`docs/PRD.md`](docs/PRD.md) — product requirements
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system architecture
- [`docs/DATA-SOURCES.md`](docs/DATA-SOURCES.md) — meteorological data sources
- [`docs/ML-METHODOLOGY.md`](docs/ML-METHODOLOGY.md) — modelling approach
- [`docs/RESEARCH-METHODOLOGY.md`](docs/RESEARCH-METHODOLOGY.md) — research problem and rigor rules
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — known unknowns and constraints
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — phase plan

Remaining documents (`SRS.md`, `DATA-DICTIONARY.md`, `DATA-PIPELINE.md`,
`MODEL-EVALUATION.md`, `XAI.md`, `API.md`, `DATABASE.md`, `UI-UX.md`, `SECURITY.md`,
`TESTING.md`, `DEPLOYMENT.md`) are stubbed in `docs/` and will be filled in as each
corresponding phase is implemented — they are not written in advance of the code they
describe.

## Environment

- Python 3.11
- Node.js 22 / npm 10 (for the future React frontend)
- PostgreSQL (planned, not yet provisioned)

Copy `.env.example` to `.env` and fill in real values before running anything that needs
credentials. Never commit `.env`.

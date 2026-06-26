# AquaSense Engineering Constitution

**Version:** 1.0 — June 2026
**Scope:** Governs every plan, diff, and review Antigravity produces for this repository.
**Relationship to the PRD:** `AquaSense_PRD_v3.1.md` is the source of truth for *what* gets built, in what order, and on what stack (FastAPI + Next.js 15 + Supabase/TimescaleDB + Railway + asyncio-mqtt). This constitution governs *how* it gets built. If a request conflicts with the PRD's stack or phase boundaries, flag the conflict in the Implementation Plan instead of silently deviating from either document.

---

## Article I — Layered Architecture

The backend and frontend are each organized into layers with a single responsibility. No layer may reach past its neighbor.

**Backend (`/backend`)**

| Layer | Path | Responsibility | May NOT contain |
| --- | --- | --- | --- |
| API | `app/api/` | FastAPI routers: request/response models, status codes, calling services | Business logic, direct DB/ORM queries |
| Services | `app/services/` | Business logic — WQI scoring orchestration, alert rules, ML pipeline orchestration | FastAPI imports, raw SQL |
| Repositories | `app/repositories/` | Data access only — Supabase/Postgres queries, TimescaleDB continuous aggregate reads | Business logic, validation rules |
| ML | `app/ml/` | XGBoost + SHAP + Isolation Forest + EWMA pipeline, independently testable | API or DB code |
| Ingestion | `app/ingestion/` | asyncio-mqtt subscriber, ThingSpeak integration | Business logic beyond parse-and-handoff |
| Core | `app/core/` | Config, auth helpers, shared utilities | Feature-specific logic |

**Frontend (`/frontend`)**

| Layer | Path | Responsibility |
| --- | --- | --- |
| Routes | `app/(routes)/` | Page composition only — no data-fetching logic inline |
| Data | `lib/api/` | Backend calls, SSE client setup |
| UI | `components/` | Presentational components; receive data via props, don't fetch it themselves |

**Rationale:** a reviewer (or you, six weeks from now) should be able to find "where the WQI gets calculated" or "where ThingSpeak data gets validated" without reading the whole codebase. Mixing layers is the single fastest way an academic project's codebase becomes unreadable by demo day.

## Article II — Code Shape

- **Functions:** soft cap ~40 lines, hard stop at 60. If a function needs a comment like "# now do the next part," split it.
- **Files:** soft cap ~300 lines. A FastAPI router or service file approaching this should be split by sub-resource (e.g. `readings_router.py` / `alerts_router.py`, not one `routes.py`).
- **Classes:** single responsibility. If describing what a class does requires "and," split it.
- **Naming:**
  - Python: `snake_case` functions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constants. Module names describe one responsibility (`readings_repository.py`, not `db_utils.py`).
  - TypeScript/React: `PascalCase` components, `camelCase` functions/variables, hooks prefixed `use` (`useReadingsStream`).
  - Database: `snake_case` tables/columns, matching the schema already defined in PRD §4 exactly — no renaming columns ad hoc.
  - API routes: REST nouns, plural resources, matching the endpoints already specified in PRD §7. New endpoints not in the PRD get proposed in the Implementation Plan before being built.

## Article III — Security

These are non-negotiable, not best-effort:

1. **Secrets are never hardcoded.** Supabase keys, the ThingSpeak MQTT password, JWT secret, and any Railway-injected config are read via environment variables only. A `.env.example` with placeholder names is checked into git; the real `.env` is gitignored. Grep for anything that looks like a credential before any commit is finalized.
2. **No secret in logs or errors.** Exception messages and log lines must never interpolate raw env var values.
3. **Every FastAPI endpoint validates its input via a Pydantic model.** No raw `dict` request bodies. No endpoint trusts a query param or path param without type/range validation.
4. **Every value arriving from ThingSpeak (via MQTT or REST) is validated before it touches the database** — type-checked, and range-checked for pH/TDS/turbidity before WQI scoring runs on it. Malformed or missing sensor data is handled defensively, not assumed well-formed.
5. **No string-interpolated SQL.** Use the Supabase client / parameterized queries exclusively.
6. **Dependency hygiene:** run `pip-audit` (backend) and `npm audit` (frontend) before closing out a build phase. A flagged vulnerability is either fixed or explicitly accepted with a one-line reason recorded in the phase's Walkthrough — never silently ignored.
7. **No `eval`/`exec`**, and no shelling out to system commands with unsanitized input.

## Article IV — Documentation & Architecture Records

- **Architecture Decision Records** live in `docs/adr/NNN-short-title.md`, one per decision *not already settled by the PRD*. Write one whenever you choose between two reasonable implementation approaches the PRD doesn't dictate (e.g., how the MQTT reconnect/backoff is implemented, how the SSE per-user queue is structured). Use a short format: Context → Decision → Consequences.
- **API documentation is generated, not hand-written.** FastAPI's auto-generated OpenAPI schema is the source of truth. If a human-readable `docs/api.md` exists, it is regenerated from the schema, never edited by hand in a way that lets it drift.
- **Architecture diagrams** live in `docs/diagrams/` (Mermaid or equivalent, checked into git as text, not binary images) and are updated whenever a layer's responsibilities change — this is part of "done," not a follow-up task.
- **Every build phase's Walkthrough notes any deviation from the PRD**, however small, so the PRD and the deployed system never quietly drift apart.

## Article V — Verification

- Lightweight, not enterprise-grade: this project does not need a full CI/CD gate, but every service-layer function with non-trivial logic (WQI scoring, alert thresholds, ML pipeline glue) gets at least one test that would catch an obviously wrong answer.
- Before a build phase is marked complete: tests that exist must pass, the relevant security checklist items in Article III have been checked, and any new ADRs/diagrams are written.
- Prefer running the actual test suite over describing what tests *would* show.

## Article VI — Process

- Follow the plan → implement → verify → walkthrough cycle (see `.agents/workflows/devloop.md`) for every non-trivial task.
- When a request conflicts with this constitution or with the PRD, say so in the Implementation Plan rather than picking one silently.
- This constitution is the source of truth for engineering standards on this repo. If you (the agent) believe a principle here is actively wrong for a specific situation, propose an amendment in the plan rather than quietly working around it.

## Amendments

This file is edited deliberately by the project author, not rewritten mid-task by an agent. Proposed changes surface as a recommendation in an Implementation Plan; the author approves and edits this file directly.

# 1. Auth Flow Routes Through FastAPI

**Status:** Accepted  
**Date:** 2026-06-26

## Context

AquaSense uses **Supabase Auth** as the identity provider and **FastAPI** as the backend API layer. The PRD specifies both Supabase Auth integration and explicit FastAPI auth endpoints (`POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `PATCH /api/auth/profile`).

Two viable approaches exist for wiring these together:

### Option A — Direct Supabase Auth from the Frontend

The Next.js frontend calls Supabase Auth directly via `@supabase/ssr`. The Supabase client manages its own session cookies. FastAPI acts as a **passive verifier**: it reads the JWT from the request, validates it against the Supabase JWKS, and grants or denies access to protected data endpoints. No auth-specific FastAPI routes are needed.

**Pros:** Fewer backend routes, leverages Supabase's built-in session management, simpler initial setup.  
**Cons:** Auth logic is split across frontend and backend, frontend must hold the Supabase anon key (acceptable) but also coordinate cookie handling with Supabase's SDK, harder to inject custom business logic (e.g., creating a `users` table row on signup), rate limiting and audit logging must be implemented separately on each surface.

### Option B — FastAPI Proxies All Auth Calls

The Next.js frontend calls FastAPI for every auth operation (signup, login, logout, profile). FastAPI uses the `supabase-py` admin client (service-role key) to proxy these calls to Supabase Auth, then sets/clears **httpOnly** cookies on the response. The frontend never communicates with Supabase Auth directly for login/signup flows.

**Pros:** Single point of control, centralized cookie management, backend owns all auth side-effects, frontend never needs the service-role key.  
**Cons:** One extra network hop per auth call (frontend → FastAPI → Supabase), frontend Supabase client may still be needed for token refresh via `@supabase/ssr`.

## Decision

**Option B: FastAPI is the single auth gateway.**

All auth operations flow through FastAPI endpoints. The backend proxies signup/login to Supabase Auth, manages httpOnly cookie lifecycle, and performs any side-effects (e.g., inserting into `public.users` on signup). The frontend treats FastAPI as the only auth API surface.

## Consequences

### Positive

- **Single point of control** for auth logic, rate limiting, and audit logging.
- **Frontend never needs the service-role key** — it only knows the FastAPI base URL.
- **Cookie management is centralized** in the backend; the frontend doesn't manage auth tokens directly.
- **Easier to add custom business logic** on auth events (e.g., creating a `public.users` row on signup, sending welcome emails, provisioning default ThingSpeak channels).
- **Consistent API surface** — SSE streams, data endpoints, and auth all go through FastAPI.

### Negative

- **One extra network hop** (frontend → FastAPI → Supabase) for auth calls — negligible latency for infrequent operations like login/signup.
- **Frontend Supabase client may still be needed** for session refresh via `@supabase/ssr`, creating a small surface area outside the proxy pattern.

### Neutral

- SSE and data endpoints already route through FastAPI, so this decision keeps the architecture uniform.
- The approach does not preclude switching to Option A in the future; the Supabase Auth tables and JWT structure remain the same regardless.

# 2. Roles Stored in app_metadata, Not user_metadata

**Status:** Accepted  
**Date:** 2026-06-26

## Context

Supabase Auth provides two metadata buckets on every user object:

- **`user_metadata`** — Writable by the authenticated user via `supabase.auth.updateUser()`. Intended for user-controlled profile data (display name, avatar URL, preferences).
- **`app_metadata`** — Only writable via the admin/service-role API (`supabase.auth.admin.updateUserById()`). Intended for application-controlled data that users must not modify directly.

AquaSense requires **role-based access control** with at least two roles: `user` (default) and `admin`. The role determines access to admin dashboards, user management, and system configuration. Storing the role in the wrong metadata bucket would allow privilege escalation.

Additionally, the project maintains a `public.users` table with a `role` column for query convenience (e.g., listing all admins, filtering by role in SQL). This creates a dual-storage situation that must be kept in sync.

## Decision

**Store the authoritative role in `app_metadata.role`.** Mirror the value in `public.users.role` for query convenience.

- On signup, the backend sets `app_metadata.role = 'user'` via the service-role client and inserts a matching row in `public.users`.
- Role changes are performed exclusively through backend admin endpoints that update both `app_metadata` (via Supabase admin API) and `public.users.role` (via SQL) in a single operation.
- Authorization checks in FastAPI middleware read the role from the decoded JWT's `app_metadata` claim — no database query required for simple role gates.

## Consequences

### Positive

- **Users cannot self-escalate privileges** — `app_metadata` is not writable from the client SDK.
- **Role is available in JWT claims** — `app_metadata` is embedded in the Supabase-issued JWT, enabling stateless authorization checks in FastAPI middleware.
- **Backend can check role from JWT without a DB query** — reduces latency on every authenticated request.
- **Clear separation of concerns** — user-editable fields live in `user_metadata`, application-controlled fields live in `app_metadata`.

### Negative

- **Role changes require the service-role key** — only the backend can modify `app_metadata`, so all role mutations must go through FastAPI admin endpoints.
- **Must keep `users.role` and `app_metadata.role` in sync** — the backend must update both atomically. A sync failure could cause inconsistency between JWT claims and database queries.
- **JWT claims may be stale until token refresh** — if a user's role changes, the old JWT still carries the previous role until the token is refreshed. The system must be designed to handle this window (e.g., force token refresh on role change, or accept a short staleness window).

### Neutral

- The `public.users.role` column includes a `CHECK (role IN ('user', 'admin'))` constraint, ensuring only valid roles are stored at the database level regardless of what the application layer sends.
- This pattern is consistent with Supabase's own documentation and recommended practices for RBAC.

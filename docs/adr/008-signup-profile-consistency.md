# 8. Signup Profile Consistency

## Context
During registration (`AuthService.signup`), the system must perform two primary operations:
1. Create a user account in Supabase Auth via `sign_up`.
2. Insert a corresponding profile row in `public.users` via `UserRepository.create_user`.

Because this is a distributed system with two separate interfaces (GoTrue Auth API and PostgREST Database API), these operations do not share a local database transaction. If the database insertion fails (due to connection loss, constraint violations, or database errors), the auth account remains created but has no profile row. 

This results in an "orphaned user". Since all other tables (e.g. `readings`, `alerts`) reference `public.users(id)` via a foreign key constraint, an orphaned user will crash or fail on almost every subsequent request, including login and telemetry ingestion. Furthermore, because their email is registered in `auth.users`, they cannot self-correct by retrying the registration.

## Decision
We implement a **Saga Rollback pattern**:
1. Wrap the `UserRepository.create_user` call in a `try-except` block.
2. If `create_user` raises a `ProfileCreationError`, log a warning and call `self._admin.auth.admin.delete_user(user.id)` to delete the newly created auth user.
3. Propagate the error so that the API layer can return a clear failure response.

## Consequences
- **Data Integrity:** Orphaned `auth.users` accounts are prevented.
- **User Experience:** When a registration failure occurs, the user can immediately retry with the same email address once the temporary database issue is resolved.
- **Failure Recovery:** If deletion also fails, a critical log message `signup_rollback_failed` is raised to alert administrators for manual cleanup.

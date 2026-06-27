"""Domain exceptions and FastAPI exception-handler registration.

Domain exceptions live in the services/repositories layers.
The API layer catches them via registered handlers and returns
the correct HTTP status code — keeping business logic free of
FastAPI imports (constitution Article I).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ── Domain Exceptions ─────────────────────────────────

class InvalidCredentialsError(Exception):
    """Raised when login credentials are wrong or a JWT is invalid."""

    def __init__(self, detail: str = "Invalid credentials"):
        self.detail = detail
        super().__init__(self.detail)


class UserNotFoundError(Exception):
    """Raised when a user lookup returns no result."""

    def __init__(self, detail: str = "User not found"):
        self.detail = detail
        super().__init__(self.detail)


class UserAlreadyExistsError(Exception):
    """Raised when signup is attempted with an existing email."""

    def __init__(self, detail: str = "A user with this email already exists"):
        self.detail = detail
        super().__init__(self.detail)


class ProfileUpdateError(Exception):
    """Raised when a profile update fails."""

    def __init__(self, detail: str = "Failed to update profile"):
        self.detail = detail
        super().__init__(self.detail)


class ProfileCreationError(Exception):
    """Raised when profile creation fails after auth signup."""

    def __init__(self, user_id: str, detail: str = "Failed to create user profile"):
        self.user_id = user_id
        self.detail = detail
        super().__init__(f"{detail} for user {user_id}")


# ── Handler Registration ─────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Attach domain-exception → HTTP-response mappings to the app."""

    @app.exception_handler(InvalidCredentialsError)
    async def _invalid_credentials(
        _request: Request, exc: InvalidCredentialsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": exc.detail},
        )

    @app.exception_handler(UserNotFoundError)
    async def _user_not_found(
        _request: Request, exc: UserNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": exc.detail},
        )

    @app.exception_handler(UserAlreadyExistsError)
    async def _user_exists(
        _request: Request, exc: UserAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": "conflict", "message": exc.detail},
        )

    @app.exception_handler(ProfileUpdateError)
    async def _profile_update(
        _request: Request, exc: ProfileUpdateError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "bad_request", "message": exc.detail},
        )

    @app.exception_handler(ProfileCreationError)
    async def _profile_creation(
        _request: Request, exc: ProfileCreationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": exc.detail},
        )


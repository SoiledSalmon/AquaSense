"""JWT verification and cookie utilities.

All token validation happens server-side — the frontend never decodes
JWTs itself (auth-implementation-patterns skill, rule #10).
"""

from datetime import datetime, timezone

from jose import JWTError, jwt

from app.core.config import Settings
from app.core.exceptions import InvalidCredentialsError

# ── Constants ─────────────────────────────────────────
ALGORITHM = "HS256"
ACCESS_TOKEN_MAX_AGE = 900          # 15 minutes in seconds
REFRESH_TOKEN_MAX_AGE = 604_800     # 7 days in seconds


def verify_jwt(token: str, settings: Settings) -> dict:
    """Decode and validate a Supabase-issued JWT.

    Validates: signature (HS256 + JWT secret), expiration.
    Returns the decoded payload dict on success.
    Raises InvalidCredentialsError on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,
                "verify_aud": False,   # Supabase audience varies
            },
        )
    except JWTError:
        raise InvalidCredentialsError("Invalid or expired token")

    # Ensure the token isn't expired (belt-and-suspenders — jose checks
    # this too, but we guard against clock skew edge cases)
    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(
        tz=timezone.utc
    ):
        raise InvalidCredentialsError("Token has expired")

    return payload


def create_cookie_params(settings: Settings) -> dict:
    """Return kwargs dict for Response.set_cookie().

    httpOnly + Secure + SameSite=Lax per auth-implementation-patterns.
    Secure is False in development for localhost without HTTPS.
    """
    return {
        "httponly": True,
        "secure": settings.IS_PRODUCTION,
        "samesite": "lax",
        "path": "/",
    }

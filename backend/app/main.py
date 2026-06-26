"""FastAPI application entry point.

Initializes the app, configures CORS, rate limiting, exception handlers,
and mounts routers.
"""

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from supabase import create_client

from app.api.auth_router import router as auth_router, limiter
from app.api.readings_router import router as readings_router
from app.services.sse_manager import sse_manager
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application.

    Initializes Supabase clients and starts the background MQTT subscriber at startup.
    Cancels and awaits the subscriber task on shutdown.
    """
    import asyncio
    from app.mqtt_subscriber import run_mqtt_subscriber

    settings = get_settings()
    logger.info("app_starting", environment=settings.ENVIRONMENT)

    # Initialize Supabase client (anon role)
    app.state.supabase = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )

    # Initialize Supabase admin client (service role)
    app.state.supabase_admin = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY
    )

    # Initialize SSE Manager in application state
    app.state.sse_manager = sse_manager

    # Start the background MQTT subscriber task
    mqtt_task = asyncio.create_task(run_mqtt_subscriber(app))

    yield

    logger.info("app_stopping")
    mqtt_task.cancel()
    await asyncio.gather(mqtt_task, return_exceptions=True)
    logger.info("app_stopped")

app = FastAPI(
    title="AquaSense API",
    description="Backend API for the AquaSense IoT monitoring system.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Rate Limiting ────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception Handlers ────────────────────────────────
register_exception_handlers(app)

# ── CORS Middleware ───────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security Headers Middleware ───────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── Routers ───────────────────────────────────────────
app.include_router(auth_router)
app.include_router(readings_router)

# ── Health Check ──────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint to verify backend status."""
    return {"status": "healthy", "service": "backend"}

"""FastAPI application entry point.

Initializes the app, configures CORS, rate limiting, exception handlers,
and mounts routers.
"""

import sys
import os
import asyncio

# Add repository root to system path for importing the 'ml' module
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Crucial fix for aiomqtt on Windows:
if sys.platform == "win32":
    # Uvicorn on Windows instantiates ProactorEventLoop directly, bypassing the policy.
    # We override ProactorEventLoop to force SelectorEventLoop, which is required by aiomqtt.
    asyncio.ProactorEventLoop = asyncio.SelectorEventLoop

    selector_policy = asyncio.WindowsSelectorEventLoopPolicy()
    asyncio.set_event_loop_policy(selector_policy)
    # Prevent uvicorn from overriding this policy during startup
    asyncio.set_event_loop_policy = lambda policy: None

from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from supabase import create_async_client

from app.core.logging import setup_logging

setup_logging()

from app.api.auth_router import router as auth_router, limiter
from app.api.readings_router import router as readings_router
from app.api.alerts_router import router as alerts_router
from app.api.admin_router import router as admin_router
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
    from app.mqtt_subscriber import run_mqtt_subscriber
    from ml import load_models

    settings = get_settings()
    logger.info("app_starting", environment=settings.ENVIRONMENT)

    # Trigger model loading/training once at startup
    try:
        load_models()
    except Exception as e:
        logger.error("app_model_loading_failed_at_startup", error=str(e))

    # Initialize Supabase client (anon role)
    app.state.supabase = await create_async_client(
        settings.SUPABASE_URL, settings.SUPABASE_KEY
    )

    # Initialize Supabase admin client (service role)
    app.state.supabase_admin = await create_async_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
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
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Routers ───────────────────────────────────────────
app.include_router(auth_router)
app.include_router(readings_router)
app.include_router(alerts_router)
app.include_router(admin_router)


# ── Health Check ──────────────────────────────────────
@app.get("/api/health", tags=["health"])
async def health_check(request: Request):
    """Health check endpoint to verify backend status."""
    mqtt_status = getattr(request.app.state, "mqtt_status", "unknown")
    return {"status": "healthy", "service": "backend", "mqtt_status": mqtt_status}

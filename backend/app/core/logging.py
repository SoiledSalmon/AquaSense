"""Structured logging setup for AquaSense backend.

Logs to stdout with JSON format in production and console format in development.
"""

import logging
import structlog
from app.core.config import get_settings


def setup_logging():
    """Configures application-wide logging with structlog.

    Checks environment configurations and applies JSON formatting for production/staging,
    and pretty console logging for development.
    """
    settings = get_settings()
    is_production = settings.ENVIRONMENT in ("production", "staging")

    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_production:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [structlog.dev.ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # In production, limit third-party libraries' debug/info log outputs
    if is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
        logging.getLogger("aiomqtt").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

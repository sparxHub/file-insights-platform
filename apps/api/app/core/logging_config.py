"""Advanced logging configuration with structured logging"""

import logging
import sys
from typing import Any, Dict, Optional

import structlog
from uvicorn.config import LOGGING_CONFIG

from .config import settings


def configure_structlog() -> None:
    """Configure structured logging with proper processors and formatting"""
    
    # Shared processors for consistent log format
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.debug:
        # Development: Pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_uvicorn_logging() -> Dict[str, Any]:
    """Configure uvicorn logging to use structured format"""
    
    # Get base uvicorn config
    config = LOGGING_CONFIG.copy()
    
    # Update formatters for structured logging
    if settings.debug:
        # Development: Keep uvicorn's default formatting
        pass
    else:
        # Production: JSON formatting
        config["formatters"]["default"]["format"] = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
        config["formatters"]["access"]["format"] = (
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "method": "%(method)s", "path": "%(path)s", '
            '"status": %(status_code)d, "duration": %(duration)s}'
        )
    
    return config


class RequestContextMiddleware:
    """Middleware to add request context to structured logs"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract request information
            headers = dict(scope.get("headers", []))
            request_id = headers.get(b"x-request-id", b"unknown").decode("latin1")
            method = scope.get("method", "unknown")
            path = scope.get("path", "unknown")
            
            # Add to context
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(
                request_id=request_id,
                method=method,
                path=path,
                service="file-insights-api"
            )
        
        await self.app(scope, receive, send)


# Business metric loggers
def log_upload_event(event_type: str, upload_id: str, user_id: str, **kwargs) -> None:
    """Log upload-related events with consistent structure"""
    logger = structlog.get_logger("business.upload")
    logger.info(
        "upload_event",
        event_type=event_type,
        upload_id=upload_id,
        user_id=user_id,
        **kwargs
    )


def log_performance_metric(operation: str, duration: float, success: bool, **kwargs) -> None:
    """Log performance metrics"""
    logger = structlog.get_logger("metrics.performance")
    logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration * 1000,
        success=success,
        **kwargs
    )


def log_security_event(event_type: str, user_id: Optional[str] = None, ip_address: Optional[str] = None, **kwargs) -> None:
    """Log security-related events"""
    logger = structlog.get_logger("security")
    logger.warning(
        "security_event",
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        **kwargs
    )


def log_business_error(error_code: str, message: str, user_id: Optional[str] = None, **kwargs) -> None:
    """Log business logic errors"""
    logger = structlog.get_logger("business.error")
    logger.error(
        "business_error",
        error_code=error_code,
        message=message,
        user_id=user_id,
        **kwargs
    )


# Initialize logging on module import
configure_structlog()

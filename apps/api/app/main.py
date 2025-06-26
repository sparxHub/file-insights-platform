import time

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

from .api.routes import auth_routes, upload_routes
from .core.config import settings
from .core.logging_config import RequestContextMiddleware, log_business_error

# Initialize structured logging
logger = structlog.get_logger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Add request context middleware for logging
app.add_middleware(RequestContextMiddleware)

# Add logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            "request_started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=duration * 1000
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                error=str(e),
                duration_ms=duration * 1000
            )
            raise

app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(upload_routes.router, prefix="/api/v1")

@app.get("/health")
def health():
    logger.info("health_check_requested")
    return {"status": "ok"}

# Import custom exceptions
from .core.exceptions import FileInsightsError, create_http_exception

# Custom exception handlers
@app.exception_handler(FileInsightsError)
async def file_insights_exception_handler(request: Request, exc: FileInsightsError):
    """Handle custom FileInsightsError exceptions"""
    logger.error(
        "business_error_handled",
        error_code=exc.error_code.value,
        message=exc.message,
        context=exc.context,
        url=str(request.url),
        method=request.method
    )
    
    http_exc = create_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )

# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        url=str(request.url),
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "SYSTEM_003",
            "message": "An unexpected error occurred",
            "details": {}
        }
    )

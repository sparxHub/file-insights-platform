"""Enterprise-grade exception hierarchy and error handling"""

from typing import Any, Dict, Optional
from enum import Enum

import structlog
from fastapi import HTTPException, status


logger = structlog.get_logger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for API responses"""
    
    # Authentication & Authorization
    INVALID_CREDENTIALS = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002"
    TOKEN_INVALID = "AUTH_003"
    INSUFFICIENT_PERMISSIONS = "AUTH_004"
    RATE_LIMIT_EXCEEDED = "AUTH_005"
    
    # Upload Errors
    UPLOAD_NOT_FOUND = "UPLOAD_001"
    UPLOAD_ALREADY_EXISTS = "UPLOAD_002"
    UPLOAD_SIZE_EXCEEDED = "UPLOAD_003"
    UPLOAD_TYPE_NOT_SUPPORTED = "UPLOAD_004"
    UPLOAD_CHUNK_INVALID = "UPLOAD_005"
    UPLOAD_ALREADY_COMPLETED = "UPLOAD_006"
    
    # Storage Errors
    S3_CONNECTION_FAILED = "STORAGE_001"
    S3_UPLOAD_FAILED = "STORAGE_002"
    S3_PERMISSION_DENIED = "STORAGE_003"
    DYNAMODB_CONNECTION_FAILED = "STORAGE_004"
    DYNAMODB_WRITE_FAILED = "STORAGE_005"
    
    # Validation Errors
    INVALID_REQUEST_FORMAT = "VALIDATION_001"
    MISSING_REQUIRED_FIELD = "VALIDATION_002"
    FIELD_VALUE_INVALID = "VALIDATION_003"
    FILE_TYPE_NOT_ALLOWED = "VALIDATION_004"
    
    # Business Logic Errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_001"
    WORKFLOW_STATE_INVALID = "BUSINESS_002"
    RESOURCE_CONFLICT = "BUSINESS_003"
    
    # System Errors
    EXTERNAL_SERVICE_UNAVAILABLE = "SYSTEM_001"
    DATABASE_ERROR = "SYSTEM_002"
    INTERNAL_SERVER_ERROR = "SYSTEM_003"
    SERVICE_TIMEOUT = "SYSTEM_004"


class FileInsightsError(Exception):
    """Base exception class for all File Insights Platform errors"""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.user_message = user_message or message
        self.cause = cause
        
        super().__init__(message)
        
        # Log the error with structured context
        logger.error(
            "file_insights_error",
            error_code=error_code.value,
            message=message,
            user_message=user_message,
            context=self.context,
            caused_by=str(cause) if cause else None
        )


class AuthenticationError(FileInsightsError):
    """Authentication-related errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.INVALID_CREDENTIALS, **kwargs):
        super().__init__(message, error_code, **kwargs)


class AuthorizationError(FileInsightsError):
    """Authorization-related errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.INSUFFICIENT_PERMISSIONS, **kwargs):
        super().__init__(message, error_code, **kwargs)


class ValidationError(FileInsightsError):
    """Input validation errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.INVALID_REQUEST_FORMAT, **kwargs):
        super().__init__(message, error_code, **kwargs)


class UploadError(FileInsightsError):
    """Upload-related business logic errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.UPLOAD_NOT_FOUND, **kwargs):
        super().__init__(message, error_code, **kwargs)


class StorageError(FileInsightsError):
    """Storage service errors (S3, DynamoDB)"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.S3_CONNECTION_FAILED, **kwargs):
        super().__init__(message, error_code, **kwargs)


class ExternalServiceError(FileInsightsError):
    """External service integration errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, **kwargs):
        super().__init__(message, error_code, **kwargs)


class BusinessRuleError(FileInsightsError):
    """Business rule violation errors"""
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.BUSINESS_RULE_VIOLATION, **kwargs):
        super().__init__(message, error_code, **kwargs)


# HTTP Exception mapping for API responses
ERROR_CODE_TO_HTTP_STATUS = {
    # Authentication errors
    ErrorCode.INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.TOKEN_INVALID: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,
    ErrorCode.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    
    # Upload errors
    ErrorCode.UPLOAD_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.UPLOAD_ALREADY_EXISTS: status.HTTP_409_CONFLICT,
    ErrorCode.UPLOAD_SIZE_EXCEEDED: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    ErrorCode.UPLOAD_TYPE_NOT_SUPPORTED: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    ErrorCode.UPLOAD_CHUNK_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UPLOAD_ALREADY_COMPLETED: status.HTTP_409_CONFLICT,
    
    # Storage errors
    ErrorCode.S3_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.S3_UPLOAD_FAILED: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.S3_PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    ErrorCode.DYNAMODB_CONNECTION_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.DYNAMODB_WRITE_FAILED: status.HTTP_502_BAD_GATEWAY,
    
    # Validation errors
    ErrorCode.INVALID_REQUEST_FORMAT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.MISSING_REQUIRED_FIELD: status.HTTP_400_BAD_REQUEST,
    ErrorCode.FIELD_VALUE_INVALID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.FILE_TYPE_NOT_ALLOWED: status.HTTP_400_BAD_REQUEST,
    
    # Business logic errors
    ErrorCode.BUSINESS_RULE_VIOLATION: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.WORKFLOW_STATE_INVALID: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.RESOURCE_CONFLICT: status.HTTP_409_CONFLICT,
    
    # System errors
    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.DATABASE_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.INTERNAL_SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.SERVICE_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
}


def create_http_exception(error: FileInsightsError) -> HTTPException:
    """Convert FileInsightsError to HTTPException for FastAPI"""
    
    status_code = ERROR_CODE_TO_HTTP_STATUS.get(
        error.error_code, 
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    detail = {
        "error_code": error.error_code.value,
        "message": error.user_message,
        "details": error.context
    }
    
    return HTTPException(status_code=status_code, detail=detail)


# Context managers for error handling patterns
class ErrorContext:
    """Context manager for consistent error handling and logging"""
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.logger = structlog.get_logger(__name__)
    
    def __enter__(self):
        self.logger.info(f"{self.operation}_started", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"{self.operation}_completed", **self.context)
        else:
            self.logger.error(
                f"{self.operation}_failed",
                exception_type=exc_type.__name__,
                exception_message=str(exc_val),
                **self.context
            )
        return False  # Don't suppress exceptions


# Decorator for error handling
def handle_errors(operation: str, default_error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR):
    """Decorator to standardize error handling for service methods"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                with ErrorContext(operation, function=func.__name__):
                    return await func(*args, **kwargs)
            except FileInsightsError:
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Convert unexpected exceptions to FileInsightsError
                raise FileInsightsError(
                    message=f"Unexpected error in {operation}",
                    error_code=default_error_code,
                    context={"function": func.__name__},
                    cause=e
                )
        return wrapper
    return decorator


# Utility functions for common error scenarios
def raise_upload_not_found(upload_id: str) -> None:
    """Raise standardized upload not found error"""
    raise UploadError(
        message=f"Upload not found",
        error_code=ErrorCode.UPLOAD_NOT_FOUND,
        context={"upload_id": upload_id},
        user_message="The requested upload could not be found"
    )


def raise_invalid_chunk(upload_id: str, chunk_number: int, reason: str) -> None:
    """Raise standardized invalid chunk error"""
    raise UploadError(
        message=f"Invalid chunk: {reason}",
        error_code=ErrorCode.UPLOAD_CHUNK_INVALID,
        context={"upload_id": upload_id, "chunk_number": chunk_number, "reason": reason},
        user_message="The chunk upload request is invalid"
    )


def raise_storage_error(service: str, operation: str, cause: Exception) -> None:
    """Raise standardized storage error"""
    error_code = ErrorCode.S3_CONNECTION_FAILED if service == "s3" else ErrorCode.DYNAMODB_CONNECTION_FAILED
    
    raise StorageError(
        message=f"{service.upper()} {operation} failed",
        error_code=error_code,
        context={"service": service, "operation": operation},
        user_message="A storage service error occurred. Please try again.",
        cause=cause
    )

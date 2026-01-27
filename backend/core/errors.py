"""
Error handling module - Custom exceptions and error handlers
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Dict


class APIError(Exception):
    """Base API error class"""
    
    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class FileValidationError(APIError):
    """Error for invalid file uploads"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=400, details=details)


class SessionNotFoundError(APIError):
    """Error when session doesn't exist"""
    
    def __init__(self, session_id: str):
        super().__init__(
            f"Session {session_id} not found",
            status_code=404,
            details={'session_id': session_id}
        )


class ProcessingError(APIError):
    """Error during survey processing"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=500, details=details)


class OpenAIError(APIError):
    """Error communicating with OpenAI API"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            f"OpenAI API error: {message}",
            status_code=503,
            details=details
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "details": exc.details,
            "path": str(request.url)
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "path": str(request.url)
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    import traceback
    
    # Log the full traceback
    print(f"Unexpected error: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )

"""
Middleware - Custom middleware for the application
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        # Log request
        print(f"→ {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        print(f"← {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)")
        
        return response


class FileSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to validate file upload sizes"""
    
    def __init__(self, app, max_size_mb: int = 50):
        super().__init__(app)
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check content length for file uploads
        if request.method == "POST" and "/upload" in request.url.path:
            content_length = request.headers.get("content-length")
            
            if content_length:
                content_length = int(content_length)
                
                if content_length > self.max_size_bytes:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "File too large",
                            "max_size_mb": self.max_size_bytes / (1024 * 1024),
                            "received_size_mb": content_length / (1024 * 1024)
                        }
                    )
        
        return await call_next(request)

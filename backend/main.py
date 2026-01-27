"""
Main FastAPI Application
Survey Coding with AI - Backend Server
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import socketio
from dotenv import load_dotenv

from core.session import SessionManager
from core.websocket import WebSocketManager
from core.middleware import LoggingMiddleware, FileSizeMiddleware
from core.errors import (
    APIError,
    api_error_handler,
    validation_error_handler,
    general_exception_handler
)
from api import routes

# Load environment variables
load_dotenv()

# Configuration
TEMP_DIR = os.getenv('TEMP_DIR', 'temp_uploads')
SESSION_TIMEOUT_HOURS = int(os.getenv('SESSION_TIMEOUT_HOURS', '24'))
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=False
)

# Create FastAPI app
api_app = FastAPI(
    title="Survey Coding API",
    description="API for automatic survey response coding with AI",
    version="1.0.0"
)

# Create Socket.IO ASGI app (which wraps FastAPI)
app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=api_app
)

# Configure CORS
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
api_app.add_middleware(LoggingMiddleware)
api_app.add_middleware(FileSizeMiddleware, max_size_mb=MAX_FILE_SIZE_MB)


# Initialize managers
session_manager = SessionManager(
    temp_dir=TEMP_DIR,
    session_timeout_hours=SESSION_TIMEOUT_HOURS
)

ws_manager = WebSocketManager(sio)

# Set managers in routes module
routes.set_managers(session_manager, ws_manager)

# Register error handlers
api_app.add_exception_handler(APIError, api_error_handler)
api_app.add_exception_handler(RequestValidationError, validation_error_handler)
api_app.add_exception_handler(Exception, general_exception_handler)

# Include routers
api_app.include_router(routes.router)

@api_app.get("/api/test")
async def test_endpoint():
    return {"status": "ok", "message": "API is working"}

@api_app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("=" * 60)
    print("Survey Coding API - Starting")
    print("=" * 60)
    print(f"Temp directory: {TEMP_DIR}")
    print(f"Session timeout: {SESSION_TIMEOUT_HOURS} hours")
    print(f"Max file size: {MAX_FILE_SIZE_MB} MB")
    print(f"CORS origins: {CORS_ORIGINS}")
    print("=" * 60)
    
    # Cleanup old sessions on startup
    cleaned = session_manager.cleanup_old_sessions()
    if cleaned > 0:
        print(f"Cleaned up {cleaned} old sessions")


# Serve static files from frontend build (for production)
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    # Mount assets
    api_app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    # Catch-all route for SPA
    @api_app.get("/{full_path:path}")
    async def serve_app(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
             raise HTTPException(status_code=404, detail="Not found")
            
        # Check if file exists in dist (e.g. favicon.ico, robots.txt)
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Return index.html for any other route (SPA)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@api_app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("=" * 60)
    print("Survey Coding API - Shutting down")
    print("=" * 60)


@api_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_session_count(),
        "active_connections": ws_manager.get_connection_count()
    }


# Export the socket_app for uvicorn
# Use: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

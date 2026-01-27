"""
WebSocket Manager - Handles real-time communication with clients
"""
import socketio
from typing import Dict, Any, Optional
import asyncio


class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self, sio: socketio.AsyncServer):
        """
        Initialize WebSocket manager
        
        Args:
            sio: Socket.IO server instance
        """
        self.sio = sio
        self.connections: Dict[str, str] = {}  # session_id -> socket_id
        self.setup_handlers()
        
        print("WebSocketManager initialized")
    
    def setup_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        async def connect(sid, environ):
            """Handle client connection"""
            print(f"Client connected: {sid}")
        
        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection"""
            print(f"Client disconnected: {sid}")
            # Remove from connections
            session_to_remove = None
            for session_id, socket_id in self.connections.items():
                if socket_id == sid:
                    session_to_remove = session_id
                    break
            if session_to_remove:
                del self.connections[session_to_remove]
                print(f"Removed session {session_to_remove} from connections")
        
        @self.sio.event
        async def join(sid, data):
            """Handle client joining a session room"""
            session_id = data.get('session_id')
            if session_id:
                self.connections[session_id] = sid
                await self.sio.enter_room(sid, session_id)
                print(f"Client {sid} joined session room: {session_id}")
                await self.sio.emit('joined', {'session_id': session_id}, room=sid)
    
    async def emit_progress(self, session_id: str, progress: float, 
                           message: str = "", **kwargs) -> None:
        """
        Emit progress update to a session
        
        Args:
            session_id: Session identifier
            progress: Progress value (0.0 to 1.0)
            message: Status message
            **kwargs: Additional data to send
        """
        data = {
            'progress': progress,
            'message': message,
            **kwargs
        }
        
        await self.sio.emit('progress_update', data, room=session_id)
        print(f"Emitted progress to {session_id}: {progress:.2%} - {message}")
    
    async def emit_status(self, session_id: str, status: str, 
                         message: str = "", **kwargs) -> None:
        """
        Emit status update to a session
        
        Args:
            session_id: Session identifier
            status: Status value ('idle', 'processing', 'completed', 'error')
            message: Status message
            **kwargs: Additional data to send
        """
        data = {
            'status': status,
            'message': message,
            **kwargs
        }
        
        await self.sio.emit('status_update', data, room=session_id)
        print(f"Emitted status to {session_id}: {status} - {message}")
    
    async def emit_error(self, session_id: str, error: str, **kwargs) -> None:
        """
        Emit error to a session
        
        Args:
            session_id: Session identifier
            error: Error message
            **kwargs: Additional error data
        """
        data = {
            'error': error,
            **kwargs
        }
        
        await self.sio.emit('error', data, room=session_id)
        print(f"Emitted error to {session_id}: {error}")
    
    async def emit_complete(self, session_id: str, results: Dict[str, Any]) -> None:
        """
        Emit completion notification to a session
        
        Args:
            session_id: Session identifier
            results: Processing results
        """
        data = {
            'status': 'completed',
            'results': results
        }
        
        await self.sio.emit('processing_complete', data, room=session_id)
        print(f"Emitted completion to {session_id}")
    
    def is_connected(self, session_id: str) -> bool:
        """
        Check if a session has an active connection
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if connected, False otherwise
        """
        return session_id in self.connections
    
    def get_socket_id(self, session_id: str) -> Optional[str]:
        """
        Get socket ID for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Socket ID or None if not connected
        """
        return self.connections.get(session_id)
    
    def get_connection_count(self) -> int:
        """
        Get number of active connections
        
        Returns:
            Number of active connections
        """
        return len(self.connections)

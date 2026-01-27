"""
Session Manager - Manages user sessions and temporary files
"""
import os
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path


class SessionManager:
    """Manages user sessions and temporary file storage"""
    
    def __init__(self, temp_dir: str = "temp_uploads", session_timeout_hours: int = 24):
        """
        Initialize session manager
        
        Args:
            temp_dir: Directory for temporary file storage
            session_timeout_hours: Hours before session expires
        """
        self.temp_dir = Path(temp_dir)
        self.session_timeout_hours = session_timeout_hours
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Create temp directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"SessionManager initialized with temp_dir: {self.temp_dir}")
    
    def create_session(self) -> str:
        """
        Create a new session
        
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = {
            'created_at': datetime.now(),
            'files': {},
            'status': 'idle',
            'task_id': None,
            'config': {},
            'results': {}
        }
        
        print(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data dictionary or None if not found
        """
        return self.sessions.get(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        return session_id in self.sessions
    
    def save_file(self, session_id: str, file_type: str, file_content: bytes, 
                  filename: str) -> str:
        """
        Save uploaded file to temporary storage
        
        Args:
            session_id: Session identifier
            file_type: Type of file ('responses' or 'codes')
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            Path to saved file
        """
        if not self.session_exists(session_id):
            raise ValueError(f"Session {session_id} does not exist")
        
        # Create session directory
        session_dir = self.temp_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate file path
        file_extension = Path(filename).suffix
        file_path = session_dir / f"{file_type}{file_extension}"
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Update session
        self.sessions[session_id]['files'][file_type] = str(file_path)
        
        print(f"Saved {file_type} file for session {session_id}: {file_path}")
        return str(file_path)
    
    def get_file_path(self, session_id: str, file_type: str) -> Optional[str]:
        """
        Get path to a session file
        
        Args:
            session_id: Session identifier
            file_type: Type of file ('responses' or 'codes')
            
        Returns:
            File path or None if not found
        """
        session = self.get_session(session_id)
        if session:
            return session['files'].get(file_type)
        return None
    
    def update_session_status(self, session_id: str, status: str) -> None:
        """
        Update session status
        
        Args:
            session_id: Session identifier
            status: New status ('idle', 'processing', 'completed', 'error')
        """
        if self.session_exists(session_id):
            self.sessions[session_id]['status'] = status
            print(f"Session {session_id} status updated to: {status}")
    
    def update_session_config(self, session_id: str, config: Dict[str, Any]) -> None:
        """
        Update session configuration
        
        Args:
            session_id: Session identifier
            config: Configuration dictionary
        """
        if self.session_exists(session_id):
            self.sessions[session_id]['config'] = config
            print(f"Session {session_id} config updated")
    
    def update_session_results(self, session_id: str, results: Dict[str, Any]) -> None:
        """
        Update session results
        
        Args:
            session_id: Session identifier
            results: Results dictionary
        """
        if self.session_exists(session_id):
            self.sessions[session_id]['results'] = results
            print(f"Session {session_id} results updated")
    
    def set_task_id(self, session_id: str, task_id: str) -> None:
        """
        Set task ID for a session
        
        Args:
            session_id: Session identifier
            task_id: Task identifier
        """
        if self.session_exists(session_id):
            self.sessions[session_id]['task_id'] = task_id
            print(f"Session {session_id} task_id set to: {task_id}")
    
    def get_task_id(self, session_id: str) -> Optional[str]:
        """
        Get task ID for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Task ID or None
        """
        session = self.get_session(session_id)
        if session:
            return session.get('task_id')
        return None
    
    def _delete_session_files(self, session_id: str) -> None:
        """
        Delete all files associated with a session
        
        Args:
            session_id: Session identifier
        """
        session_dir = self.temp_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            print(f"Deleted files for session: {session_id}")
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete a session and its files
        
        Args:
            session_id: Session identifier
        """
        if self.session_exists(session_id):
            self._delete_session_files(session_id)
            del self.sessions[session_id]
            print(f"Deleted session: {session_id}")
    
    def cleanup_old_sessions(self) -> int:
        """
        Clean up sessions older than timeout period
        
        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.now() - timedelta(hours=self.session_timeout_hours)
        sessions_to_delete = []
        
        for session_id, session_data in self.sessions.items():
            if session_data['created_at'] < cutoff:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        if sessions_to_delete:
            print(f"Cleaned up {len(sessions_to_delete)} old sessions")
        
        return len(sessions_to_delete)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions
        
        Returns:
            Dictionary of all sessions
        """
        return self.sessions.copy()
    
    def get_session_count(self) -> int:
        """
        Get number of active sessions
        
        Returns:
            Number of active sessions
        """
        return len(self.sessions)

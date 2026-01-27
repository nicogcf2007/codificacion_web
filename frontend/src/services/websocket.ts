/**
 * WebSocket Service - Real-time communication with backend
 */
import { io, Socket } from 'socket.io-client';
import { toast } from 'react-toastify';
import type { ProgressUpdate, StatusUpdate } from '../types';

// Get WebSocket URL from environment or use default
// @ts-ignore
const WS_URL = import.meta.env.VITE_WS_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);

export class WebSocketClient {
  private socket: Socket | null = null;
  private sessionId: string | null = null;
  private onProgressCallback: ((update: ProgressUpdate) => void) | null = null;
  private onStatusCallback: ((update: StatusUpdate) => void) | null = null;
  private onErrorCallback: ((error: string) => void) | null = null;
  private onCompleteCallback: ((results: any) => void) | null = null;

  /**
   * Connect to WebSocket server
   */
  connect(sessionId: string): void {
    this.sessionId = sessionId;

    if (this.socket?.connected) {
      console.log('WebSocket already connected, ensuring room join');
      this.socket.emit('join', { session_id: sessionId });
      return;
    }

    // Create socket connection
    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });

    // Setup event listeners
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      // Join session room
      if (this.socket && this.sessionId) {
        this.socket.emit('join', { session_id: this.sessionId });
      }
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('joined', (data) => {
      console.log('Joined session room:', data.session_id);
    });

    this.socket.on('progress_update', (data: ProgressUpdate) => {
      console.log('Progress update received:', data);
      if (this.onProgressCallback) {
        this.onProgressCallback(data);
      } else {
        console.warn('No progress callback registered!');
      }
    });

    this.socket.on('status_update', (data: StatusUpdate) => {
      console.log('Status update received:', data);
      if (this.onStatusCallback) {
        this.onStatusCallback(data);
      }
    });

    this.socket.on('error', (data: { error: string }) => {
      console.error('WebSocket error:', data.error);
      toast.error(`WS Error: ${data.error}`);
      if (this.onErrorCallback) {
        this.onErrorCallback(data.error);
      }
    });

    this.socket.on('processing_complete', (data: { status: string; results: any }) => {
      console.log('Processing complete:', data);
      if (this.onCompleteCallback) {
        this.onCompleteCallback(data.results);
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('Connection error:', error);
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.sessionId = null;
    }
  }

  /**
   * Set callback for progress updates
   */
  onProgress(callback: (update: ProgressUpdate) => void): void {
    this.onProgressCallback = callback;
  }

  /**
   * Set callback for status updates
   */
  onStatus(callback: (update: StatusUpdate) => void): void {
    this.onStatusCallback = callback;
  }

  /**
   * Set callback for errors
   */
  onError(callback: (error: string) => void): void {
    this.onErrorCallback = callback;
  }

  /**
   * Set callback for completion
   */
  onComplete(callback: (results: any) => void): void {
    this.onCompleteCallback = callback;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();

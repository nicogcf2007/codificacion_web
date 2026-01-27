import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { wsClient } from '../services/websocket';
import { stopProcessing, handleAPIError } from '../services/api';
import type { ProgressUpdate, StatusUpdate, ProcessingResults } from '../types';

interface ProcessingMonitorProps {
  sessionId: string;
  taskId?: string; // Optional to satisfy interface compatibility
  onComplete: (results: ProcessingResults) => void;
}

const ProcessingMonitor: React.FC<ProcessingMonitorProps> = ({
  sessionId,
  // taskId, // Not currently used
  onComplete,
}) => {
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Iniciando procesamiento...');
  const [currentColumn, setCurrentColumn] = useState('');
  const [stopping, setStopping] = useState(false);

  useEffect(() => {
    // Connect to WebSocket
    wsClient.connect(sessionId);

    // Setup callbacks
    wsClient.onProgress((update: ProgressUpdate) => {
      setProgress(update.progress);
      if (update.message) {
        setStatusMessage(update.message);
      }
      if (update.current_column) {
        setCurrentColumn(update.current_column);
      }
    });

    wsClient.onStatus((update: StatusUpdate) => {
      setStatusMessage(update.message);
    });

    wsClient.onError((error: string) => {
      toast.error(`Error: ${error}`);
    });

    wsClient.onComplete((results: ProcessingResults) => {
      setProgress(1);
      setStatusMessage('Procesamiento completado');
      toast.success('¡Procesamiento completado exitosamente!');
      setTimeout(() => {
        onComplete(results);
      }, 1000);
    });

    // Cleanup on unmount
    return () => {
      // Don't disconnect here to prevent closing connection on re-renders/strict mode
      // The connection should be managed by the parent or persist until explicitly closed
      // wsClient.disconnect();
    };
  }, [sessionId, onComplete]);

  const handleStop = async () => {
    if (window.confirm('¿Estás seguro de que deseas detener el procesamiento?')) {
      setStopping(true);
      try {
        await stopProcessing(sessionId);
        toast.info('Procesamiento detenido');
      } catch (error) {
        const errorMessage = handleAPIError(error);
        toast.error(`Error al detener: ${errorMessage}`);
      } finally {
        setStopping(false);
      }
    }
  };

  const progressPercentage = Math.round(progress * 100);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Procesando Respuestas
          </h1>
          <p className="text-gray-600">
            El sistema está codificando las respuestas automáticamente
          </p>
        </div>

        <div className="card space-y-6">
          {/* Progress Bar */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">
                Progreso
              </span>
              <span className="text-sm font-medium text-blue-600">
                {progressPercentage}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-4 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progressPercentage}%` }}
              >
                <div className="h-full w-full bg-white opacity-20 animate-pulse"></div>
              </div>
            </div>
          </div>

          {/* Status Message */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <svg
                  className="animate-spin h-6 w-6 text-blue-600"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900">
                  {statusMessage}
                </p>
                {currentColumn && (
                  <p className="text-sm text-blue-700 mt-1">
                    Columna actual: {currentColumn}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Info Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg
                    className="h-8 w-8 text-blue-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs text-blue-600 font-medium">
                    Procesamiento
                  </p>
                  <p className="text-lg font-bold text-blue-900">
                    En curso
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-lg p-4 border border-indigo-200">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg
                    className="h-8 w-8 text-indigo-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs text-indigo-600 font-medium">
                    IA Activa
                  </p>
                  <p className="text-lg font-bold text-indigo-900">
                    OpenAI
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 border border-purple-200">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg
                    className="h-8 w-8 text-purple-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs text-purple-600 font-medium">
                    Tiempo Real
                  </p>
                  <p className="text-lg font-bold text-purple-900">
                    WebSocket
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Stop Button */}
          <div className="flex justify-center pt-4">
            <button
              onClick={handleStop}
              disabled={stopping}
              className={stopping ? 'btn-disabled' : 'btn-danger'}
            >
              {stopping ? 'Deteniendo...' : 'Detener Procesamiento'}
            </button>
          </div>

          {/* Tips */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <svg
                className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="text-sm text-yellow-800">
                <p className="font-medium mb-1">Información:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>El procesamiento puede tomar varios minutos</li>
                  <li>No cierres esta ventana hasta que finalice</li>
                  <li>Los resultados se guardarán automáticamente</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProcessingMonitor;

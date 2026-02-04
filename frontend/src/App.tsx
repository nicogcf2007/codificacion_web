import { useState } from 'react';
import { toast } from 'react-toastify';
import FileUpload from './components/FileUpload';
import Configuration from './components/Configuration';
import ProcessingMonitor from './components/ProcessingMonitor';
import Results from './components/Results';
import ManualCoding from './components/ManualCoding';
import { wsClient } from './services/websocket';
import { startProcessing, handleAPIError, cleanupSession } from './services/api';
import type {
  AppStep,
  UploadResponse,
  ProcessingConfig,
  ProcessingResults,
} from './types';

function App() {
  const [step, setStep] = useState<AppStep>('upload');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [results, setResults] = useState<ProcessingResults | null>(null);
  const [pendingConfig, setPendingConfig] = useState<ProcessingConfig | null>(null);

  const handleFilesUploaded = (data: UploadResponse) => {
    // If there was a previous session (e.g. from back button), clean it up
    if (sessionId && sessionId !== data.session_id) {
      cleanupSession(sessionId).catch(console.error);
    }
    setSessionId(data.session_id);
    setColumns(data.columns);
    setStep('configure');
  };

  const handleConfigComplete = (config: ProcessingConfig) => {
    setPendingConfig(config);
    setStep('manual-coding');
  };

  const handleStartProcessing = async (config: ProcessingConfig) => {
    if (!sessionId) {
      toast.error('No hay sesión activa');
      return;
    }

    try {
      // 1. Conectar WebSocket primero y esperar a que esté listo
      wsClient.connect(sessionId);
      
      // Pequeña pausa para asegurar que el socket se establezca y se una a la sala
      await new Promise(resolve => setTimeout(resolve, 1000));

      // 2. Iniciar procesamiento en backend
      const response = await startProcessing(sessionId, config);
      setTaskId(response.task_id);
      
      // 3. Cambiar vista al monitor
      setStep('processing');
      toast.success('Procesamiento iniciado');
    } catch (error) {
      const errorMessage = handleAPIError(error);
      toast.error(`Error al iniciar procesamiento: ${errorMessage}`);
      console.error('Start processing error:', error);
    }
  };

  const handleProcessingComplete = (processingResults: ProcessingResults) => {
    setResults(processingResults);
    setStep('results');
  };

  const handleReset = () => {
    // Cleanup backend session when resetting
    const currentSessionId = sessionId;
    if (currentSessionId) {
      cleanupSession(currentSessionId).catch(console.error);
    }

    wsClient.disconnect(); // Disconnect when resetting the app
    setStep('upload');
    setSessionId(null);
    setTaskId(null);
    setColumns([]);
    setResults(null);
  };

  const handleBackToUpload = () => {
    setStep('upload');
  };

  return (
    <div className="App">
      {step === 'upload' && (
        <FileUpload onFilesUploaded={handleFilesUploaded} />
      )}

      {step === 'configure' && (
        <Configuration
          columns={columns}
          onStartProcessing={handleConfigComplete} // Change: go to manual coding first
          onBack={handleBackToUpload}
        />
      )}

      {step === 'manual-coding' && sessionId && pendingConfig && (
        <ManualCoding
          sessionId={sessionId}
          config={pendingConfig}
          onConfirm={handleStartProcessing}
          onBack={() => setStep('configure')}
        />
      )}

      {step === 'processing' && sessionId && taskId && (
        <ProcessingMonitor
          sessionId={sessionId}
          taskId={taskId}
          onComplete={handleProcessingComplete}
        />
      )}

      {step === 'results' && sessionId && results && (
        <Results
          sessionId={sessionId}
          results={results}
          onReset={handleReset}
        />
      )}
    </div>
  );
}

export default App;

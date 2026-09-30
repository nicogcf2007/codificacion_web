import { useState } from 'react';
import { toast } from 'react-toastify';
import HomeMenu from './components/HomeMenu';
import FileUpload from './components/FileUpload';
import FileUploadReview from './components/FileUploadReview';
import Configuration from './components/Configuration';
import ProcessingMonitor from './components/ProcessingMonitor';
import Results from './components/Results';
import ManualCoding from './components/ManualCoding';
import TempFilesList from './components/TempFilesList';
import Workspace from './components/Workspace';
import ReviewQueue from './components/ReviewQueue';
import { wsClient } from './services/websocket';
import { startProcessing, startReview, handleAPIError, cleanupSession } from './services/api';
import type {
  AppStep,
  UploadResponse,
  ProcessingConfig,
  ProcessingResults,
} from './types';

function App() {
  const [step, setStep] = useState<AppStep>('home');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [results, setResults] = useState<ProcessingResults | null>(null);
  const [pendingConfig, setPendingConfig] = useState<ProcessingConfig | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeCatalogId, setActiveCatalogId] = useState<string | null>(null);
  const [mode, setMode] = useState<'codify' | 'review'>('codify'); // New state for mode

  const handleMenuSelection = (option: 'codify' | 'review' | 'temp-files' | 'workspace') => {
    if (option === 'workspace') {
      setStep('workspace');
      return;
    }
    if (option === 'temp-files') {
      setStep('temp-files');
      return;
    }
    setMode(option);
    if (option === 'codify') {
        setStep('upload');
    } else {
        setStep('upload-review');
    }
  };

  const handleUseProject = (projectId: string, catalogId?: string) => {
    setActiveProjectId(projectId);
    setActiveCatalogId(catalogId || null);
    setMode('codify');
    setStep('upload');
    toast.success('Proyecto seleccionado para la próxima codificación');
  };

  const handleOpenJob = (selectedJobId: string) => {
    setJobId(selectedJobId);
    setStep('review-queue');
  };

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
    const enrichedConfig: ProcessingConfig = {
      ...config,
      project_id: activeProjectId || undefined,
      catalog_id: activeCatalogId || undefined,
      job_name: activeProjectId ? 'Codificación del proyecto' : undefined,
    };
    setPendingConfig(enrichedConfig);
    
    // Logic branch:
    // If mode is 'codify', go to manual coding first
    // If mode is 'review', skip manual coding and start review immediately
    if (mode === 'codify') {
        setStep('manual-coding');
    } else {
        handleStartReviewProcess(enrichedConfig);
    }
  };

  const handleStartReviewProcess = async (config: ProcessingConfig) => {
      if (!sessionId) return;
      
      try {
          // Connect WS
          wsClient.connect(sessionId);
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          // For review mode, we first need to 'configure' the session with columns
          // but startReview endpoint might expect config to be saved already?
          // Actually, startReview endpoint takes NO config, it reads from session.
          // BUT session config is updated in startProcessing usually.
          // We need to update session config manually first?
          // startProcessing does: update_session_config -> add_task
          // startReview does: get_session -> check files -> get config -> add_task
          
          // So we need to save the config to the session BEFORE calling startReview.
          // Currently we don't have an endpoint just to save config.
          // Let's reuse startProcessing but pointing to a different task?
          // No, better to update startReview to accept config OR add saveConfig endpoint.
          // OR, simpler: We call startProcessing but with a flag? 
          // No, review is a separate endpoint.
          
          // Let's assume for now we use 'startProcessing' endpoint but with a flag/param?
          // Actually, looking at backend, startProcessing calls 'process_survey_task'.
          // startReview calls 'process_review_task'.
          
          // We need a way to save config for review.
          // I will use 'startProcessing' but effectively hijack it? No.
          
          // Let's modify the backend 'start_review' to accept config in body, similar to 'process'.
          // For now, as I cannot change backend in this specific file update, I will assume
          // I need to add a way to save config.
          
          // Wait! startProcessing saves config. 
          // If I call startProcessing, it starts coding.
          // I want to start REVIEW.
          
          // Workaround: Call startProcessing with a flag "review_only"? 
          // Or update backend (which I did in previous turns) to support this? 
          // I haven't updated start_review to accept config yet.
          
          // Let's assume I will update the backend to allow passing config to start-review.
          // For now, I will simulate it by calling a new endpoint or modified one.
          
          // To make it work with current backend:
          // We need to call an endpoint that saves config.
          // 'process' endpoint saves config then starts task.
          
          // I will implement a "save-config" call in API (frontend side) that effectively 
          // prepares the session, or I'll update backend to accept config in start-review.
          // I'll update backend logic in next step.
          
          // Assuming updated backend:
          const response = await startReview(sessionId, config); // Pass config here
          setTaskId(response.task_id);
          setStep('processing');
          toast.success('Revisión iniciada');
          
      } catch (error) {
          const errorMessage = handleAPIError(error);
          toast.error(`Error al iniciar revisión: ${errorMessage}`);
      }
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
      setJobId(response.job_id || null);
      
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
    setStep('home'); // Go back to home menu
    setSessionId(null);
    setTaskId(null);
    setJobId(null);
    setColumns([]);
    setResults(null);
    setActiveProjectId(null);
    setActiveCatalogId(null);
    setMode('codify');
  };

  const handleBackToUpload = () => {
    if (mode === 'codify') {
        setStep('upload');
    } else {
        setStep('upload-review');
    }
  };

  return (
    <div className="App">
      {step === 'home' && (
        <HomeMenu onSelectOption={handleMenuSelection} />
      )}

      {step === 'workspace' && (
        <Workspace
          onBack={() => setStep('home')}
          onUseProject={handleUseProject}
          onOpenJob={handleOpenJob}
        />
      )}

      {step === 'upload' && (
        <FileUpload 
            onFilesUploaded={handleFilesUploaded} 
            onBack={() => setStep('home')}
            projectId={activeProjectId || undefined}
        />
      )}

      {step === 'upload-review' && (
        <FileUploadReview 
            onFilesUploaded={handleFilesUploaded}
            onBack={() => setStep('home')}
            projectId={activeProjectId || undefined}
        />
      )}

      {step === 'configure' && (
        <Configuration
          columns={columns}
          onStartProcessing={handleConfigComplete}
          onBack={handleBackToUpload}
          mode={mode} // Pass mode to customize text (e.g. "Start Review" instead of "Start Coding")
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
          onStartReview={() => setStep('processing')}
          onOpenHumanReview={jobId ? () => setStep('review-queue') : undefined}
        />
      )}

      {step === 'review-queue' && jobId && (
        <ReviewQueue jobId={jobId} onBack={() => setStep('workspace')} />
      )}

      {step === 'temp-files' && (
        <TempFilesList onBack={() => setStep('home')} />
      )}
    </div>
  );
}

export default App;

# Design Document

## Overview

Esta aplicación web convierte el sistema de codificación automática de encuestas de una aplicación de escritorio Python/Flet a una arquitectura web moderna con:

- **Backend**: Python (FastAPI) que reutiliza toda la lógica existente de `ui.py`
- **Frontend**: React con TypeScript para una interfaz moderna y responsiva
- **Comunicación**: API REST + WebSockets para actualizaciones en tiempo real
- **Almacenamiento**: Sistema de archivos temporal para sesiones de usuario

### Principios de Diseño

1. **Reutilización máxima**: Todo el código de lógica de negocio de `ui.py` se reutiliza sin cambios
2. **Separación de responsabilidades**: Backend maneja procesamiento, frontend maneja UI
3. **Tiempo real**: WebSockets para actualizaciones de progreso durante el procesamiento
4. **Escalabilidad**: Procesamiento asíncrono para manejar múltiples usuarios
5. **Simplicidad**: Mantener la misma experiencia de usuario que la aplicación original

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ File Upload  │  │  Processing  │  │   Results    │      │
│  │  Component   │  │   Monitor    │  │   Download   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                           │                                  │
│                    REST API + WebSocket                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   API        │  │  Processing  │  │   Session    │      │
│  │  Endpoints   │  │   Engine     │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                           │                                  │
│              ┌────────────┴────────────┐                     │
│              │                         │                     │
│    ┌─────────▼────────┐    ┌──────────▼─────────┐          │
│    │  Core Logic      │    │   OpenAI Client    │          │
│    │  (from ui.py)    │    │   (from config.py) │          │
│    └──────────────────┘    └────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- Pandas (Excel processing)
- OpenAI Python SDK
- python-multipart (file uploads)
- python-socketio (WebSocket support)
- openpyxl (Excel file handling)

**Frontend:**
- React 18+ with TypeScript
- Axios (HTTP client)
- Socket.io-client (WebSocket)
- React Dropzone (file uploads)
- TailwindCSS (styling)
- Recharts (progress visualization)

## Components and Interfaces

### Backend Components

#### 1. API Layer (`backend/api/routes.py`)

Endpoints REST que exponen la funcionalidad:

```python
# File Upload
POST /api/upload
- Body: multipart/form-data with files
- Response: { session_id, columns, questions }

# Start Processing
POST /api/process
- Body: { session_id, selected_columns, config }
- Response: { task_id, status }

# Get Progress (polling fallback)
GET /api/progress/{task_id}
- Response: { progress, current_column, status }

# Stop Processing
POST /api/stop/{task_id}
- Response: { status, message }

# Download Results
GET /api/download/responses/{session_id}
GET /api/download/codes/{session_id}
- Response: Excel file stream
```

#### 2. Processing Engine (`backend/core/processor.py`)

Wrapper alrededor de las funciones existentes de `ui.py`:

```python
class SurveyProcessor:
    def __init__(self, session_id):
        self.session_id = session_id
        self.stop_flag = False
        self.progress_callback = None
        
    def load_files(self, responses_path, codes_path):
        """Wrapper de load_files() de ui.py"""
        return load_files(responses_path, codes_path)
    
    def process(self, responses_df, codes_df, config):
        """Wrapper de process_responses() con callbacks"""
        # Implementa callbacks para WebSocket
        return process_responses(
            responses_df, codes_df,
            config['columns'],
            config['question_column'],
            config['limit_77'],
            config['limit_labels'],
            self._status_callback,
            self._progress_callback,
            None  # page no es necesario
        )
    
    def stop(self):
        """Detiene el procesamiento"""
        global PROCESS_STOPPED
        PROCESS_STOPPED = True
        self.stop_flag = True
```

#### 3. Session Manager (`backend/core/session.py`)

Gestiona sesiones de usuario y archivos temporales:

```python
class SessionManager:
    def __init__(self):
        self.sessions = {}  # session_id -> session_data
        self.temp_dir = "temp_uploads"
        
    def create_session(self):
        """Crea una nueva sesión"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'created_at': datetime.now(),
            'files': {},
            'status': 'idle'
        }
        return session_id
    
    def save_file(self, session_id, file_type, file):
        """Guarda archivo temporal"""
        path = f"{self.temp_dir}/{session_id}_{file_type}.xlsx"
        with open(path, 'wb') as f:
            f.write(file.read())
        self.sessions[session_id]['files'][file_type] = path
        return path
    
    def cleanup_old_sessions(self):
        """Limpia sesiones > 24 horas"""
        cutoff = datetime.now() - timedelta(hours=24)
        for sid, data in list(self.sessions.items()):
            if data['created_at'] < cutoff:
                self._delete_session_files(sid)
                del self.sessions[sid]
```

#### 4. WebSocket Manager (`backend/core/websocket.py`)

Maneja conexiones WebSocket para actualizaciones en tiempo real:

```python
class WebSocketManager:
    def __init__(self, sio):
        self.sio = sio
        self.connections = {}  # session_id -> sid
    
    async def emit_progress(self, session_id, data):
        """Envía actualización de progreso"""
        if session_id in self.connections:
            await self.sio.emit('progress_update', data, 
                               room=self.connections[session_id])
    
    async def emit_status(self, session_id, status, message):
        """Envía actualización de estado"""
        if session_id in self.connections:
            await self.sio.emit('status_update', {
                'status': status,
                'message': message
            }, room=self.connections[session_id])
```

#### 5. Core Logic Module (`backend/core/logic.py`)

Importa y expone todas las funciones de `ui.py`:

```python
# Importar todas las funciones existentes
from ui import (
    load_files,
    select_columns,
    request_openai,
    assign_labels_to_response,
    create_new_labels,
    normalize_text,
    filter_exclusive_codes,
    get_next_valid_code,
    process_response,
    group_labels_codes,
    process_responses,
    update_codes_file,
    process_other_columns,
    update_used_columns,
    save_new_label
)

# Re-exportar para uso en el backend
__all__ = [
    'load_files',
    'select_columns',
    # ... todas las funciones
]
```

### Frontend Components

#### 1. App Component (`src/App.tsx`)

Componente principal que maneja el flujo de la aplicación:

```typescript
interface AppState {
  step: 'upload' | 'configure' | 'processing' | 'results';
  sessionId: string | null;
  files: {
    responses: File | null;
    codes: File | null;
  };
  columns: string[];
  config: ProcessingConfig;
}

function App() {
  const [state, setState] = useState<AppState>({
    step: 'upload',
    sessionId: null,
    files: { responses: null, codes: null },
    columns: [],
    config: defaultConfig
  });
  
  // Renderiza el componente apropiado según el step
  return (
    <div className="app">
      {state.step === 'upload' && <FileUpload />}
      {state.step === 'configure' && <Configuration />}
      {state.step === 'processing' && <ProcessingMonitor />}
      {state.step === 'results' && <Results />}
    </div>
  );
}
```

#### 2. FileUpload Component (`src/components/FileUpload.tsx`)

Maneja la carga de archivos Excel:

```typescript
interface FileUploadProps {
  onFilesUploaded: (sessionId: string, columns: string[]) => void;
}

function FileUpload({ onFilesUploaded }: FileUploadProps) {
  const [files, setFiles] = useState({
    responses: null,
    codes: null
  });
  
  const handleUpload = async () => {
    const formData = new FormData();
    formData.append('responses', files.responses);
    formData.append('codes', files.codes);
    
    const response = await axios.post('/api/upload', formData);
    onFilesUploaded(response.data.session_id, response.data.columns);
  };
  
  return (
    <div className="file-upload">
      <Dropzone onDrop={handleResponsesFile}>
        Archivo de Respuestas (.xlsx)
      </Dropzone>
      <Dropzone onDrop={handleCodesFile}>
        Archivo de Códigos (.xlsx)
      </Dropzone>
      <button onClick={handleUpload}>Cargar Archivos</button>
    </div>
  );
}
```

#### 3. Configuration Component (`src/components/Configuration.tsx`)

Permite configurar parámetros del procesamiento:

```typescript
interface ConfigurationProps {
  columns: string[];
  onStartProcessing: (config: ProcessingConfig) => void;
}

function Configuration({ columns, onStartProcessing }: ConfigurationProps) {
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [maxNewLabels, setMaxNewLabels] = useState(8);
  const [startCode, setStartCode] = useState(501);
  
  return (
    <div className="configuration">
      <h2>Seleccionar Columnas a Procesar</h2>
      <ColumnSelector 
        columns={columns}
        selected={selectedColumns}
        onChange={setSelectedColumns}
      />
      
      <h2>Configuración</h2>
      <input 
        type="number" 
        value={maxNewLabels}
        onChange={e => setMaxNewLabels(e.target.value)}
        label="Máximo de nuevas etiquetas"
      />
      <input 
        type="number" 
        value={startCode}
        onChange={e => setStartCode(e.target.value)}
        label="Código inicial para columnas OTRO"
      />
      
      <button onClick={() => onStartProcessing({
        columns: selectedColumns,
        maxNewLabels,
        startCode
      })}>
        Iniciar Procesamiento
      </button>
    </div>
  );
}
```

#### 4. ProcessingMonitor Component (`src/components/ProcessingMonitor.tsx`)

Muestra progreso en tiempo real usando WebSocket:

```typescript
interface ProcessingMonitorProps {
  sessionId: string;
  taskId: string;
  onComplete: () => void;
}

function ProcessingMonitor({ sessionId, taskId, onComplete }: ProcessingMonitorProps) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [socket, setSocket] = useState<Socket | null>(null);
  
  useEffect(() => {
    const newSocket = io('http://localhost:8000');
    
    newSocket.emit('join', { session_id: sessionId });
    
    newSocket.on('progress_update', (data) => {
      setProgress(data.progress);
      setStatus(data.message);
    });
    
    newSocket.on('status_update', (data) => {
      if (data.status === 'completed') {
        onComplete();
      }
    });
    
    setSocket(newSocket);
    
    return () => newSocket.close();
  }, [sessionId]);
  
  const handleStop = async () => {
    await axios.post(`/api/stop/${taskId}`);
  };
  
  return (
    <div className="processing-monitor">
      <h2>Procesando Respuestas</h2>
      <ProgressBar value={progress} />
      <p>{status}</p>
      <button onClick={handleStop}>Detener Proceso</button>
    </div>
  );
}
```

#### 5. Results Component (`src/components/Results.tsx`)

Muestra resultados y permite descargar archivos:

```typescript
interface ResultsProps {
  sessionId: string;
  onReset: () => void;
}

function Results({ sessionId, onReset }: ResultsProps) {
  const downloadResponses = () => {
    window.location.href = `/api/download/responses/${sessionId}`;
  };
  
  const downloadCodes = () => {
    window.location.href = `/api/download/codes/${sessionId}`;
  };
  
  return (
    <div className="results">
      <h2>Procesamiento Completado</h2>
      <div className="download-buttons">
        <button onClick={downloadResponses}>
          Descargar Respuestas Codificadas
        </button>
        <button onClick={downloadCodes}>
          Descargar Códigos Actualizados
        </button>
      </div>
      <button onClick={onReset}>Procesar Nuevos Archivos</button>
    </div>
  );
}
```

## Data Models

### Session Data

```python
{
    "session_id": "uuid-string",
    "created_at": "2025-01-15T10:30:00",
    "files": {
        "responses": "/temp/uuid_responses.xlsx",
        "codes": "/temp/uuid_codes.xlsx"
    },
    "status": "idle" | "processing" | "completed" | "error",
    "task_id": "task-uuid",
    "config": {
        "columns": ["P1", "P2_OTRO"],
        "question_column": "Nombre de la Pregunta",
        "max_new_labels": 8,
        "start_code": 501
    },
    "results": {
        "processed_columns": 5,
        "new_labels_created": 12,
        "total_records": 1500
    }
}
```

### Progress Update (WebSocket)

```typescript
{
  progress: number;  // 0-1
  message: string;   // "Procesando columna 3 de 10: P3"
  current_column: string;
  processed_records: number;
  total_records: number;
}
```

### Processing Config

```typescript
interface ProcessingConfig {
  columns: string[];
  question_column: string;
  max_new_labels: number;
  start_code: number;
  limit_77: {
    count: number;
    max: number;
    new_code: number;
    new_labels: Array<[string, string, string]>;
  };
  limit_labels: {
    count: number;
    max: number;
  };
}
```

## Error Handling

### Backend Error Handling

```python
class APIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

@app.exception_handler(APIError)
async def api_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

# Manejo de errores de OpenAI
try:
    response = request_openai(messages)
except Exception as e:
    logger.error(f"OpenAI error: {e}")
    raise APIError(
        "Error al comunicarse con OpenAI. Verifica tu API key.",
        status_code=503
    )
```

### Frontend Error Handling

```typescript
const handleError = (error: AxiosError) => {
  if (error.response) {
    // Error del servidor
    toast.error(error.response.data.error);
  } else if (error.request) {
    // Sin respuesta del servidor
    toast.error("No se pudo conectar con el servidor");
  } else {
    // Error de configuración
    toast.error("Error inesperado");
  }
};

// Uso en componentes
try {
  await axios.post('/api/process', data);
} catch (error) {
  handleError(error as AxiosError);
}
```

### Error Recovery

1. **Errores de API de OpenAI**: Reintentos automáticos (5 intentos, 10s espera)
2. **Errores de archivo**: Validación en frontend antes de subir
3. **Pérdida de conexión WebSocket**: Fallback a polling cada 2 segundos
4. **Sesión expirada**: Redirigir a inicio y solicitar nueva carga

## Testing Strategy

### Backend Testing

```python
# tests/test_processor.py
def test_load_files():
    """Verifica que load_files carga correctamente los Excel"""
    responses_df, codes_df = load_files(
        'test_data/responses.xlsx',
        'test_data/codes.xlsx'
    )
    assert not responses_df.empty
    assert 'Codificación' in codes_df

def test_process_response():
    """Verifica que process_response asigna códigos correctamente"""
    result, _ = process_response(
        question="Test question",
        response="Test response",
        available_labels=["Label1", "Label2"],
        available_codes=["01", "02"],
        limit_77={'count': 0, 'max': 100, 'new_code': 0, 'new_labels': []},
        limit_labels={'count': 0, 'max': 8},
        codes_df=test_codes_df
    )
    assert result in ["01", "02", "77", "NEW_LABEL_NEEDED"]

# tests/test_api.py
def test_upload_endpoint(client):
    """Verifica que el endpoint de upload funciona"""
    with open('test_data/responses.xlsx', 'rb') as f1:
        with open('test_data/codes.xlsx', 'rb') as f2:
            response = client.post('/api/upload', files={
                'responses': f1,
                'codes': f2
            })
    assert response.status_code == 200
    assert 'session_id' in response.json()
```

### Frontend Testing

```typescript
// src/components/__tests__/FileUpload.test.tsx
describe('FileUpload', () => {
  it('should upload files successfully', async () => {
    const mockOnFilesUploaded = jest.fn();
    render(<FileUpload onFilesUploaded={mockOnFilesUploaded} />);
    
    const responsesFile = new File(['content'], 'responses.xlsx');
    const codesFile = new File(['content'], 'codes.xlsx');
    
    // Simular drag & drop
    fireEvent.drop(screen.getByText(/Archivo de Respuestas/), {
      dataTransfer: { files: [responsesFile] }
    });
    
    fireEvent.drop(screen.getByText(/Archivo de Códigos/), {
      dataTransfer: { files: [codesFile] }
    });
    
    fireEvent.click(screen.getByText('Cargar Archivos'));
    
    await waitFor(() => {
      expect(mockOnFilesUploaded).toHaveBeenCalled();
    });
  });
});

// src/components/__tests__/ProcessingMonitor.test.tsx
describe('ProcessingMonitor', () => {
  it('should display progress updates', () => {
    const mockSocket = {
      on: jest.fn(),
      emit: jest.fn()
    };
    
    render(<ProcessingMonitor sessionId="test" taskId="test" />);
    
    // Simular actualización de progreso
    act(() => {
      mockSocket.on.mock.calls
        .find(call => call[0] === 'progress_update')[1]({
          progress: 0.5,
          message: 'Procesando columna 5 de 10'
        });
    });
    
    expect(screen.getByText(/Procesando columna 5 de 10/)).toBeInTheDocument();
  });
});
```

### Integration Testing

```python
# tests/test_integration.py
def test_full_processing_flow():
    """Test completo del flujo de procesamiento"""
    # 1. Upload files
    session_id = upload_test_files()
    
    # 2. Start processing
    task_id = start_processing(session_id, {
        'columns': ['P1', 'P2'],
        'max_new_labels': 8
    })
    
    # 3. Wait for completion
    status = wait_for_completion(task_id, timeout=60)
    assert status == 'completed'
    
    # 4. Download results
    responses_file = download_responses(session_id)
    codes_file = download_codes(session_id)
    
    assert os.path.exists(responses_file)
    assert os.path.exists(codes_file)
    
    # 5. Verify results
    df = pd.read_excel(responses_file)
    assert 'CP1' in df.columns
    assert 'CP2' in df.columns
```

## Deployment Considerations

### Development Environment

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Production Environment

```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend Dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Environment Variables

```bash
# Backend .env
OPENAI_API_KEY=sk-...
TEMP_DIR=/tmp/survey_uploads
SESSION_TIMEOUT_HOURS=24
MAX_FILE_SIZE_MB=50
CORS_ORIGINS=http://localhost:3000,https://app.example.com

# Frontend .env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### Security Considerations

1. **API Key Protection**: Nunca exponer la API key de OpenAI al frontend
2. **File Upload Validation**: Validar tipo y tamaño de archivos
3. **Session Security**: Usar tokens seguros para sesiones
4. **CORS**: Configurar orígenes permitidos
5. **Rate Limiting**: Limitar requests por IP
6. **File Cleanup**: Eliminar archivos temporales regularmente

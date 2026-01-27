# Backend - Sistema de Codificación de Encuestas

Backend Python con FastAPI que reutiliza toda la lógica del script original `ui.py`.

## Estructura

```
backend/
├── core/
│   ├── __init__.py
│   ├── logic.py          # Funciones de ui.py
│   ├── processor.py      # Wrapper de procesamiento
│   ├── session.py        # Gestión de sesiones
│   └── websocket.py      # Manager de WebSocket
├── api/
│   ├── __init__.py
│   └── routes.py         # Endpoints REST
├── main.py               # Aplicación FastAPI
├── requirements.txt      # Dependencias
└── .env                  # Variables de entorno
```

## Instalación

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` a `.env` y configura:

```env
OPENAI_API_KEY=tu-api-key-aqui
TEMP_DIR=temp_uploads
SESSION_TIMEOUT_HOURS=24
MAX_FILE_SIZE_MB=50
CORS_ORIGINS=http://localhost:5173
```

## Ejecución

```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

- `POST /api/upload` - Subir archivos Excel
- `POST /api/process` - Iniciar procesamiento
- `GET /api/progress/{task_id}` - Consultar progreso
- `POST /api/stop/{task_id}` - Detener procesamiento
- `GET /api/download/responses/{session_id}` - Descargar respuestas
- `GET /api/download/codes/{session_id}` - Descargar códigos

## WebSocket

Conectar a `/socket.io` para recibir actualizaciones en tiempo real:

- `progress_update` - Actualización de progreso
- `status_update` - Cambio de estado

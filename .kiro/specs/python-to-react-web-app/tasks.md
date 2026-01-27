# Implementation Plan

- [x] 1. Configurar estructura del proyecto



  - Crear directorios para backend (Python/FastAPI) y frontend (React/TypeScript)
  - Configurar archivos de configuración (package.json, requirements.txt, tsconfig.json)
  - Configurar variables de entorno (.env files)


  - _Requirements: 9.1, 10.7_

- [x] 2. Extraer y modularizar lógica del script Python existente


  - [x] 2.1 Crear módulo core/logic.py con todas las funciones de ui.py

    - Copiar funciones: load_files, select_columns, request_openai, assign_labels_to_response, create_new_labels, normalize_text, filter_exclusive_codes, get_next_valid_code, process_response, group_labels_codes, process_responses, update_codes_file, process_other_columns, update_used_columns, save_new_label
    - Importar cliente OpenAI desde config.py
    - Mantener variables globales PROCESS_STOPPED, MODIFIED_CELLS, questions_dict
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [x] 2.2 Crear módulo core/processor.py con clase SurveyProcessor


    - Implementar __init__ con session_id y flags de control
    - Implementar método load_files que llama a la función de logic.py
    - Implementar método process con callbacks para progreso
    - Implementar método stop que actualiza PROCESS_STOPPED
    - _Requirements: 9.1, 9.8_

- [x] 3. Implementar gestión de sesiones y archivos temporales



  - [x] 3.1 Crear módulo core/session.py con clase SessionManager


    - Implementar create_session() que genera UUID
    - Implementar save_file() para guardar archivos Excel temporales
    - Implementar get_session() para recuperar datos de sesión
    - Implementar cleanup_old_sessions() para eliminar sesiones > 24 horas
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 3.2 Crear directorio temp_uploads y configurar permisos


    - Crear directorio si no existe al iniciar la aplicación
    - Configurar .gitignore para excluir archivos temporales
    - _Requirements: 12.1_

- [x] 4. Implementar WebSocket para actualizaciones en tiempo real



  - [x] 4.1 Crear módulo core/websocket.py con clase WebSocketManager


    - Configurar python-socketio con FastAPI
    - Implementar emit_progress() para enviar actualizaciones de progreso
    - Implementar emit_status() para enviar cambios de estado
    - Implementar manejo de conexiones (join/leave rooms)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 4.2 Integrar WebSocketManager con SurveyProcessor


    - Modificar callbacks en process() para emitir via WebSocket
    - Enviar actualizaciones cada vez que cambia el progreso
    - _Requirements: 11.2, 11.3, 11.4_

- [x] 5. Crear endpoints REST de la API



  - [x] 5.1 Implementar endpoint POST /api/upload


    - Recibir archivos multipart/form-data
    - Validar formato Excel (.xlsx, .xls)
    - Crear sesión y guardar archivos temporales
    - Cargar archivos con load_files() y extraer columnas/preguntas
    - Retornar session_id, columnas disponibles y preguntas
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 10.1_

  - [x] 5.2 Implementar endpoint POST /api/process


    - Recibir session_id y configuración (columnas, límites)
    - Validar que la sesión existe
    - Iniciar procesamiento asíncrono en background task
    - Retornar task_id y estado inicial
    - _Requirements: 2.5, 3.1, 3.2, 3.3, 3.4, 10.3_

  - [x] 5.3 Implementar endpoint GET /api/progress/{task_id}


    - Consultar estado actual del procesamiento
    - Retornar progreso, columna actual, registros procesados
    - Servir como fallback si WebSocket falla
    - _Requirements: 4.1, 4.2, 10.4_

  - [x] 5.4 Implementar endpoint POST /api/stop/{task_id}


    - Actualizar flag PROCESS_STOPPED
    - Cancelar procesamiento en curso
    - Retornar estado actualizado
    - _Requirements: 3.8, 4.3, 4.4, 4.5, 10.5_

  - [x] 5.5 Implementar endpoints GET /api/download/responses y /api/download/codes


    - Recuperar archivos procesados de la sesión
    - Generar nombres con timestamp
    - Retornar archivos Excel como stream
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 10.6_

- [x] 6. Implementar manejo de errores en el backend


  - Crear clase APIError personalizada
  - Implementar exception handlers para FastAPI
  - Manejar errores de OpenAI con reintentos (5 intentos, 10s)
    - Capturar excepciones en request_openai()
    - Implementar lógica de reintento con sleep
    - Retornar error descriptivo si todos los intentos fallan
  - Validar archivos antes de procesarlos
  - Retornar códigos HTTP apropiados (400, 404, 500, 503)
  - _Requirements: 6.4, 6.5, 8.1, 8.2, 8.3, 8.5, 10.7_

- [x] 7. Crear aplicación FastAPI principal



  - [x] 7.1 Crear main.py con configuración de FastAPI


    - Inicializar app FastAPI
    - Configurar CORS para permitir frontend
    - Montar SocketIO
    - Incluir routers de API
    - _Requirements: 10.1-10.7_

  - [x] 7.2 Configurar middleware y logging


    - Agregar middleware de logging para requests
    - Configurar manejo de errores global
    - Agregar validación de tamaño de archivos
    - _Requirements: 8.1, 8.5_

  - [x] 7.3 Crear archivo requirements.txt


    - Listar dependencias: fastapi, uvicorn, pandas, openpyxl, python-multipart, python-socketio, openai
    - Especificar versiones compatibles
    - _Requirements: 9.1_

- [x] 8. Configurar proyecto React con TypeScript


  - [x] 8.1 Inicializar proyecto con Vite

    - Ejecutar `npm create vite@latest frontend -- --template react-ts`
    - Instalar dependencias base
    - _Requirements: 7.1_

  - [x] 8.2 Instalar dependencias adicionales

    - Instalar axios para HTTP requests
    - Instalar socket.io-client para WebSocket
    - Instalar react-dropzone para file uploads
    - Instalar tailwindcss para estilos
    - Instalar react-toastify para notificaciones
    - _Requirements: 7.1, 8.2_

  - [x] 8.3 Configurar TailwindCSS


    - Inicializar configuración de Tailwind
    - Agregar directivas a CSS principal
    - _Requirements: 7.1_

- [x] 9. Crear tipos TypeScript y servicios



  - [x] 9.1 Crear types/index.ts con interfaces


    - Definir AppState, ProcessingConfig, ProgressUpdate, SessionData
    - Exportar todos los tipos
    - _Requirements: 7.1_

  - [x] 9.2 Crear services/api.ts con funciones de API


    - Implementar uploadFiles() que llama POST /api/upload
    - Implementar startProcessing() que llama POST /api/process
    - Implementar getProgress() que llama GET /api/progress
    - Implementar stopProcessing() que llama POST /api/stop
    - Configurar axios con baseURL desde variables de entorno
    - _Requirements: 1.1, 2.5, 4.3, 10.1-10.5_

  - [x] 9.3 Crear services/websocket.ts con cliente WebSocket


    - Implementar clase WebSocketClient con socket.io-client
    - Implementar connect() y disconnect()
    - Implementar onProgressUpdate() y onStatusUpdate()
    - _Requirements: 4.1, 4.2, 11.2, 11.3, 11.4_

- [x] 10. Implementar componente FileUpload



  - [x] 10.1 Crear componente FileUpload.tsx


    - Usar react-dropzone para drag & drop
    - Mostrar dos zonas de drop (respuestas y códigos)
    - Validar tipo de archivo (.xlsx, .xls)
    - Mostrar preview de archivos seleccionados
    - _Requirements: 1.1, 1.2_

  - [x] 10.2 Implementar lógica de upload


    - Crear FormData con ambos archivos
    - Llamar a uploadFiles() del servicio API
    - Manejar respuesta con session_id y columnas
    - Mostrar errores si la validación falla
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 8.2_

  - [x] 10.3 Agregar estilos responsivos

    - Adaptar layout para móvil, tablet y desktop
    - Usar clases de Tailwind para responsividad
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 11. Implementar componente Configuration


  - [x] 11.1 Crear componente Configuration.tsx


    - Recibir lista de columnas como prop
    - Mostrar checkboxes para seleccionar columnas
    - Mostrar inputs para configuración (max_new_labels, start_code)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 11.2 Implementar ColumnSelector subcomponente

    - Renderizar lista de columnas con checkboxes
    - Permitir seleccionar/deseleccionar todas
    - Filtrar columnas por búsqueda
    - _Requirements: 2.2_

  - [x] 11.3 Implementar validación de configuración

    - Validar que al menos una columna esté seleccionada
    - Validar que max_new_labels sea > 0
    - Validar que start_code sea válido
    - Deshabilitar botón si configuración inválida
    - _Requirements: 2.5, 8.5_

  - [x] 11.4 Implementar botón de inicio

    - Llamar a startProcessing() con configuración
    - Transicionar a vista de procesamiento
    - _Requirements: 2.5_

- [x] 12. Implementar componente ProcessingMonitor


  - [x] 12.1 Crear componente ProcessingMonitor.tsx


    - Conectar a WebSocket al montar
    - Mostrar barra de progreso visual
    - Mostrar mensaje de estado actual
    - Mostrar botón de detener
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 12.2 Implementar conexión WebSocket

    - Conectar usando WebSocketClient
    - Suscribirse a eventos progress_update y status_update
    - Actualizar estado local con datos recibidos
    - Desconectar al desmontar componente
    - _Requirements: 4.1, 4.2, 11.2, 11.3, 11.4_

  - [x] 12.3 Implementar barra de progreso

    - Usar componente visual para mostrar porcentaje
    - Animar transiciones de progreso
    - Mostrar contador de registros procesados
    - _Requirements: 4.1, 4.2_

  - [x] 12.4 Implementar botón de detener

    - Llamar a stopProcessing() del servicio API
    - Mostrar confirmación antes de detener
    - Actualizar UI cuando se detiene
    - _Requirements: 4.3, 4.4, 4.5_

  - [x] 12.5 Implementar fallback a polling

    - Si WebSocket falla, usar polling cada 2 segundos
    - Llamar a getProgress() periódicamente
    - Detener polling cuando completa o hay error
    - _Requirements: 4.1, 10.4_

- [x] 13. Implementar componente Results


  - [x] 13.1 Crear componente Results.tsx


    - Mostrar mensaje de éxito
    - Mostrar resumen de procesamiento (columnas, etiquetas nuevas, registros)
    - Mostrar botones de descarga
    - Mostrar botón para procesar nuevos archivos
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 4.6_

  - [x] 13.2 Implementar descarga de archivos

    - Crear enlaces a /api/download/responses y /api/download/codes
    - Usar window.location.href o fetch con blob
    - Mostrar indicador de descarga en progreso
    - _Requirements: 5.4, 5.5, 5.6_

  - [x] 13.3 Implementar botón de reset

    - Limpiar estado de la aplicación
    - Volver a vista de upload
    - _Requirements: 5.6_

- [x] 14. Implementar componente App principal


  - [x] 14.1 Crear App.tsx con gestión de estado


    - Definir estado con step, sessionId, files, columns, config
    - Implementar funciones para cambiar entre steps
    - _Requirements: 7.1_

  - [x] 14.2 Implementar navegación entre vistas

    - Renderizar componente apropiado según step
    - Pasar props necesarias a cada componente
    - Manejar transiciones entre steps
    - _Requirements: 7.1_

  - [x] 14.3 Implementar manejo de errores global

    - Usar react-toastify para mostrar notificaciones
    - Capturar errores de API y mostrar mensajes
    - Implementar error boundary para errores de React
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 15. Agregar estilos y responsividad

  - Aplicar estilos de Tailwind a todos los componentes
  - Implementar diseño responsivo para móvil
    - Ajustar layout de FileUpload para pantallas pequeñas
    - Hacer ColumnSelector scrollable en móvil
    - Adaptar barra de progreso para móvil
  - Implementar diseño para tablet
    - Optimizar espaciado para pantallas medianas
  - Agregar animaciones y transiciones
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 16. Configurar variables de entorno


  - [x] 16.1 Crear archivo .env para backend


    - Configurar OPENAI_API_KEY desde config.py
    - Configurar TEMP_DIR, SESSION_TIMEOUT_HOURS, MAX_FILE_SIZE_MB
    - Configurar CORS_ORIGINS
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 16.2 Crear archivo .env para frontend

    - Configurar VITE_API_URL (http://localhost:8000)
    - Configurar VITE_WS_URL (ws://localhost:8000)
    - _Requirements: 10.1-10.6_

  - [x] 16.3 Actualizar config.py para usar variables de entorno

    - Importar os y cargar API key desde env
    - Mantener fallback a valor hardcoded para desarrollo
    - _Requirements: 6.1, 6.2_

- [x] 17. Crear documentación y scripts de desarrollo



  - [x] 17.1 Crear README.md con instrucciones

    - Documentar requisitos del sistema
    - Documentar instalación de dependencias
    - Documentar cómo ejecutar backend y frontend
    - Documentar estructura del proyecto
    - _Requirements: 9.1_

  - [x] 17.2 Crear scripts de desarrollo

    - Crear script start-backend.sh/bat
    - Crear script start-frontend.sh/bat
    - Crear script start-all.sh/bat que inicia ambos
    - _Requirements: 9.1_

- [ ] 18. Testing y validación
  - [ ]* 18.1 Crear tests unitarios para backend
    - Test para load_files()
    - Test para process_response()
    - Test para SessionManager
    - Test para endpoints de API
    - _Requirements: 9.1-9.8_

  - [ ]* 18.2 Crear tests para frontend
    - Test para FileUpload component
    - Test para ProcessingMonitor component
    - Test para servicios de API
    - _Requirements: 1.1-1.6, 4.1-4.6_

  - [ ]* 18.3 Crear test de integración end-to-end
    - Test del flujo completo: upload → configure → process → download
    - Usar archivos de prueba reales
    - Verificar que los archivos generados son correctos
    - _Requirements: 1.1-8.5_

- [ ] 19. Preparar para deployment
  - [ ]* 19.1 Crear Dockerfile para backend
    - Usar imagen base python:3.11-slim
    - Copiar requirements.txt e instalar dependencias
    - Copiar código fuente
    - Exponer puerto 8000
    - _Requirements: 9.1_

  - [ ]* 19.2 Crear Dockerfile para frontend
    - Usar multi-stage build (node para build, nginx para servir)
    - Copiar archivos build a nginx
    - Configurar nginx.conf
    - _Requirements: 7.1_

  - [ ]* 19.3 Crear docker-compose.yml
    - Definir servicios backend y frontend
    - Configurar networking entre servicios
    - Configurar volúmenes para archivos temporales
    - _Requirements: 9.1, 7.1_

# Requirements Document

## Introduction

Este documento define los requisitos para convertir una aplicación de escritorio Python (Flet) de codificación automática de encuestas con IA en una aplicación web moderna. La arquitectura será:
- **Backend**: Python (Flask/FastAPI) reutilizando toda la lógica existente del script actual (ui.py)
- **Frontend**: React para la interfaz de usuario web

La aplicación actual utiliza OpenAI para codificar respuestas de encuestas de forma automática, permitiendo cargar archivos Excel con respuestas y códigos, procesar las respuestas usando IA, y exportar los resultados codificados. La nueva aplicación web debe mantener TODA la funcionalidad existente del script Python mientras proporciona una interfaz web moderna, escalable y fácil de usar.

## Requirements

### Requirement 1: Carga y Gestión de Archivos

**User Story:** Como usuario, quiero cargar archivos Excel con respuestas de encuestas y códigos de clasificación, para que el sistema pueda procesarlos automáticamente.

#### Acceptance Criteria

1. WHEN el usuario accede a la aplicación THEN el sistema SHALL mostrar una interfaz para cargar dos archivos Excel (respuestas y códigos)
2. WHEN el usuario selecciona un archivo Excel THEN el sistema SHALL validar que el archivo tenga el formato correcto (.xlsx o .xls)
3. WHEN el usuario carga el archivo de respuestas THEN el sistema SHALL leer y mostrar las columnas disponibles
4. WHEN el usuario carga el archivo de códigos THEN el sistema SHALL leer la hoja 'Codificación' y mostrar las preguntas disponibles
5. IF el archivo no tiene el formato correcto THEN el sistema SHALL mostrar un mensaje de error descriptivo
6. WHEN ambos archivos están cargados THEN el sistema SHALL habilitar las opciones de configuración del proceso

### Requirement 2: Configuración del Proceso de Codificación

**User Story:** Como usuario, quiero configurar los parámetros del proceso de codificación, para que pueda controlar cómo se procesan las respuestas.

#### Acceptance Criteria

1. WHEN los archivos están cargados THEN el sistema SHALL mostrar opciones para seleccionar columnas de respuestas a procesar
2. WHEN el usuario selecciona columnas THEN el sistema SHALL permitir seleccionar múltiples columnas usando checkboxes
3. WHEN el usuario configura el proceso THEN el sistema SHALL permitir establecer límites para nuevas etiquetas (máximo 8 por defecto)
4. WHEN el usuario configura el proceso THEN el sistema SHALL permitir establecer el código inicial para columnas "_OTRO" (501 por defecto)
5. WHEN la configuración está completa THEN el sistema SHALL habilitar el botón para iniciar el procesamiento

### Requirement 3: Procesamiento con IA de Respuestas

**User Story:** Como usuario, quiero que el sistema procese automáticamente las respuestas usando IA, para que las respuestas sean codificadas de forma consistente y precisa.

#### Acceptance Criteria

1. WHEN el usuario inicia el procesamiento THEN el sistema SHALL enviar las respuestas a OpenAI para su codificación
2. WHEN se procesa una respuesta THEN el sistema SHALL intentar asignar códigos existentes antes de crear nuevos
3. WHEN no existe un código apropiado THEN el sistema SHALL crear una nueva etiqueta usando IA
4. WHEN se crea una nueva etiqueta THEN el sistema SHALL asignar el siguiente código válido disponible
5. IF se alcanza el límite de nuevas etiquetas THEN el sistema SHALL asignar el código 77 (sin clasificar)
6. WHEN se procesan columnas "_OTRO" o "_OTRA" THEN el sistema SHALL aplicar lógica especial para reemplazar el código 77
7. WHEN ocurre un error en la API THEN el sistema SHALL reintentar hasta 5 veces con espera de 10 segundos
8. IF el proceso es detenido por el usuario THEN el sistema SHALL cancelar las solicitudes pendientes y retornar los datos procesados

### Requirement 4: Monitoreo y Control del Proceso

**User Story:** Como usuario, quiero ver el progreso del procesamiento en tiempo real y poder detenerlo si es necesario, para tener control sobre el proceso.

#### Acceptance Criteria

1. WHEN el procesamiento está en curso THEN el sistema SHALL mostrar una barra de progreso con el porcentaje completado
2. WHEN el procesamiento está en curso THEN el sistema SHALL mostrar el estado actual (columna y registro siendo procesado)
3. WHEN el procesamiento está en curso THEN el sistema SHALL mostrar un botón para detener el proceso
4. WHEN el usuario detiene el proceso THEN el sistema SHALL cancelar las operaciones pendientes inmediatamente
5. WHEN el usuario detiene el proceso THEN el sistema SHALL preservar los datos procesados hasta ese momento
6. WHEN el procesamiento finaliza THEN el sistema SHALL mostrar un resumen de las operaciones realizadas

### Requirement 5: Exportación y Descarga de Resultados

**User Story:** Como usuario, quiero descargar los archivos procesados con las codificaciones aplicadas, para poder usar los resultados en mi análisis.

#### Acceptance Criteria

1. WHEN el procesamiento finaliza THEN el sistema SHALL generar dos archivos Excel actualizados
2. WHEN se generan los archivos THEN el sistema SHALL incluir las nuevas columnas de códigos (formato C{columna})
3. WHEN se generan los archivos THEN el sistema SHALL actualizar el archivo de códigos con las nuevas etiquetas creadas
4. WHEN los archivos están listos THEN el sistema SHALL proporcionar botones de descarga para ambos archivos
5. WHEN el usuario descarga un archivo THEN el sistema SHALL usar nombres descriptivos con timestamp
6. WHEN se descargan los archivos THEN el sistema SHALL mantener el formato Excel original

### Requirement 6: Gestión de API Keys y Configuración Backend

**User Story:** Como usuario, quiero que el sistema use la configuración de API key existente del script Python, para que funcione sin configuración adicional.

#### Acceptance Criteria

1. WHEN el backend inicia THEN el sistema SHALL cargar la API key desde config.py (igual que el script actual)
2. WHEN se realiza una llamada a OpenAI THEN el sistema SHALL usar el cliente OpenAI configurado con la API key
3. WHEN se usa el modelo THEN el sistema SHALL usar "gpt-5" con max_completion_tokens=400 (igual que el script)
4. IF la API key es inválida THEN el sistema SHALL manejar errores de autenticación y retornar mensajes apropiados al frontend
5. WHEN ocurre un error de API THEN el sistema SHALL implementar la misma lógica de reintentos (5 intentos, 10 segundos de espera)

### Requirement 7: Interfaz de Usuario Responsiva

**User Story:** Como usuario, quiero usar la aplicación desde diferentes dispositivos, para poder trabajar desde cualquier lugar.

#### Acceptance Criteria

1. WHEN el usuario accede desde un navegador de escritorio THEN el sistema SHALL mostrar una interfaz optimizada para pantallas grandes
2. WHEN el usuario accede desde una tablet THEN el sistema SHALL adaptar la interfaz al tamaño de pantalla
3. WHEN el usuario accede desde un móvil THEN el sistema SHALL mostrar una versión móvil funcional
4. WHEN la ventana cambia de tamaño THEN el sistema SHALL ajustar los elementos de la interfaz dinámicamente
5. WHEN se muestran tablas de datos THEN el sistema SHALL permitir scroll horizontal en pantallas pequeñas

### Requirement 8: Manejo de Errores y Validaciones

**User Story:** Como usuario, quiero recibir mensajes claros cuando algo sale mal, para poder corregir los problemas rápidamente.

#### Acceptance Criteria

1. WHEN ocurre un error THEN el sistema SHALL mostrar un mensaje descriptivo del problema
2. WHEN falla la carga de un archivo THEN el sistema SHALL indicar qué está mal con el archivo
3. WHEN falla una llamada a la API THEN el sistema SHALL mostrar el error y sugerir acciones
4. WHEN se detectan datos inválidos THEN el sistema SHALL resaltar los campos problemáticos
5. IF el usuario intenta procesar sin configurar correctamente THEN el sistema SHALL prevenir la acción y mostrar qué falta


### Requirement 9: Arquitectura Backend Python

**User Story:** Como desarrollador, quiero que el backend reutilice toda la lógica del script Python existente, para mantener la funcionalidad probada y evitar reescribir código.

#### Acceptance Criteria

1. WHEN se implementa el backend THEN el sistema SHALL reutilizar las funciones existentes: load_files, select_columns, request_openai, assign_labels_to_response, create_new_labels, process_response, process_responses, process_other_columns
2. WHEN se procesa una solicitud THEN el sistema SHALL usar la misma lógica de normalización de texto (normalize_text)
3. WHEN se filtran códigos THEN el sistema SHALL usar filter_exclusive_codes con los mismos códigos excluidos (66, 77, 88, 99, 777, 888, 999)
4. WHEN se asignan nuevos códigos THEN el sistema SHALL usar get_next_valid_code con la misma lógica
5. WHEN se guardan nuevas etiquetas THEN el sistema SHALL usar save_new_label y update_codes_file
6. WHEN se actualizan columnas THEN el sistema SHALL usar update_used_columns preservando la lógica de celdas modificadas
7. WHEN se procesan respuestas THEN el sistema SHALL mantener la variable global questions_dict y MODIFIED_CELLS
8. WHEN se detiene el proceso THEN el sistema SHALL usar la misma lógica de PROCESS_STOPPED

### Requirement 10: API REST para Comunicación Frontend-Backend

**User Story:** Como desarrollador frontend, quiero endpoints REST claros para comunicarme con el backend, para poder construir la interfaz React.

#### Acceptance Criteria

1. WHEN el frontend carga archivos THEN el sistema SHALL proporcionar un endpoint POST /api/upload para recibir archivos Excel
2. WHEN se solicitan columnas THEN el sistema SHALL proporcionar un endpoint GET /api/columns para retornar columnas disponibles
3. WHEN se inicia el procesamiento THEN el sistema SHALL proporcionar un endpoint POST /api/process para iniciar la codificación
4. WHEN se consulta el progreso THEN el sistema SHALL proporcionar un endpoint GET /api/progress para retornar estado en tiempo real
5. WHEN se detiene el proceso THEN el sistema SHALL proporcionar un endpoint POST /api/stop para cancelar el procesamiento
6. WHEN se descargan resultados THEN el sistema SHALL proporcionar endpoints GET /api/download/responses y GET /api/download/codes
7. WHEN ocurre un error THEN el sistema SHALL retornar códigos HTTP apropiados (400, 500) con mensajes descriptivos en JSON

### Requirement 11: Procesamiento Asíncrono y WebSockets

**User Story:** Como usuario, quiero ver actualizaciones en tiempo real del progreso, para saber exactamente qué está procesando el sistema.

#### Acceptance Criteria

1. WHEN el procesamiento inicia THEN el sistema SHALL ejecutar el proceso en un thread separado para no bloquear el servidor
2. WHEN hay progreso THEN el sistema SHALL enviar actualizaciones via WebSocket o Server-Sent Events al frontend
3. WHEN se procesa una columna THEN el sistema SHALL enviar el nombre de la columna y el progreso actual
4. WHEN se procesa un registro THEN el sistema SHALL actualizar el contador de registros procesados
5. WHEN finaliza el procesamiento THEN el sistema SHALL enviar un mensaje de completado con resumen
6. IF el usuario cierra la conexión THEN el sistema SHALL continuar el procesamiento en background

### Requirement 12: Manejo de Sesiones y Estado

**User Story:** Como usuario, quiero que el sistema mantenga mi sesión y archivos cargados, para poder continuar trabajando sin recargar archivos.

#### Acceptance Criteria

1. WHEN el usuario carga archivos THEN el sistema SHALL almacenar los archivos temporalmente en el servidor con un ID de sesión
2. WHEN se procesa THEN el sistema SHALL asociar el procesamiento con la sesión del usuario
3. WHEN hay múltiples usuarios THEN el sistema SHALL mantener sesiones separadas sin interferencia
4. WHEN finaliza una sesión THEN el sistema SHALL limpiar archivos temporales después de 24 horas
5. IF el servidor se reinicia THEN el sistema SHALL manejar la pérdida de sesiones gracefully

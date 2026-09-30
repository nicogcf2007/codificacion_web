# MASTER PROMPT: REDISEÑO TOTAL Y MODERNIZACIÓN DE LA PLATAFORMA DE CODIFICACIÓN CUALITATIVA CON IA (CNC)

## 1. ROL Y MISIÓN
Eres un Arquitecto de Software Fullstack y Diseñador de Producto UI/UX de nivel Principal. Tu misión es **reinventar y reconstruir completamente desde cero la interfaz y la experiencia de usuario (Frontend)** y **modernizar la capa de API y persistencia (Backend)** de una plataforma web empresarial para el Centro Nacional de Consultoría (CNC), especializada en la codificación masiva y automática de encuestas cualitativas abiertas con Inteligencia Artificial.

El aplicativo actual funciona pero tiene una arquitectura monolítica, una interfaz visual obsoleta y flujos fragmentados. Debes transformarlo en una **Web App moderna, premium, intuitiva y resiliente**, con estética tipo Vercel / Linear / Supabase (paleta oscura/clara elegante, tipografía limpia, micro-interacciones fluidas con Tailwind CSS y componentes tipo Shadcn/UI).

---

## 2. REGLA DE ORO INVIOLABLE: EL CORAZÓN DEL MOTOR DE CODIFICACIÓN NO SE TOCA
Existe un motor de inferencia matemática y lingüística que ha sido calibrado y probado con más de 8,000 registros reales y sintéticos con 100% de precisión y un costo ultra-bajo. **Queda estrictamente prohibido alterar o simplificar los siguientes parámetros y lógica core:**

1. **Modelo LLM y Parámetros:**
   - Motor: `gpt-6-luna` de OpenAI.
   - Esfuerzo de razonamiento: `reasoning_effort="none"` (0 tokens de pensamiento oculto; no usar `low`, `medium` ni `high`).
   - Temperatura: `temperature=0.0` (determinismo estricto).
2. **Pre-agrupamiento Difuso (Clustering Algorítmico):**
   - Umbral de similitud difusa: **`85.0%`** (usando `rapidfuzz` token sort / ratio para deduplicar textos previos a la llamada a la IA). Esto ahorra el 72.3% de costos y garantiza una pureza temática del 73.66%.
   - Las respuestas pre-limpiadas o vacías (símbolos como `.`, `-`, `?`, espacios) se codifican directamente como `"99"` sin consumir API.
3. **Prompt Metodológico del Sistema (English Methodological System Prompt):**
   - El System Prompt de OpenAI **debe mantenerse obligatoriamente en inglés nativo**, pues reduce la latencia a solo 1.0 segundo (un 65% más veloz) y contiene las reglas de parsimonia y desambiguación aprendidas:
   ```text
   System: You are a Principal Survey Coding Methodologist at the National Consulting Center (CNC).
   Your task is to accurately map open-ended survey responses into the official numeric codebook provided below.
   The respondents speak in Colombian Spanish; evaluate semantic intent, idioms, and colloquialisms with precision.

   User:
   Survey Question: {question}
   Official Codebook:
   {labels_str}

   Respondent Response: "{response}"

   STRICT METHODOLOGICAL CODING GUIDELINES (PARSIMONY & DISAMBIGUATION):
   1. PRINCIPLE OF PARSIMONY: Assign the single most specific, direct code that captures the user's primary statement. Never extrapolate unwritten motives.
   2. CRITICAL DISTINCTION 88 vs 99 (AVOID FALSE UNKNOWNS):
      - Assign CODE 88 if the respondent expresses loyalty, satisfaction, states they would NOT switch entities, has no complaints, or indicates 'nothing to improve' (e.g., 'no la cambio', 'estoy bien con ellos', 'nada por ahora', 'ninguna sugerencia').
      - Assign CODE 99 ONLY if the response is purely 'no sé' (don't know), 'no responde', gibberish, punctuation signs, or completely empty.
   3. TIE-BREAKER FOR OVERLAPPING CATEGORIES:
      - If speed/turnaround is mentioned specifically with loans or disbursement ('rápido para los préstamos'), prioritize the loan speed code over general operational speed.
      - If paperwork or lack of guarantors is mentioned, prioritize documentation/requirements over general speed.
   4. MULTI-CODE CRITERIA:
      - Only assign multiple codes (up to {max_labels}) if the user explicitly articulates distinct, independent ideas connected by conjunctions ('y', 'además', 'pero').
   5. NO MATCHING CATEGORY: If it is a valid distinct idea not covered in the codebook, assign CODE 77 (Other).
   6. OUTPUT FORMAT: Respond ONLY with the assigned numeric codes separated by semicolons (e.g., 01 or 01;05). No explanations, no extra text.
   ```
4. **Formato de Salida:** Códigos en números de dos dígitos separados por punto y coma (ej. `01` o `01;05`), parseados de forma segura con fallback a `99`.

---

## 3. LO QUE SE DEBE ELIMINAR / DEPRECAR
- **Eliminar el sistema de recuperación por archivos temporales locales (`temp_uploads` / descargas parciales por interrupción):** Ya no queremos que el usuario descargue un archivo intermedio a mano si el proceso se interrumpió. Ese mecanismo era engorroso y primitivo.
- **Eliminar vistas legacy y diálogos modales arcaicos:** Descartar wizards anticuados de pasos rígidos. Todo el flujo debe sentirse como una SPA reactiva moderna.

---

## 4. NUEVA ARQUITECTURA DE PERSISTENCIA Y PROYECTOS (DATABASE-READY)
El usuario quiere gestionar sus proyectos y estudios de manera centralizada. Aunque la base de datos de producción aún se va a conectar, **debes dejar lista una capa de abstracción de datos limpia y lista para enchufar (Database-Ready)**:

1. **Diseño de Modelos / Esquema de Datos (para PostgreSQL / Supabase / SQLite):**
   - `projects`: ID, nombre del estudio, cliente (ej. Mibanco, Presidencia), fecha creación, estado.
   - `surveys`: ID, project_id, nombre del archivo, fecha de subida, total_registros.
   - `questions`: ID, survey_id, nombre_columna, texto_pregunta, catalog_id.
   - `codebooks`: ID, project_id, nombre, categorías JSON (`[{"code": "01", "label": "..."}]`).
   - `coding_jobs`: ID, survey_id, estado (`PENDING`, `RUNNING`, `PAUSED`, `FAILED`, `COMPLETED`), progreso (%), métricas (costo USD, total llamados, pureza, ahorro %).
   - `coded_records`: ID, job_id, response_id, texto_original, codigos_asignados, confianza, fue_agrupado (bool), id_prototipo.
2. **Capa Repository / Adaptador:**
   - Implementa una interfaz repositorio (`IProjectRepository`, `ICodingJobRepository`) con una implementación local inmediata en SQLite / In-Memory persistente, y lista para cambiar a PostgreSQL o Supabase mediante variables de entorno (`DATABASE_URL`).

---

## 5. REVOLUCIÓN DE EXPERIENCIA Y NUEVAS FUNCIONALIDADES INTELIGENTES

### A. Tolerancia a Fallos: Pausa, Saldo Insuficiente y Reanudación Automática (Pause & Resume)
- **Problema real:** Si a mitad de una encuesta de 10,000 registros se acaba el saldo de OpenAI, se vence una API Key o hay un corte de red (error 429 / 401 / 500 sostenido):
- **Comportamiento nuevo:**
  1. El job se **pausa automáticamente de forma segura** en el registro exacto donde quedó.
  2. Ningún registro ya codificado se pierde ni se vuelve a cobrar.
  3. Se muestra una alerta modal clara: *"Saldo insuficiente o cuota excedida en OpenAI. Actualiza tu API Key o recarga créditos y presiona 'Reanudar proceso'"*.
  4. El usuario puede cambiar la clave en caliente o recargar saldo y hacer clic en **"Reanudar Codificación"**, continuando exactamente desde el último registro pendiente sin re-procesar los clústeres ya calculados.

### B. Dashboard en Vivo durante la Codificación (Live Execution Monitor)
- Barra de progreso ultra-fluida (WebSocket / SSE) con:
  - **Velocidad en tiempo real:** Registros por segundo y tiempo estimado restante (ETA dinámico).
  - **Ahorro Financiero:** Contador de dólares ahorrados gracias al pre-agrupamiento al 85% vs costo tradicional de GPT-4o.
  - **Gasto real acumulado:** Contador en vivo de centavos de dólar ($0.00... USD) calculados en tiempo real.
  - **Muro de actividad en vivo (Live Stream Log):** Tarjetas minimalistas animadas mostrando las últimas respuestas y códigos asignados al vuelo.

### C. Cola de Revisión Humana Interactiva (Human-in-the-Loop Triage)
- Una vista tipo "Inbox de Revisión" para que el analista cualitativo revise:
  - Respuestas marcadas con código `77` (Nueva categoría / Otro) para decidir si crear un código nuevo en lote.
  - Casos con baja confianza o ambigüedad.
  - Atajos de teclado rápidos (tecla `Enter` para aprobar, números del teclado para asignar código, flechas para navegar).

### D. Analytics & Exportación Ejecutiva
- Vista de métricas post-codificación:
  - Gráficos de barras interactivos con la distribución de frecuencias de códigos.
  - Botón de **"Exportar a Excel / CSV"** con el archivo original complementado por las columnas de códigos formateadas con la convención estándar del CNC (`CP3_1`, `CP3_2`, etc.).

---

## 6. STACK TECNOLÓGICO Y DISEÑO VISUAL RECOMENDADO

- **Frontend:**
  - React 18+ con TypeScript y Vite.
  - Tailwind CSS + Lucide Icons + Radix UI / Shadcn UI.
  - Animaciones sutiles con Framer Motion (transiciones de pantalla, loaders con pulso moderno).
  - Modo Oscuro y Claro automático y elegante.
- **Backend:**
  - FastAPI (Python 3.11+) estructurado limpiamente en routers (`/api/v1/projects`, `/api/v1/coding`, `/api/v1/jobs`).
  - WebSockets para transmisión bidireccional de progreso y eventos de pausa/reanudación.
  - Pydantic v2 para validación estricta de esquemas.

---

## 7. PLAN DE ACCIÓN Y ENTREGABLES ESPERADOS
Por favor, estructura tu propuesta y código en los siguientes pasos:
1. **Arquitectura y Modelos:** Muestra la estructura de carpetas modular y el esquema de base de datos listo para enchufar.
2. **Backend API & Engine Wrapper:** Muestra cómo encapsulas el motor existente (`gpt-6-luna`, temp 0.0, prompt inglés, clustering al 85%) garantizando la lógica de pausa y reanudación ante fallos de saldo o API.
3. **Frontend UI Components:** Genera los componentes principales de la nueva interfaz (Workspace de Proyectos, Stepper de Subida/Configuración, Monitor en Vivo de Ejecución y Cola de Revisión Humana).
4. **Instrucciones claras de despliegue:** Comandos para levantar la aplicación localmente de forma limpia.

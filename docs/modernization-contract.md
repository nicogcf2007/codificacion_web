# Contrato de modernización CNC v1

El motor legacy no se modifica. La aplicación nueva no usa sesiones temporales ni `temp_uploads`. Todos los endpoints siguientes tienen prefijo `/api/v1`. REST devuelve objetos JSON y listas en envolturas explícitas. Los errores usan `detail` (texto o lista Pydantic). Fechas UTC ISO 8601. Estado de job `PENDING|RUNNING|PAUSED|FAILED|COMPLETED`. `progress` es 0..100. No hay datos demo automáticos.

## Recursos

- `GET /health`: `{status:'healthy', provider_mode:'blocked'|'demo'|'openai', database:'sqlite'|'postgresql', auth_required:boolean}`. No devuelve secretos.
- `GET /projects`: `{projects: Project[]}`.
- `POST /projects`: `{name,client}` => Project (201).
- Project: `{id,name,client,status,created_at,survey_count,job_count}`.
- `GET /projects/{id}/codebooks`: `{codebooks: Codebook[]}`.
- `POST /projects/{id}/codebooks`: `{name,categories:[{code,label}],max_labels:1..6}` => Codebook (201). Códigos exactamente dos dígitos; no normalizar códigos inválidos. Lista no vacía ni duplicados.
- Codebook: `{id,project_id,name,categories,max_labels,created_at}`.
- `GET /projects/{id}/surveys`: `{surveys: Survey[]}`.
- `POST /projects/{id}/surveys`: multipart `file` (.xlsx/.csv), conserva original como blob en DB; sin recuperación por disco. => Survey (201).
- Survey: `{id,project_id,filename,total_records,columns:string[],preview:object[],created_at}` (preview limitado).
- `POST /coding/jobs`: `{survey_id,name,questions:[{column_name,question_text,codebook_id}]}` => Job (201, PENDING). Valida columnas únicas, catálogo y encuesta del mismo proyecto. Persistir configuración, clústeres y prototipos una sola vez. No llama proveedor.
- `GET /jobs?project_id=`: `{jobs:Job[]}`.
- `GET /jobs/{id}`: Job.
- Job: `{id,project_id,survey_id,name,status,progress,total_records,processed_records,created_at,updated_at,pause_reason:string|null,provider_mode,metrics:Metrics,questions:JobQuestion[]}`.
- JobQuestion: `{id,column_name,question_text,codebook_id,categories,max_labels}`.
- Metrics: `{api_calls,saved_calls,savings_pct,cost_usd:number|null,saved_usd:number|null,purity:number|null,records_per_second,eta_seconds:number|null,input_tokens,output_tokens}`. Las tarifas son configurables. Costes no disponibles = null; pureza no medida = null. Ahorro de llamadas calculado, nunca constante de benchmark.
- `POST /jobs/{id}/start` o `/resume`: cuerpo opcional `{retry_uncertain:false}` => Job. No se permite tarea simultánea. `/pause` => Job con pausa cooperativa; esperar y persistir resultado de llamada en curso antes de detener. Errores 401/429/5xx/red se pausan sin codificar error como 99. Llamada iniciada sin checkpoint tras caída => pausa por resultado incierto, no repetir sin consentimiento explícito.
- `GET /jobs/{id}/events`: SSE `event: snapshot`, `data: {job:Job,records:CodedRecord[]}`; snapshot inicial, luego polling DB/heartbeat; reconexión recupera DB. Consumir por fetch streaming si se configura token Bearer.
- `GET /jobs/{id}/records?review_only=true`: `{records:CodedRecord[]}`. Puede limitar la lista a 200, pero `GET .../analytics` y exportación siempre incluyen TODOS los registros.
- CodedRecord: `{id,job_id,response_id,column_name,text_original,codes:string[],confidence:number|null,was_grouped,prototype_id,review_status:'PENDING'|'APPROVED',review_reason:string|null}`. Se revisan 77, parsing inválido, agrupamiento difuso ambiguo; sin inventar confianza LLM.
- `PATCH /jobs/{id}/records/{record_id}`: `{codes:string[],review_status:'APPROVED'}` => CodedRecord. Validar contra snapshot del catálogo y cardinalidad. Decisión humana auditable.
- `POST /jobs/{id}/review/batch`: `{record_ids:string[],code:string,label:string}` => `{updated:number}`. Crea categoría humana y aplica a registros seleccionados de una sola pregunta, transacción única; catálogo del job/snapshot actualizado. Rechazar mezclar preguntas o modificar RUNNING.
- `GET /jobs/{id}/analytics`: `{distribution:[{question_id,column_name,code,label,count}],total_records,processed_records,pending_review}`. Se agrupa por pregunta y código: el mismo número puede significar cosas distintas en catálogos diferentes. Multi-código cuenta cada mención; no inferir porcentaje de personas.
- `GET /jobs/{id}/export?format=xlsx|csv`: descarga original (valores y columnas) + columnas `C{column_name}_{1..max_labels}`, preservando ceros iniciales. Rechazar colisión con columnas originales y jobs no COMPLETED. XLSX sin fórmulas; CSV neutraliza celdas peligrosas. Nombres seguros generados por servidor.
- `POST /settings/openai-key`: `{api_key}` => `{configured:true}`. Solo autorizado con APP_ACCESS_TOKEN, sin devolver/loggear clave; cambio en memoria server-side, reinicio requiere variable OPENAI_API_KEY. No registrar request body.

## Seguridad y proveedor

`CODING_PROVIDER=blocked` por defecto (sin llamadas reales). `demo` explícito es una simulación sintética y debe identificarse en UI, métricas y job. `openai` respeta exactamente `gpt-6-luna`, `reasoning_effort='none'`, `temperature=0.0`, prompt inglés existente. No sustituir modelo si rechaza parámetros. OPENAI_API_KEY nunca llega al frontend. APP_ACCESS_TOKEN se introduce en ajustes y viaja en header Authorization Bearer (solo memoria del navegador). Si APP_ACCESS_TOKEN está configurado se exige en todos los endpoints excepto health. Arrancar proveedor real exige token configurado, credencial y autorización; sin ello fallar cerrado. SSE incluye mismo header. Servicio local por defecto en loopback, un worker. PostgreSQL/Supabase a través de DATABASE_URL con SQLAlchemy y psycopg; no afirmar verificación remota sin conectar.

## Propiedad del trabajo

Backend: nuevos módulos `backend/modern/`, `backend/api/v1/`, pruebas `backend/tests/modern/` y requirements (no editar main.py ni core legacy). Frontend: `frontend/src/modern/`, App.tsx, index.css, vite.config.ts, package.json/lock y pruebas frontend. Integración/documentación/verificación: agente principal, main.py, Docker/Compose y documentación. No tocar eliminaciones previas IDEA.md/MASTER_PROMPT_REDISENO_UI_UX.md ni archivos reales Excel, .env/config con credenciales. No commit/push/deploy.

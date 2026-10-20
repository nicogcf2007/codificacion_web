# CNC Studio · Codificación cualitativa

React/TypeScript + FastAPI v1 + SQLAlchemy. Proyectos, bases, catálogos, clústeres, resultados y revisión humana se guardan en la base de datos. Acceso empresarial por correo/contraseña, sesiones con cookies y proyectos compartidos. No hay autoregistro ni credenciales de proveedor en el frontend.

## 1. Arquitectura y esquema

```text
backend/
  main.py                   # Entrada moderna; sin SessionManager ni temp_uploads
  api/v1/routes.py           # Estudios, jobs, SSE, revisión y exportación
  modern/
    app.py                  # Factory, autorización, ciclo de vida y SPA local
    db.py                   # Esquema SQLAlchemy SQLite/PostgreSQL
    repository.py           # IProjectRepository / ICodingJobRepository
    study.py                # Archivos, catálogos y planes de clústeres persistidos
    engine.py               # Wrapper y proveedores blocked/demo/openai
    runtime.py              # Checkpoints, pausa y recuperación
    results.py              # Revisión auditada, analytics y exportación
    schemas.py              # Validación Pydantic 2
  core/                     # Motor original, sin cambios
  tests/modern/             # Pruebas aisladas y regresiones independientes
frontend/src/modern/
  Console.tsx               # Navegación, sesión, perfil y temas
  Workspace.tsx             # Proyectos y búsqueda
  Composer.tsx              # Base, catálogo editable y múltiples preguntas
  Monitor.tsx               # SSE autenticado, reconexión y respaldo REST
  Review.tsx                # Inbox, atajos y categorías humanas en lote
  Analytics.tsx             # Distribución por pregunta y descargas
  api.ts                    # Cookies de sesión, CSRF y parser de transmisión
  studio.css                # Diseño claro/oscuro adaptable
scripts/run-local.ps1       # Arranque local seguro para Windows
scripts/create-admin.ps1    # Primer administrador sin detener el servidor
tests/modern_session_browser_smoke.py
```

Tablas: `projects`, `surveys`, `questions`, `codebooks`, `coding_jobs`, `coding_prototypes`, `coded_records`, `audit_events`. El original se guarda como blob; cada job conserva una copia de sus preguntas y catálogos. `coding_prototypes` guarda el plan y sus checkpoints.

Contrato de endpoints y campos: [docs/modernization-contract.md](docs/modernization-contract.md). Contrato de sesiones, roles y auditoría: [docs/session-ui-contract.md](docs/session-ui-contract.md).

## 2. Motor y reanudación

- Modelo literal **`gpt-6-luna`**, `reasoning_effort="none"`, `temperature=0.0`. Sin fallback de modelo/proveedor.
- Prompt metodológico en inglés; una regresión lo compara con el método original aislado mediante AST, sin inicializar clientes ni configuración legacy.
- Clustering original con umbral **85.0**. El código calibrado usa `token_set_ratio`: se conserva, no se sustituye por `token_sort_ratio`.
- Vacíos/símbolos reconocidos por el core reciben `99` sin API. Una salida inválida recibe `99` y revisión; **un fallo del proveedor nunca se convierte en una codificación**.
- Prototipo y registros se confirman en una sola transacción. Reanudar no repite prototipos completados ni recalcula los clústeres.
- 401/429 pausan con instrucciones. Red/5xx o una interrupción inflight dejan un resultado **incierto**; reintentar exige un booleano JSON `true` explícito y puede generar otro cargo. No se promete facturación exactamente una vez cuando se pierde una respuesta externa.
- La pausa manual espera a que termine la solicitud en curso y guarda su resultado.
- Confianza/pureza quedan sin valor si no se miden. Las cifras históricas del prompt maestro no se muestran como métricas live.

## 3. Interfaz y flujo

1. Iniciar sesión, crear/seleccionar proyecto y subir Excel `.xlsx`/`.xls` o CSV desde el botón o la zona de arrastre. Límites: 50 MB, 50.000 filas y 500 columnas; `.xls` limita también la lectura a 2.000.000 de celdas. Se codifica la hoja activa de XLSX o la primera hoja de XLS.
2. Guardar catálogo oficial con códigos exactos de dos dígitos y máximo de 1–6 códigos.
3. Seleccionar columnas, escribir cada pregunta y vincular su catálogo.
4. Preparar el plan; **iniciar por separado** en Monitor. Preparar no llama al proveedor.
5. Pausar/reanudar y recuperar el job guardado desde Ejecuciones tras cerrar el navegador o reiniciar el servidor.
6. Revisar códigos 77, salidas inválidas y agrupamientos difusos: flechas navegan, números eligen, Enter aprueba. Los atajos no interfieren al escribir. Una categoría humana nueva puede aplicarse a un lote de una sola pregunta.
7. Consultar frecuencias separadas por pregunta y exportar Excel/CSV. Para una columna `P3`, se añaden `CP3_1`, `CP3_2`, etc. Se detectan colisiones y neutralizan fórmulas peligrosas en celdas **y encabezados**. La exportación requiere un job completado y avisa si queda revisión pendiente.

Los `.xls` se exportan como `.xlsx`: se conservan valores de las hojas y se añaden códigos CNC a la primera; no se preservan macros, fórmulas ejecutables ni estilos BIFF originales. Solo existen Modo Claro y Modo Oscuro, con oscuro inicial y preferencia `cnc-theme` en localStorage. La sesión no se almacena allí.

## 4. Instalación local · PowerShell

Python 3.11+ (validado con 3.12) y Node 22.12+; se recomienda Node 22 LTS. Desde la raíz del repositorio:

```powershell
# Solo si backend/venv todavía no existe:
uv venv --python 3.12 backend/venv

uv pip install --python backend/venv/Scripts/python.exe -r backend/requirements-dev.txt
cd frontend
npm ci
npm run build
cd ..
```

### Una consola: interfaz compilada y backend

La primera cuenta es ADMIN y se crea **solo desde el servidor**. En una consola PowerShell interactiva:

```powershell
.\scripts\run-local.ps1 -BootstrapAdmin -AdminEmail 'tu-correo@empresa.com' -AdminName 'Tu nombre'
```

El script solicita la contraseña con entrada oculta (mínimo 12 caracteres), la pasa al servidor y restaura las variables al salir. No escribe contraseñas en archivos ni ofrece registro público. Reiniciar no cambia la contraseña de usuarios existentes. También puede provisionarse el primer ADMIN mediante `CNC_ADMIN_EMAIL`, `CNC_ADMIN_PASSWORD` y `CNC_ADMIN_NAME` en el gestor de entorno del servidor. Sin primer administrador no existe acceso anónimo alternativo: el login permanece cerrado.

Si el servidor **ya está ejecutándose**, no inicies una segunda instancia: provisiona la primera cuenta sin detenerlo con `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\create-admin.ps1`. Solicita correo y contraseña oculta; puedes pasar `-Email` y `-Name` (nunca una contraseña como argumento). No crea ni resetea cuentas cuando ya existen usuarios. Usa la misma `DATABASE_URL` del servidor o su SQLite predeterminado. Después, inicia sesión en el navegador; no requiere reiniciar.

Después de la primera configuración:

```powershell
# Seguro por defecto: organiza estudios, pero bloquea llamadas de IA.
.\scripts\run-local.ps1

# Alternativa explícita de demostración, sin OpenAI:
.\scripts\run-local.ps1 -Provider demo
```

Abre `http://127.0.0.1:8000`. El backend sirve `frontend/dist`. SQLite predeterminado: **`backend/data/modern.sqlite3`**, resuelto con ruta absoluta.

Si la política de PowerShell bloquea scripts, inicia el backend directamente, sin cambiar esa política:

```powershell
$env:CODING_PROVIDER = 'blocked'
.\backend\venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
```

### Dos consolas: desarrollo con recarga

```powershell
# Consola 1, raíz del repositorio:
.\scripts\run-local.ps1 -Reload

# Consola 2:
cd frontend
npm run dev -- --host 127.0.0.1
```

Frontend: `http://127.0.0.1:5173`. API: `http://127.0.0.1:8000/api/v1`. Documentación: `http://127.0.0.1:8000/docs`. Vite enruta `/api` al backend.

## Configuración del servidor

| Variable | Uso |
|---|---|
| `DATABASE_URL` | SQLite o PostgreSQL; ausente: SQLite local absoluto. |
| `CODING_PROVIDER` | `blocked` predeterminado, `demo` explícito u `openai` real. |
| `CNC_ADMIN_EMAIL` / `CNC_ADMIN_PASSWORD` / `CNC_ADMIN_NAME` | Bootstrap inicial del administrador, solo en entorno server-side; no resetea cuentas existentes. |
| `CNC_ENV` | `production` exige configuración segura de cookies. |
| `CNC_COOKIE_SECURE` | `true` con HTTPS en producción; `false` solo en desarrollo HTTP local. |
| `OPENAI_API_KEY` | Solo en el servidor. Nunca una variable `VITE_*`. |
| `CORS_ORIGINS` | Orígenes permitidos separados por comas; por defecto los dos orígenes locales de Vite. |
| `INPUT_USD_PER_MILLION` | Tarifa de entrada que tú hayas verificado para el modelo. |
| `OUTPUT_USD_PER_MILLION` | Tarifa de salida verificada. |
| `BASELINE_RECORD_USD` | Coste de referencia por respuesta para estimar ahorro. |

Sin tarifas no se inventa un precio: los dólares quedan no disponibles. Las tarifas deben ser números finitos no negativos; una configuración inválida se rechaza antes de codificar. Los dólares mostrados son **estimaciones, no una factura**, y la referencia no se interpreta como una tarifa automática de GPT-4o.

No se carga automáticamente un `.env` heredado. Configura variables del servicio; si necesitas un archivo local propio, usa explícitamente `--env-file` de Uvicorn y mantenlo fuera de Git. No pongas credenciales en código ni las envíes por chat.

### Proveedor real

Configura privadamente `OPENAI_API_KEY` en el servidor y usa `CODING_PROVIDER=openai` o `run-local.ps1 -Provider openai`. El acceso se controla con la sesión del usuario. Pulsa **Iniciar codificación** de forma explícita. No existe panel de conexión, input de API Key ni ruta de actualización de credencial desde el navegador.

La API Key se cambia en el entorno del servicio y requiere reiniciar el servidor. Las sesiones usan un identificador aleatorio en cookie HttpOnly, hash y expiración en DB, revocación al cerrar sesión y control CSRF para mutaciones. No se guardan tokens bearer en memoria/localStorage. Todos los usuarios activos ven todos los proyectos; solo ADMIN crea cuentas y consulta la auditoría global. Una contraseña provisional obliga a cambiarla antes de acceder a los datos.

**No se llamó al proveedor real durante las pruebas.** Confirma acceso/disponibilidad del identificador literal `gpt-6-luna` y las tarifas de tu cuenta antes de autorizar una prueba pagada. Un rechazo de modelo/parámetros pausa el job: no cambia el motor.

### PostgreSQL / Supabase

Usa una URL PostgreSQL del servidor (`postgresql://…` o `postgresql+psycopg://…`). La aplicación utiliza psycopg. Para Supabase se utiliza la conexión PostgreSQL, no el API REST ni una clave expuesta al frontend.

SQLAlchemy crea las tablas iniciales y requiere permisos adecuados en una base dedicada. **No migra bases legacy ni transfiere estudios al cambiar la URL.** SQLite se verificó en ejecución; PostgreSQL requiere una prueba contra tu instancia. Antes de producción, respalda datos y define migraciones/versionado.

## Docker Compose

Con Docker instalado:

```bash
docker compose up --build -d
docker compose ps
```

Interfaz: `http://127.0.0.1:8080`. El backend no publica un puerto al host; Nginx enruta `/api` y SSE sin buffering. El volumen `codificacion_data` conserva SQLite. Sin volumen de recuperación temporal.

- `APP_PORT` y `APP_HOST` cambian puerto y dirección de escucha.
- La imagen backend copia solo los módulos modernos necesarios y el clustering original, no configuraciones legacy, credenciales o encuestas locales.
- `docker-compose.dokploy.yml` es un overlay opcional para una instalación que ya tenga la red externa `dokploy-network`; no se usa en el arranque local normal.
- Docker no está instalado en la máquina de validación: **no se construyeron ni ejecutaron las imágenes** y no se hizo despliegue remoto.

Antes de publicar: HTTPS, `CNC_ENV=production`, `CNC_COOKIE_SECURE=true`, `CORS_ORIGINS` con el origen HTTPS exacto, cuentas de administrador provisionadas y copias de seguridad. Se mantiene **una sola instancia/worker** para codificación: no usar varias réplicas ni `--workers 2` sin un lease/cola coordinados. La visibilidad es empresarial compartida, no aislamiento por propietario ni una plataforma multiempresa.

## Verificación reproducible

```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/modern -q
.\backend\venv\Scripts\python.exe -m unittest discover -s tests -p test_delivery_contract.py -v
cd frontend
npm run lint
npm run build
npm test
npm audit --audit-level=low
cd ..
```

Pruebas con SQLite aislado, datos sintéticos y proveedores ficticios. La auditoría independiente además bloquea construir un cliente SDK real. No ejecutar benchmarks legacy ni usar encuestas reales para probar.

Smoke de sesiones real en Chromium: instalar con `backend/venv/Scripts/python.exe -m playwright install chromium` y ejecutar `backend/venv/Scripts/python.exe tests/modern_session_browser_smoke.py`. El test levanta su propio servidor loopback y una **base SQLite nueva en scratch**, con usuarios sintéticos de contraseña aleatoria. No se conecta a la instancia del usuario ni al proveedor real; bloquea solicitudes externas del navegador. Cubre login, cookies, logout, alta ADMIN, cuenta provisional, restricciones STANDARD, proyectos compartidos, XLSX por selector, XLS por arrastre, ejecución sintética, revisión, exportación, auditoría atribuida, temas y móvil. Los smoke anteriores de Bearer/sin sesión son históricos de la entrega previa y no prueban el contrato actual.

Resultados y límites de la entrega: [docs/verification.md](docs/verification.md).

## Licencia

Privado · Centro Nacional de Consultoría.
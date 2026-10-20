# Verificación local de CNC Studio

Fecha: 30 de septiembre de 2026. Entorno: Windows, Python 3.12.10, Chromium headless.

## Actualización vigente: sesiones, roles, carga Excel y limpieza de interfaz

Esta sección sustituye las cifras y el contrato de autorización de la entrega anterior que se documenta abajo como historial. **Bearer, token compartido, ajustes de conexión y campos de API Key ya no forman parte del frontend actual.**

| Comprobación actual | Resultado ejecutado |
|---|---|
| Backend `pytest backend/tests/modern` | **104 aprobadas**, 0 fallos; SQLite aislada, proveedores ficticios y red bloqueada en fixtures |
| Frontend `npm test` | **35 aprobadas** en 9 suites |
| Empaquetado/provisionamiento `unittest … test_*delivery*.py` | **7 aprobadas**; creación del primer ADMIN y segundo intento sin reset verificados en DB sintética |
| ESLint, TypeScript y Vite build | Exit 0 |
| `npm audit --audit-level=low` | **0 vulnerabilidades npm** |
| `uv pip check` | 75 paquetes compatibles |
| Scripts PowerShell | Parser de `run-local.ps1` y `create-admin.ps1` válido |
| Core original | **4/4 hashes sin cambios**; diff staged y unstaged vacío |
| Instancia operativa `http://127.0.0.1:8000` | Reiniciada en modo blocked; `auth_required=true`, proyectos anónimos 401; login oscuro validado en Chromium, sin errores JS |

### Recorrido HTTP completo con sesiones reales

`tests/modern_session_browser_smoke.py` crea su propio servidor loopback, una nueva DB en scratch, dos cuentas sintéticas y contraseñas aleatorias; nunca usa la instancia operativa ni el proveedor real de codificación. Resultado **exit 0, passed=true, 23 comprobaciones, 22 registros sintéticos, 30 eventos de auditoría leídos de la API, 0 errores JS y 0 solicitudes externas del navegador**.

- Login sin autoregistro y cookie de sesión HttpOnly; logout revoca acceso.
- ADMIN crea una cuenta STANDARD con contraseña provisional; la cuenta no accede a proyectos hasta cambiarla.
- STANDARD abre el proyecto creado por ADMIN y no puede consultar `/admin/users` (403); su navegación no muestra administración.
- Perfil de sesión con nombre e iniciales `AP` para la identidad sintética.
- XLSX mediante selector de archivo y XLS mediante `DataTransfer`/drop reales; error de extensión inválida controlado.
- Catálogo, plan, ejecución explícitamente ficticia, SSE y revisión por teclado funcionan con sesión real.
- Descarga Excel de un XLS: valores y hoja auxiliar conservados, identificadores con ceros y columnas `CP3_1`/`CP3_2` verificadas.
- Auditoría de upload, catálogo, preparación/inicio, checkpoints asíncronos y aprobación atribuida exactamente al usuario de servidor.
- Oscuro inicial aunque el sistema sea claro; solo dos opciones, preferencia conservada al recargar/cerrar sesión y únicamente `cnc-theme` en localStorage.
- Móvil de 390 px sin desbordamiento horizontal; contraste computado de texto principal claro **13,43:1**. Esta medición no equivale a una auditoría WCAG integral.
- Recarga superior conservada; ninguna leyenda de proveedor, modelo, API Key, conexión o estado técnico en las pantallas del recorrido.

Evidencia: `C:/Users/CNC/AppData/Local/hermes/cache/scratch/cnc-session-browser-wrign1b2/browser-results.json`, seis capturas y `synthetic-export.xlsx`. JUnit actual: `C:/Users/CNC/AppData/Local/hermes/cache/scratch/cnc-session-final-tests.xml`. Login de la instancia operativa: `C:/Users/CNC/AppData/Local/hermes/cache/scratch/cnc-session-local-login.png`.

### Revisión independiente actual

El intento `deleg_1e3cd9d0` falló por HTTP 429: **no fue una aprobación**. Se obtuvo después un dictamen independiente mediante OpenCode, ruta comercial `openrouter/anthropic/claude-sonnet-4.6`, sobre un paquete inmutable de 13 archivos de código/contrato sin datos reales ni credenciales. Se verificaron permisos denegados del agente y una prueba de conectividad antes de enviar el paquete. Resultado parseado: **passed=true, security_concerns=[], logic_errors=[]**.

Alcance: auth, factory, esquemas, DB, repository, runtime, rutas, StudyRepository, frontend API/Session y scripts de primer ADMIN. El revisor fue **estático**: no ejecutó pruebas ni auditó CSS, Admin/Upload, parsing XLS o motor. La verificación runtime corresponde a las pruebas y Chromium del padre. No es una auditoría integral de producción. SHA-256 del paquete: `a5107255dc7e76dbd5dc78d8a4dedfddb2ece38d7b24caccff3919159abfbbaa`; manifiesto/dictamen en scratch `session-review-manifest.json` y `session-review-verdict.json`.

Observaciones no bloqueantes: configurar proxies de confianza antes de publicar para no agrupar a todo el equipo en el bucket de login; mantener sanitización de mensajes del proveedor; respaldos/migraciones y HTTPS/Secure en producción. La observación del revisor sobre la convención HMAC no demuestra un defecto: `hmac.new(token, mensaje, sha256)` utiliza la firma correcta y el token aleatorio secreto como clave; no se cambió. No se cambió el procesamiento de fórmulas XLSX por una recomendación genérica.

**Primer acceso pendiente de datos del usuario:** la consulta read-only de cantidad de cuentas de la instancia operativa confirmó que aún no hay administrador configurado. No se inventó ni publicó una contraseña administrativa. Desde la raíz del proyecto, `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\create-admin.ps1` solicita correo y contraseña oculta, provisiona solo la primera cuenta y no necesita detener el servidor. Variables de servidor: `CNC_ADMIN_EMAIL`, `CNC_ADMIN_PASSWORD`, `CNC_ADMIN_NAME`. Si ya existen cuentas, no las cambia. Los usuarios adicionales se crean dentro de Usuarios por ADMIN.

**Límites actuales:** no hubo llamadas reales de codificación, cambios de proveedor del motor, commit, push ni despliegue remoto. La llamada externa del revisor de código es distinta del proveedor de codificación de la aplicación. Docker y PostgreSQL runtime siguen sin probarse. Se conserva un solo worker; no hay aislamiento multiempresa. El aviso previo de pandas/pyarrow persiste y no bloquea la suite.

---

## Historial de la entrega anterior (antes del sistema de usuarios)

## Resultados ejecutados

| Comprobación | Resultado |
|---|---|
| Backend `pytest backend/tests/modern` | **59 aprobadas**, 0 fallos, 0 omitidas |
| Empaquetado `unittest … test_delivery_contract.py` | **3 aprobadas** |
| Frontend `npm test` | **9 aprobadas** en 4 archivos |
| ESLint y TypeScript/Vite build | Exit 0 |
| `npm audit --audit-level=low` | **0 vulnerabilidades npm** |
| `uv pip check` | Dependencias instaladas compatibles |
| Instalación Python declarada, dry-run | No requiere cambios |
| `git diff --check` | Exit 0; solo avisos de conversión LF/CRLF |
| Hashes del core original | 4/4 coinciden con el baseline; diff staged y unstaged vacíos |
| PowerShell: parser, arranque y guardia | Sintaxis válida, servidor iniciado en demo; modo OpenAI sin credenciales rechazado con exit 1 |
| PostgreSQL DDL | 8 tablas compiladas localmente; **no conexión PostgreSQL** |

Aviso no bloqueante: pandas 2.2 emite una advertencia de deprecación sobre pyarrow. No fue una regresión de las pruebas.

## Navegador real

`tests/modern_browser_smoke.py` ejecutado contra un servidor local explícitamente demo y una base SQLite nueva en scratch:

- 22 registros sintéticos; creación de proyecto, upload CSV, catálogo y pregunta.
- Preparación sin llamadas de proveedor; inicio, pausa cooperativa y reanudación.
- Finalización transmitida por SSE y progreso al 100% leído de la API.
- Asignación con teclado y aprobación; categoría humana en lote, con read-back de registros.
- Gráfico por pregunta y descargas reales CSV/XLSX; todas las filas, ceros iniciales, columnas CNC y neutralización de fórmulas en encabezados/celdas.
- Modo oscuro/claro, viewport móvil de 390 px sin scroll horizontal y persistencia al recargar.
- Avisos transitorios correctos, indicador de actividad guardada al completar y padding del contrato del motor.
- **0 errores JavaScript y 0 solicitudes del navegador a hosts externos.**

`tests/modern_browser_auth_smoke.py` ejecutado contra otro servidor local **blocked**, con token de aplicación exclusivamente sintético:

- Sin token: recursos privados devuelven 401.
- El formulario Ajustes autoriza peticiones reales a la API con Bearer.
- Se verifica creación y lectura autenticada de un proyecto sintético.
- El campo se vacía y recargar pierde la autorización; localStorage conserva solo el tema.
- **0 errores JavaScript y 0 solicitudes externas.**

El coste cero de demo no es una medición de eficiencia ni de precisión del modelo. Ninguna asignación de demostración procede de OpenAI.

## Revisión independiente

La revisión independiente inicial añadió regresiones y encontró cuatro clases de defectos:

| Hallazgo inicial | Corrección y evidencia local |
|---|---|
| Encabezados exportados podían convertirse en fórmulas | `safe_cell` también para encabezados CSV/XLSX; regresiones y descargas de navegador aprobadas |
| Código idéntico de catálogos distintos mezclaba frecuencias/etiquetas | Agrupación por pregunta y código, contrato/types/chart alineados; regresiones aprobadas |
| Consentimiento de reintento aceptaba strings o números | Booleano Pydantic estricto; regresiones rechazan coerciones |
| CSV/XML corruptos podían devolver 500 o dejar recursos abiertos | Parsing controlado, límite declarado y cierre de Excel en finally; regresiones aprobadas |

Los fallos iniciales no se ocultaron con xfail. Las regresiones independientes pasan ahora dentro de las 59 pruebas. **La reverificación final independiente está aprobada**: `deleg_c7f6f89e` ejecutó la suite de nuevo (59 aprobadas, 0 fallos, exit 0), confirmó los cuatro fixes y la alineación del contrato con los tipos y Analytics. No quedan hallazgos originales sin resolver.

Su alcance fue el cierre de esos cuatro hallazgos y los seis archivos solicitados, no una nueva auditoría integral de producción. El revisor comprobó el diff unstaged del core; el padre verificó además hashes y diff staged. No hubo SDK real, red externa, Git remoto, Docker ni PostgreSQL durante esa revisión. Un intento anterior de cierre falló por HTTP 429 del proveedor del revisor, pero el dictamen final no estuvo bloqueado por cuota.

Dictamen recibido y contrastado con `C:/Users/CNC/AppData/Local/hermes/cache/delegation/live/deleg_c7f6f89e/task-0.log`.

## Evidencias de la sesión

Carpeta local: `C:/Users/CNC/AppData/Local/hermes/cache/scratch/cnc-delivery-browser-evidence/`.

- `browser-results.json`: resultado y 16 comprobaciones del recorrido demo.
- `browser-auth-results.json`: resultado del recorrido de autorización bloqueado.
- Capturas reales de configuración, monitor, revisión, resultados, proyectos y móvil; `monitor-preview.png` es un viewport real actualizado, no un mockup.
- Exportaciones CSV y XLSX sintéticas descargadas por Chromium.

JUnit: `C:/Users/CNC/AppData/Local/hermes/cache/scratch/cnc-delivery-pytest.xml`.

Los archivos de scratch son evidencia temporal de QA, no la base de datos operativa del proyecto.

## Alcance pendiente para producción

- **Proveedor real:** no hubo llamadas reales, consumo de saldo ni benchmarks de precisión. Falta confirmar el acceso a `gpt-6-luna` y las tarifas antes de una prueba pagada autorizada.
- **PostgreSQL/Supabase:** esquema portable y DDL compilado; falta conectar y verificar una instancia real. No se migraron estudios legacy.
- **Docker:** no instalado; se ajustó el empaquetado y se probaron sus contratos estáticos, no imágenes ejecutadas.
- **Distribución/RBAC, estado histórico:** la entrega anterior usaba token compartido. La actualización actual usa usuarios, roles y cookies; permanece el requisito de un único ejecutor. Varias réplicas requieren coordinación/leases; producción requiere HTTPS, permisos y respaldos.
- **Git y despliegue:** no se hizo commit, push ni despliegue remoto. Se conservaron los cambios preexistentes del usuario, incluidas sus eliminaciones de documentos.

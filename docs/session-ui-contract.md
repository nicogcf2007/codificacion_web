# Contrato de sesiones y espacio empresarial compartido

## Identidad

`User`: `{id,email,name,role:'ADMIN'|'STANDARD',active,must_change_password,created_at}`. Todos los usuarios activos comparten todos los proyectos; no aplicar filtros de propietario. Solo ADMIN crea cuentas, consulta auditoría global y resumen administrativo. Sin autoregistro público.

- `POST /api/v1/auth/login {email,password}` → `{user,csrf_token}`. Cookie `cnc_session` HttpOnly, identificador aleatorio, hash en DB, expiración y revocación. Cookie `cnc_csrf` legible por JS para añadir `X-CSRF-Token` a mutaciones; vinculada a la sesión. No bearer, API key ni tokens de autenticación en memoria/localStorage del frontend.
- `GET /api/v1/auth/me` → `{user,csrf_token}` o 401.
- `POST /api/v1/auth/logout` → `{ok:true}`; revoca sesión y borra cookies.
- `POST /api/v1/auth/password {current_password,password}` → `{user,csrf_token}`. Permite reemplazar contraseña provisional y revoca otras sesiones; el login provisional no permite acceder a datos hasta el cambio.
- `GET /api/v1/admin/users` → `{users:User[]}`.
- `POST /api/v1/admin/users {email,name,password,role,must_change_password}` → User, 201. Contraseña temporal/definitiva según flag; nunca retorna hash/contraseña.
- `GET /api/v1/admin/audit?limit=50&offset=0` → `{events:[{id,actor_id,actor_name,actor_email,action,resource_type,resource_id,project_id,job_id,created_at}],total}`. Se pueden añadir campos outcome/detail seguros sin respuestas ni credenciales.
- `GET /api/v1/admin/overview` → `{projects,jobs,users,active_jobs,completed_jobs}` derivados de DB.

Rehidratar el usuario activo en cada petición; 401 sin sesión y 403 sin rol/CSRF. Validar origen de mutaciones, SameSite=Lax, Secure obligatorio en producción HTTPS, respuestas privadas no-store, errores de login genéricos y limitación de intentos. Contraseñas Argon2id, bootstrap ADMIN exclusivamente mediante `CNC_ADMIN_EMAIL`, `CNC_ADMIN_PASSWORD`, `CNC_ADMIN_NAME` en entorno del servidor (sin defaults secretos). La ausencia de bootstrap no abre la API; el login permanece cerrado. Bootstrap solo crea el primer admin; reiniciar no resetea usuarios/contraseñas.

## Trazabilidad

Registrar identidad del servidor en creación de proyectos, upload, catálogo, preparación/inicio/pausa/reanudación, revisión y categoría en lote; mantener actor del trabajo en ejecución asíncrona/checkpoints. No aceptar actor desde payload del cliente. Conservar auditoría previa como histórica sin atribuir autores inventados. No tocar `backend/core` ni parámetros/prompt del motor.

## Interfaz

Login con correo y contraseña; sin registro. Perfil de sesión con iniciales/nombre, menú y logout. Vistas Usuarios/Auditoría/Resumen solo ADMIN. Ocultar detalles de proveedor, modelo, clave y estado de API en Console, Composer, Monitor, Review y Analytics, manteniendo recarga superior y progreso/estado funcional del trabajo. Para demo explícita mantener aviso neutral 'Datos de demostración; no usar como resultados reales' sin referencia técnica al proveedor.

Tema solo light/dark, oscuro inicial incluso con sistema claro, persistir solo `cnc-theme`. Acento azul y contraste claro/oscuro. Carga accesible por botón y drag-and-drop .xlsx/.xls/.csv con límite visible, filename/progreso/errores. No crear datos demo automáticamente.

## Verificación

SQLite aislada en scratch, usuarios/contraseñas sintéticas, proveedor bloqueado o fake; ningún dato real, key real ni red de proveedor. Tests RED→GREEN, sin commit/push/deploy. Primer administrador de producción se provisiona por entorno: no entregar contraseña fija pública ni imprimir secretos.
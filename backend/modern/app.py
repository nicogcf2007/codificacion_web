"""Application factory. No import of legacy sessions or credential config."""
from contextlib import asynccontextmanager
import os

import math
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import FastAPI, APIRouter, Depends, Request, Response, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .db import database
from .study import StudyRepository as Repository
from api.v1.routes import build_router
from fastapi.responses import JSONResponse, FileResponse
from .schemas import (ProjectCreate, LoginRequest, PasswordChange, UserCreate, User,
                      SessionResponse, UsersResponse, AuditResponse, AdminOverview, OkResponse)
from .auth import AuthService
from .runtime import Runtime
from .engine import provider_for
from fastapi.exceptions import RequestValidationError


def create_app(database_url=None, provider=None, *, admin_email=None, admin_password=None,
               admin_name=None, session_ttl_seconds=28800):
    for name in ('INPUT_USD_PER_MILLION', 'OUTPUT_USD_PER_MILLION', 'BASELINE_RECORD_USD'):
        value = os.getenv(name)
        if value:
            try:
                rate = float(value)
            except ValueError:
                raise ValueError(f'{name} debe ser un número finito y no negativo') from None
            if not math.isfinite(rate) or rate < 0:
                raise ValueError(f'{name} debe ser un número finito y no negativo')
    url = database_url or os.getenv("DATABASE_URL") or "sqlite:///" + (Path(__file__).resolve().parents[1] / "data/modern.sqlite3").as_posix()
    production = os.getenv('CNC_ENV', os.getenv('APP_ENV', 'development')).lower() == 'production'
    cookie_setting = os.getenv('CNC_COOKIE_SECURE', 'true' if production else 'false').lower()
    if cookie_setting not in {'true', 'false'} or production and cookie_setting != 'true':
        raise ValueError('Cookies Secure obligatorias en producción')
    secure_cookies = cookie_setting == 'true'
    origins = [value.strip().rstrip('/') for value in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if value.strip()]
    for origin in origins:
        parsed = urlsplit(origin)
        if (origin == 'null' or '*' in origin or parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or production and parsed.scheme != 'https'):
            raise ValueError('Configuración de origen inválida: use orígenes exactos HTTPS en producción')
    engine = database(url)
    repo = Repository(engine)
    auth = AuthService(engine, session_ttl_seconds)
    auth.bootstrap(admin_email if admin_email is not None else os.getenv('CNC_ADMIN_EMAIL'),
                   admin_password if admin_password is not None else os.getenv('CNC_ADMIN_PASSWORD'),
                   admin_name if admin_name is not None else os.getenv('CNC_ADMIN_NAME'))

    mode = getattr(provider, "mode", None) or os.getenv("CODING_PROVIDER") or "blocked"
    if mode not in {"blocked", "demo", "openai"}:
        raise ValueError("CODING_PROVIDER debe ser blocked, demo u openai")
    runtime = Runtime(repo, provider or provider_for(mode))

    @asynccontextmanager
    async def lifespan(app):
        runtime.recover()
        yield
        await runtime.shutdown()
        engine.dispose()

    app = FastAPI(title="CNC · Codificación cualitativa", version="2.0.0", lifespan=lifespan)
    app.state.repository = repo
    app.state.runtime = runtime
    app.state.auth = auth

    @app.middleware('http')
    async def private_responses(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            # Do not serialize/log SQL/provider exceptions with request data.
            response = JSONResponse(status_code=500, content={'detail': 'Error interno del servidor'})
        response.headers['X-Content-Type-Options'] = 'nosniff'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(KeyError)
    async def missing_resource(request, error):
        return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado"})

    @app.exception_handler(ValueError)
    async def invalid_input(request, error):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        details = [{"loc":item['loc'], "msg":item['msg'], "type":item['type']} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": details})
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type', 'X-CSRF-Token'])

    def check_origin(request: Request):
        origin = request.headers.get('origin')
        same_origin = str(request.base_url).rstrip('/')
        allowed = set(origins)
        if not production or same_origin.startswith('https://'):
            allowed.add(same_origin)
        if not origin or origin == 'null' or origin not in allowed:
            raise HTTPException(403, 'Origen de solicitud no permitido')

    def session(request: Request):
        context = auth.resolve(request.cookies.get('cnc_session'))
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            check_origin(request)
            auth.check_csrf(request, context)
        return context

    def authorize(request: Request):
        context = session(request)
        if context['user']['must_change_password']:
            raise HTTPException(403, 'Cambie la contraseña provisional antes de acceder a los datos')
        request.state.user = context['user']
        return context

    def administrator(context=Depends(authorize)):
        if context['user']['role'] != 'ADMIN':
            raise HTTPException(403, 'Se requiere rol ADMIN')
        return context

    @app.post('/api/v1/auth/login', response_model=SessionResponse)
    def login(data: LoginRequest, request: Request, response: Response):
        check_origin(request)
        token, context = auth.login(data.email, data.password, request.client.host if request.client else 'unknown')
        response.set_cookie('cnc_session', token, httponly=True, secure=secure_cookies, samesite='lax', max_age=auth.session_ttl_seconds)
        response.set_cookie('cnc_csrf', context['csrf_token'], secure=secure_cookies, samesite='lax', max_age=auth.session_ttl_seconds)
        return context

    @app.get('/api/v1/auth/me', response_model=SessionResponse)
    def me(context=Depends(session)):
        return {key: context[key] for key in ('user', 'csrf_token')}

    @app.post('/api/v1/auth/logout', response_model=OkResponse)
    def logout(response: Response, context=Depends(session)):
        auth.logout(context['session_id'])
        response.delete_cookie('cnc_session', httponly=True, secure=secure_cookies, samesite='lax')
        response.delete_cookie('cnc_csrf', secure=secure_cookies, samesite='lax')
        return {'ok': True}

    @app.post('/api/v1/auth/password', response_model=SessionResponse)
    def password(data: PasswordChange, context=Depends(session)):
        return auth.change_password(context, data.current_password, data.password)

    @app.get('/api/v1/admin/users', response_model=UsersResponse)
    def users(context=Depends(administrator)):
        return {'users': auth.list_users()}

    @app.post('/api/v1/admin/users', status_code=201, response_model=User)
    def create_user(data: UserCreate, context=Depends(administrator)):
        return auth.create_user(context['user']['id'], **data.model_dump())

    @app.get('/api/v1/admin/audit', response_model=AuditResponse)
    def audit(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), context=Depends(administrator)):
        return repo.audit_events(limit, offset)

    @app.get('/api/v1/admin/overview', response_model=AdminOverview)
    def overview(context=Depends(administrator)):
        return repo.overview()

    async def health():
        return dict(status="healthy", provider_mode=mode, database=engine.dialect.name, auth_required=True)

    app.get("/health")(health)
    app.get("/api/v1/health")(health)
    router = APIRouter(prefix="/api/v1", dependencies=[Depends(authorize)])

    @router.get("/projects")
    async def projects():
        return {"projects": repo.list_projects()}

    @router.post("/projects", status_code=201)
    async def create_project(data: ProjectCreate, context=Depends(authorize)):
        return repo.create_project(data.name, data.client, context['user']['id'])

    app.include_router(router)
    app.include_router(build_router(repo, authorize, mode, runtime))

    @app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE'], include_in_schema=False)
    def unknown_api(path: str):
        raise HTTPException(404, 'Recurso no encontrado')

    frontend = (Path(__file__).resolve().parents[2] / 'frontend/dist').resolve()
    if (frontend / 'index.html').is_file():
        @app.get('/{path:path}', include_in_schema=False)
        async def spa(path: str):
            if path.startswith(('api/', 'health')):
                raise HTTPException(404, 'Recurso no encontrado')
            target = (frontend / path).resolve()
            try:
                target.relative_to(frontend)
            except ValueError:
                raise HTTPException(404, 'Recurso no encontrado') from None
            if target.is_file() and not any(part.startswith('.') for part in Path(path).parts):
                return FileResponse(target)
            if Path(path).suffix or any(part.startswith('.') for part in Path(path).parts):
                raise HTTPException(404, 'Recurso no encontrado')
            return FileResponse(frontend / 'index.html')
    return app

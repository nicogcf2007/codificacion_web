import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient as RawTestClient

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
ADMIN_EMAIL = 'admin@example.test'
ADMIN_PASSWORD = 'Synthetic-password-2026!'


def login(client, email=ADMIN_EMAIL, password=ADMIN_PASSWORD):
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password},
                           headers={'Origin': str(client.base_url).rstrip('/')})
    assert response.status_code == 200, response.text
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    client.headers['Origin'] = str(client.base_url).rstrip('/')
    return response.json()


class SessionClient(RawTestClient):
    """Test-only convenience that authenticates through the actual login API."""
    def __enter__(self):
        super().__enter__()
        login(self)
        return self


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in ('DATABASE_URL', 'APP_ACCESS_TOKEN', 'OPENAI_API_KEY', 'CODING_PROVIDER',
                 'CNC_ADMIN_EMAIL', 'CNC_ADMIN_PASSWORD', 'CNC_ADMIN_NAME', 'APP_ENV',
                 'CNC_ENV', 'ENVIRONMENT', 'CNC_COOKIE_SECURE', 'CORS_ORIGINS'):
        monkeypatch.delenv(name, raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('External provider/network forbidden in backend tests')
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=forbidden))
    import importlib
    # TestClient here may use httpx2; block both libraries at transport seams.
    for module_name in ('httpx', 'httpx2'):
        try:
            client_module = importlib.import_module(module_name)
        except ImportError:
            continue
        original_send = client_module.Client.send
        original_async_send = client_module.AsyncClient.send
        def local_send(self, request, *args, _send=original_send, **kwargs):
            transport_module = type(self._transport).__module__
            if transport_module != 'starlette.testclient':
                forbidden()
            return _send(self, request, *args, **kwargs)
        async def local_async_send(self, request, *args, _send=original_async_send, **kwargs):
            transport_module = type(self._transport).__module__
            if not transport_module.endswith('asgi'):
                forbidden()
            return await _send(self, request, *args, **kwargs)
        monkeypatch.setattr(client_module.Client, 'send', local_send)
        monkeypatch.setattr(client_module.AsyncClient, 'send', local_async_send)
    import urllib.request
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    import requests
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)


@pytest.fixture
def factory(tmp_path):
    from modern.app import create_app
    def build(**kwargs):
        defaults = dict(admin_email=ADMIN_EMAIL, admin_password=ADMIN_PASSWORD, admin_name='Test Admin')
        defaults.update(kwargs)
        return create_app(database_url=f'sqlite:///{(tmp_path / "test.sqlite3").as_posix()}', **defaults)
    return build

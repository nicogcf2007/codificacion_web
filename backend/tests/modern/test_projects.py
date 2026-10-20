import importlib.util
from fastapi.testclient import TestClient
from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, login


def test_factory_health_auth_projects_persist(tmp_path):
    assert importlib.util.find_spec('modern') is not None, 'Modern backend factory is missing'
    from modern.app import create_app
    url = f'sqlite:///{(tmp_path / "persist.sqlite3").as_posix()}'
    app = create_app(url, admin_email=ADMIN_EMAIL, admin_password=ADMIN_PASSWORD, admin_name='Test Admin')
    with TestClient(app) as client:
        for path in ['/health', '/api/v1/health']:
            assert client.get(path).json() == {'status': 'healthy', 'provider_mode': 'blocked', 'database': 'sqlite', 'auth_required': True}
        assert client.get('/api/v1/projects').status_code == 401
        assert client.get('/api/v1/projects', headers={'Authorization': 'Bearer invalid'}).status_code == 401
        login(client)
        created = client.post('/api/v1/projects', json={'name':'Estudio', 'client':'CNC'})
        assert created.status_code == 201, created.text
        project = created.json()
        assert project['survey_count'] == project['job_count'] == 0
        assert project['created_at'].endswith('Z')
        assert client.get('/api/v1/projects').json()['projects'] == [project]
        assert client.post('/api/v1/projects', json={'name': '', 'client': 'CNC'}).status_code == 422
    with TestClient(create_app(url)) as client:
        login(client)
        assert client.get('/api/v1/projects').json()['projects'][0]['id'] == project['id']
        assert 'core.ai_engine' not in __import__('sys').modules
        assert 'core.config' not in __import__('sys').modules

"""Session contract: isolated storage and synthetic identities only."""
from fastapi.testclient import TestClient
from conftest import login, ADMIN_PASSWORD
from sqlalchemy import select, update
import pytest
from modern import db


def test_admin_creates_standard_accounts_shared_projects_and_provisional_gate(factory):
    app = factory()
    with TestClient(app) as admin:
        login(admin)
        project = admin.post('/api/v1/projects', json={'name': 'Shared'}).json()
        created = admin.post('/api/v1/admin/users', json={
            'email': 'staff@example.test', 'name': 'Test Staff', 'role': 'STANDARD',
            'password': 'Synthetic-staff-2026!', 'must_change_password': True,
        })
        assert created.status_code == 201, created.text
        user = created.json()
        assert user['must_change_password'] and user['active']
        assert 'password' not in user and 'password_hash' not in user and 'argon2' not in created.text
        assert {u['id'] for u in admin.get('/api/v1/admin/users').json()['users']} == {user['id'], admin.get('/api/v1/auth/me').json()['user']['id']}
        with TestClient(app) as staff, TestClient(app) as second_session:
            login(staff, 'staff@example.test', 'Synthetic-staff-2026!')
            login(second_session, 'staff@example.test', 'Synthetic-staff-2026!')
            for path in ['/api/v1/projects', '/api/v1/jobs', f"/api/v1/projects/{project['id']}/surveys", '/api/v1/admin/users']:
                assert staff.get(path).status_code == 403
            assert staff.post('/api/v1/auth/password', json={'current_password': 'wrong', 'password': 'Synthetic-new-staff-2026!'}).status_code == 401
            assert staff.post('/api/v1/auth/password', json={'current_password': 'Synthetic-staff-2026!', 'password': 'short'}).status_code == 422
            changed = staff.post('/api/v1/auth/password', json={'current_password': 'Synthetic-staff-2026!', 'password': 'Synthetic-new-staff-2026!'})
            assert changed.status_code == 200, changed.text
            assert not changed.json()['user']['must_change_password']
            assert staff.get('/api/v1/projects').json()['projects'][0]['id'] == project['id']
            assert second_session.get('/api/v1/auth/me').status_code == 401
            assert staff.post('/api/v1/projects', json={'name': 'Shared Staff'}).status_code == 201
            assert len(admin.get('/api/v1/projects').json()['projects']) == 2
            for path in ['/api/v1/admin/users', '/api/v1/admin/audit', '/api/v1/admin/overview']:
                assert staff.get(path).status_code == 403
            assert staff.post('/api/v1/admin/users', json={
                'email': 'intruder@example.test', 'name': 'Intruder', 'role': 'ADMIN',
                'password': 'Synthetic-intruder-2026!', 'must_change_password': False,
            }).status_code == 403
        duplicate = admin.post('/api/v1/admin/users', json={
            'email': 'STAFF@example.test', 'name': 'Duplicate', 'role': 'STANDARD',
            'password': 'Synthetic-duplicate-2026!', 'must_change_password': False,
        })
        assert duplicate.status_code == 409
        assert admin.post('/api/v1/auth/register', json={}).status_code == 404



def test_mutations_require_session_bound_csrf_and_origin_and_logout_revokes(factory):
    app = factory()
    with TestClient(app) as client:
        payload = login(client)
        assert client.post('/api/v1/projects', json={'name': 'Private'}, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
        client.headers.pop('X-CSRF-Token')
        assert client.post('/api/v1/projects', json={'name': 'Private'}).status_code == 403
        client.headers['X-CSRF-Token'] = payload['csrf_token']
        assert client.post('/api/v1/projects', json={'name': 'Private'}, headers={'Origin': 'https://evil.example'}).status_code == 403
        client.headers.pop('Origin')
        assert client.post('/api/v1/projects', json={'name': 'Private'}).status_code == 403
        client.headers['Origin'] = 'http://testserver'
        assert client.post('/api/v1/projects', json={'name': 'Private'}).status_code == 201
        cookie = client.cookies.get('cnc_session')
        assert client.post('/api/v1/auth/logout', headers={'X-CSRF-Token': 'wrong'}).status_code == 403
        assert client.get('/api/v1/auth/me').status_code == 200
        assert client.post('/api/v1/auth/logout').json() == {'ok': True}
        assert 'cnc_session' not in client.cookies and 'cnc_csrf' not in client.cookies
        client.cookies.set('cnc_session', cookie)
        assert client.get('/api/v1/auth/me').status_code == 401
        assert client.get('/api/v1/projects').status_code == 401
    with TestClient(factory()) as client:
        assert client.post('/api/v1/auth/login', json={'email': 'admin@example.test', 'password': 'Synthetic-password-2026!'},
                           headers={'Origin': 'https://evil.example'}).status_code == 403


def test_login_issues_private_session_and_bootstrap_is_not_an_auth_bypass(tmp_path):
    from modern.app import create_app
    url = f'sqlite:///{(tmp_path / "auth.sqlite3").as_posix()}'
    # Constructor credentials provision a real account, never authorize requests.
    app = create_app(url, admin_email='admin@example.test',
                     admin_password='Synthetic-password-2026!', admin_name='Test Admin')
    with TestClient(app) as client:
        assert client.get('/api/v1/projects').status_code == 401
        assert client.get('/api/v1/projects', headers={'Authorization': 'Bearer ignored'}).status_code == 401
        login = client.post('/api/v1/auth/login', json={
            'email': 'ADMIN@example.test', 'password': 'Synthetic-password-2026!',
        }, headers={'Origin': 'http://testserver'})
        assert login.status_code == 200, login.text
        payload = login.json()
        assert set(payload) == {'user', 'csrf_token'}
        assert set(payload['user']) == {'id', 'email', 'name', 'role', 'active', 'must_change_password', 'created_at'}
        assert payload['user']['role'] == 'ADMIN'
        assert payload['user']['email'] == 'admin@example.test'
        session_cookie = next(item for item in login.headers.get_list('set-cookie') if item.startswith('cnc_session='))
        assert 'HttpOnly' in session_cookie and 'SameSite=lax' in session_cookie
        assert 'HttpOnly' not in next(item for item in login.headers.get_list('set-cookie') if item.startswith('cnc_csrf='))
        assert client.get('/api/v1/auth/me').json() == payload
        assert client.get('/api/v1/projects').json() == {'projects': []}
        assert login.headers['cache-control'] == 'no-store'
        assert app.state.auth.get_user(payload['user']['id']) == payload['user']


def test_production_cookies_are_secure_and_origins_are_exact(factory, monkeypatch):
    monkeypatch.setenv('CNC_ENV', 'production')
    monkeypatch.setenv('CNC_COOKIE_SECURE', 'true')
    monkeypatch.setenv('CORS_ORIGINS', 'https://localhost:5173')
    app = factory()
    with TestClient(app, base_url='https://testserver') as client:
        response = client.post('/api/v1/auth/login', json={'email': 'admin@example.test', 'password': ADMIN_PASSWORD}, headers={'Origin': 'https://testserver'})
        assert response.status_code == 200
        assert all('Secure' in value for value in response.headers.get_list('set-cookie'))
        for origin in ['null', 'https://testserver.evil.test', 'https://testserver:8080', 'http://testserver', 'https://localhost:5173.evil']:
            assert client.post('/api/v1/auth/login', json={'email': 'admin@example.test', 'password': ADMIN_PASSWORD}, headers={'Origin': origin}).status_code == 403
        assert client.post('/api/v1/auth/login', json={'email': 'admin@example.test', 'password': ADMIN_PASSWORD}, headers={'Origin': 'https://localhost:5173'}).status_code == 200
    monkeypatch.setenv('CNC_COOKIE_SECURE', 'false')
    with pytest.raises(ValueError, match='Secure'):
        factory()
    monkeypatch.setenv('CNC_COOKIE_SECURE', 'true')
    monkeypatch.setenv('CORS_ORIGINS', '*')
    with pytest.raises(ValueError, match='origen'):
        factory()


def test_login_failures_are_uniform_and_rate_limit_survives_restart(factory):
    app = factory()
    with TestClient(app) as client:
        active = login(client)['user']
        with app.state.repository.engine.begin() as conn:
            conn.execute(update(db.users).where(db.users.c.id == active['id']).values(active=False))
        bodies = []
        for email, password in [('admin@example.test', ADMIN_PASSWORD), ('unknown@example.test', ADMIN_PASSWORD), ('admin@example.test', 'wrong')]:
            response = client.post('/api/v1/auth/login', json={'email': email, 'password': password}, headers={'Origin': 'http://testserver'})
            assert response.status_code == 401
            assert 'set-cookie' not in response.headers
            bodies.append(response.json())
        assert bodies[0] == bodies[1] == bodies[2]
        statuses = [client.post('/api/v1/auth/login', json={'email': f'unknown{i}@example.test', 'password': 'wrong'}, headers={'Origin': 'http://testserver'}).status_code for i in range(15)]
        assert 429 in statuses
        assert client.get('/api/v1/projects').status_code == 401
    with TestClient(factory()) as client:
        limited = client.post('/api/v1/auth/login', json={'email': 'unknown@example.test', 'password': 'wrong'}, headers={'Origin': 'http://testserver'})
        assert limited.status_code == 429
        assert limited.json() == bodies[0]


def test_audit_attributes_server_identity_async_checkpoints_and_historical_rows(factory):
    from sqlalchemy import insert
    from modern.repository import identity, now
    from test_study import make_study
    from test_execution import FakeProvider, wait_job
    app = factory(provider=FakeProvider())
    with TestClient(app) as client:
        user = login(client)['user']
        # Client-supplied actor fields are forbidden, not used as identity.
        assert client.post('/api/v1/projects', json={'name': 'Forged', 'actor_id': 'someone-else'}).status_code == 422
        project, book, survey, job = make_study(client, 'id,P3\n001,nueva categoría sintética\n002,crédito rápido\n')
        assert client.post(f"/api/v1/jobs/{job['id']}/start").status_code == 200
        assert wait_job(client, job['id'])['status'] == 'COMPLETED'
        records = client.get(f"/api/v1/jobs/{job['id']}/records").json()['records']
        assert client.patch(f"/api/v1/jobs/{job['id']}/records/{records[0]['id']}", json={'codes': ['02']}).status_code == 200
        assert client.post(f"/api/v1/jobs/{job['id']}/review/batch", json={'record_ids': [records[1]['id']], 'code': '03', 'label': 'Sensitive synthetic marker'}).status_code == 200
        with app.state.repository.engine.connect() as conn:
            decisions = list(conn.execute(select(db.audit.c.payload).where(db.audit.c.job_id == job['id'])).scalars())
        assert 'Sensitive synthetic marker' not in repr(decisions)
        assert all(set(payload) <= {'before', 'after'} for payload in decisions)
        historical_id = identity()
        with app.state.repository.engine.begin() as conn:
            conn.execute(insert(db.audit).values(id=historical_id, job_id=job['id'], record_id=None, action='historical_review', payload={'secret': 'Sensitive synthetic marker'}, created_at=now()))
        response = client.get('/api/v1/admin/audit?limit=100')
        assert response.status_code == 200
        report = response.json()
        assert report['total'] == len(report['events'])
        historical = next(event for event in report['events'] if event['id'] == historical_id)
        assert historical['actor_id'] is None and historical['actor_name'] is None and historical['actor_email'] is None
        current = [event for event in report['events'] if event['id'] != historical_id]
        assert {'project_created', 'codebook_created', 'survey_uploaded', 'job_prepared', 'job_started', 'job_checkpoint', 'job_completed', 'human_approved', 'human_category_created'} <= {event['action'] for event in current}
        assert all(event['actor_id'] == user['id'] and event['actor_email'] == user['email'] for event in current)
        assert all(event['job_id'] == job['id'] for event in current if event['action'].startswith('job_'))
        assert 'Sensitive synthetic marker' not in response.text
        assert 'nueva categoría sintética' not in response.text and ADMIN_PASSWORD not in response.text
        assert all('payload' not in event for event in report['events'])
        first = client.get('/api/v1/admin/audit?limit=2').json()
        second = client.get('/api/v1/admin/audit?limit=2&offset=2').json()
        assert first['events'] == report['events'][:2]
        assert second['events'] == report['events'][2:4]
        assert first['total'] == second['total'] == report['total']
        assert client.get('/api/v1/admin/audit?limit=0').status_code == 422
        assert client.get('/api/v1/admin/overview').json() == {'projects': 1, 'jobs': 1, 'users': 1, 'active_jobs': 0, 'completed_jobs': 1}


@pytest.mark.parametrize('invalidate', ['logout', 'expire', 'deactivate'])
def test_sse_rehydrates_identity_between_snapshots(factory, monkeypatch, invalidate):
    from test_study import make_study
    from test_execution import FakeProvider
    app = factory(provider=FakeProvider())
    with TestClient(app) as client:
        context = login(client)
        *_, job = make_study(client, 'id,P3\n001,crédito rápido\n')
        with app.state.repository.engine.begin() as conn:
            conn.execute(update(db.jobs).where(db.jobs.c.id == job['id']).values(status='RUNNING'))
        calls = []
        original = app.state.repository.list_activity
        def activity(job_id):
            calls.append(job_id)
            assert len(calls) == 1, 'SSE must close instead of emitting data after session invalidation'
            rows = original(job_id)
            if invalidate == 'logout':
                app.state.auth.logout(app.state.auth.resolve(client.cookies.get('cnc_session'))['session_id'])
            elif invalidate == 'expire':
                with app.state.repository.engine.begin() as conn:
                    conn.execute(update(db.sessions).values(expires_at=0))
            else:
                with app.state.repository.engine.begin() as conn:
                    conn.execute(update(db.users).where(db.users.c.id == context['user']['id']).values(active=False))
            return rows
        monkeypatch.setattr(app.state.repository, 'list_activity', activity)
        response = client.get(f"/api/v1/jobs/{job['id']}/events")
        assert response.status_code == 200
        assert response.text.count('event: snapshot') == 1
        assert len(calls) == 1


def test_mutation_audit_failure_rolls_back_project_and_billable_start(factory):
    from sqlalchemy import event, func
    from test_execution import FakeProvider
    from test_study import make_study
    provider = FakeProvider()
    app = factory(provider=provider)
    with TestClient(app, raise_server_exceptions=False) as client:
        login(client)
        *_, job = make_study(client, 'id,P3\n001,crédito rápido\n')
        def deny_audit(conn, cursor, statement, parameters, context, many):
            if statement.startswith('INSERT INTO activity_events'):
                raise RuntimeError('Synthetic audit unavailable')
        event.listen(app.state.repository.engine, 'before_cursor_execute', deny_audit)
        try:
            failure = client.post('/api/v1/projects', json={'name': 'Must roll back'})
            assert failure.status_code == 500
            assert failure.headers.get('cache-control') == 'no-store'
            assert 'Synthetic audit unavailable' not in failure.text
            assert client.post(f"/api/v1/jobs/{job['id']}/start").status_code == 500
            assert provider.calls == [] and app.state.runtime.tasks == {}
            assert client.get(f"/api/v1/jobs/{job['id']}").json()['status'] == 'PENDING'
            with app.state.repository.engine.connect() as conn:
                assert conn.scalar(select(func.count()).select_from(db.projects)) == 1
        finally:
            event.remove(app.state.repository.engine, 'before_cursor_execute', deny_audit)


def test_review_audit_actor_failure_rolls_back_decision(factory):
    from sqlalchemy import event, func
    from test_execution import FakeProvider, wait_job
    from test_study import make_study
    app = factory(provider=FakeProvider())
    with TestClient(app, raise_server_exceptions=False) as client:
        login(client)
        *_, job = make_study(client, 'id,P3\n001,nueva categoría\n')
        client.post(f"/api/v1/jobs/{job['id']}/start")
        wait_job(client, job['id'])
        record = client.get(f"/api/v1/jobs/{job['id']}/records").json()['records'][0]
        def deny_actor(conn, cursor, statement, parameters, context, many):
            if statement.startswith('INSERT INTO audit_event_actors'):
                raise RuntimeError('Synthetic actor audit unavailable')
        event.listen(app.state.repository.engine, 'before_cursor_execute', deny_actor)
        try:
            response = client.patch(f"/api/v1/jobs/{job['id']}/records/{record['id']}", json={'codes': ['02']})
            assert response.status_code == 500
            assert client.get(f"/api/v1/jobs/{job['id']}/records").json()['records'][0] == record
            with app.state.repository.engine.connect() as conn:
                assert conn.scalar(select(func.count()).select_from(db.audit)) == 0
        finally:
            event.remove(app.state.repository.engine, 'before_cursor_execute', deny_actor)


def test_bootstrap_is_closed_without_credentials_and_never_resets_existing_users(tmp_path, monkeypatch):
    from modern.app import create_app
    from argon2 import extract_parameters, Type
    url = f'sqlite:///{(tmp_path / 'bootstrap.sqlite3').as_posix()}'
    monkeypatch.setenv('APP_ACCESS_TOKEN', 'synthetic-legacy-must-not-authorize')
    app = create_app(url)
    with TestClient(app) as client:
        assert client.get('/api/v1/projects', headers={'Authorization': 'Bearer synthetic-legacy-must-not-authorize'}).status_code == 401
        assert client.post('/api/v1/auth/login', json={'email': 'admin@example.test', 'password': ADMIN_PASSWORD}, headers={'Origin': 'http://testserver'}).status_code == 401
        assert client.post('/api/v1/admin/users', json={}).status_code == 401
        assert app.state.auth.list_users() == []
    monkeypatch.setenv('CNC_ADMIN_EMAIL', 'admin@example.test')
    monkeypatch.setenv('CNC_ADMIN_PASSWORD', ADMIN_PASSWORD)
    monkeypatch.setenv('CNC_ADMIN_NAME', 'Environment Admin')
    app = create_app(url)
    with TestClient(app) as client:
        user = login(client)['user']
        with app.state.repository.engine.connect() as conn:
            hashed = conn.scalar(select(db.users.c.password_hash).where(db.users.c.id == user['id']))
            stored = conn.execute(select(db.sessions)).mappings().one()
        parameters = extract_parameters(hashed)
        assert parameters.type == Type.ID and parameters.memory_cost >= 65536 and parameters.time_cost >= 3
        assert ADMIN_PASSWORD not in hashed
        assert stored['token_hash'] != client.cookies.get('cnc_session')
        assert stored['csrf_hash'] != client.cookies.get('cnc_csrf')
        cookies = dict(client.cookies)
    monkeypatch.setenv('CNC_ADMIN_PASSWORD', 'Different-synthetic-admin-2026!')
    monkeypatch.setenv('CNC_ADMIN_NAME', 'Must not overwrite')
    restarted = create_app(url)
    with TestClient(restarted) as client:
        client.cookies.update(cookies)
        assert client.get('/api/v1/auth/me').json()['user'] == user
        assert login(client)['user'] == user
        assert len(restarted.state.auth.list_users()) == 1
        with restarted.state.repository.engine.begin() as conn:
            conn.execute(update(db.sessions).values(expires_at=0))
        assert client.get('/api/v1/projects').status_code == 401
        assert client.get('/api/v1/auth/me').status_code == 401
        login(client)
        with restarted.state.repository.engine.begin() as conn:
            conn.execute(update(db.users).where(db.users.c.id == user['id']).values(active=False))
        assert client.get('/api/v1/auth/me').status_code == 401
        assert client.get('/api/v1/projects').status_code == 401


@pytest.mark.parametrize('method,path', [
    ('GET', '/api/v1/projects'), ('POST', '/api/v1/projects'),
    ('GET', '/api/v1/projects/missing/codebooks'), ('POST', '/api/v1/projects/missing/codebooks'),
    ('GET', '/api/v1/projects/missing/surveys'), ('POST', '/api/v1/projects/missing/surveys'),
    ('POST', '/api/v1/coding/jobs'), ('GET', '/api/v1/jobs'), ('GET', '/api/v1/jobs/missing'),
    ('GET', '/api/v1/jobs/missing/records'), ('PATCH', '/api/v1/jobs/missing/records/record'),
    ('POST', '/api/v1/jobs/missing/review/batch'), ('GET', '/api/v1/jobs/missing/analytics'),
    ('GET', '/api/v1/jobs/missing/export'), ('GET', '/api/v1/jobs/missing/events'),
    ('POST', '/api/v1/jobs/missing/start'), ('POST', '/api/v1/jobs/missing/pause'), ('POST', '/api/v1/jobs/missing/resume'),
    ('GET', '/api/v1/admin/users'), ('POST', '/api/v1/admin/users'), ('GET', '/api/v1/admin/audit'), ('GET', '/api/v1/admin/overview'),
])
def test_resource_routes_authenticate_before_validation_or_lookup(factory, method, path):
    with TestClient(factory()) as client:
        assert client.request(method, path, json={}).status_code == 401
        login(client)
        if method != 'GET':
            assert client.request(method, path, json={}, headers={'X-CSRF-Token': 'wrong'}).status_code == 403


def test_csrf_is_bound_to_session_and_non_ascii_failure_is_controlled(factory):
    app = factory()
    with TestClient(app) as first, TestClient(app) as second:
        context = login(first)
        login(second)
        assert second.post('/api/v1/projects', json={'name': 'Must deny'}, headers={'X-CSRF-Token': context['csrf_token']}).status_code == 403
        assert first.post('/api/v1/projects', json={'name': 'Must deny'}, headers={'X-CSRF-Token': b'\xe9'}).status_code == 403


def test_bootstrap_concurrent_first_admin_is_singleton(tmp_path, monkeypatch):
    from modern.app import create_app
    from modern.auth import AuthService, HASHER
    from sqlalchemy import event, func
    from concurrent.futures import ThreadPoolExecutor
    import threading
    app = create_app(f'sqlite:///{(tmp_path / 'first-admin.sqlite3').as_posix()}')
    # Force both callers past the initial read before the write transaction.
    barrier = threading.Barrier(2)
    original_hash = HASHER.hash
    def together(self, password):
        hashed = original_hash(password)
        barrier.wait(timeout=5)
        return hashed
    monkeypatch.setattr(type(HASHER), 'hash', together)
    counters = {}
    inner = threading.Barrier(2)
    def overlapping_counts(conn, cursor, statement, parameters, context, many):
        if statement.startswith('SELECT count(*)') and 'FROM auth_users' in statement:
            thread = threading.get_ident()
            counters[thread] = counters.get(thread, 0) + 1
            if counters[thread] == 2:
                try:
                    inner.wait(timeout=0.3)
                except threading.BrokenBarrierError:
                    pass  # A correct serialized bootstrap may not reach this read concurrently.
    event.listen(app.state.repository.engine, 'after_cursor_execute', overlapping_counts)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(AuthService(app.state.repository.engine).bootstrap,
                f'admin{i}@example.test', f'Synthetic-password-{i}-2026!', f'Admin {i}') for i in range(2)]
            created = [future.result(timeout=15) for future in futures]
        assert sum(user is not None for user in created) == 1
        with app.state.repository.engine.connect() as conn:
            assert conn.scalar(select(func.count()).select_from(db.users)) == 1
    finally:
        event.remove(app.state.repository.engine, 'after_cursor_execute', overlapping_counts)
        app.state.repository.engine.dispose()


def test_worker_continues_after_logout_with_durable_initiator_and_pause_resume_audit(factory):
    import threading
    from test_study import make_study
    from test_execution import FakeProvider, wait_job
    entered, release = threading.Event(), threading.Event()
    class Waiting(FakeProvider):
        def code(self, *args):
            entered.set()
            assert release.wait(5)
            return super().code(*args)
    app = factory(provider=Waiting())
    with TestClient(app) as admin, TestClient(app) as staff:
        login(admin)
        staff_user = admin.post('/api/v1/admin/users', json={'email': 'worker@example.test', 'name': 'Worker', 'password': 'Synthetic-worker-2026!', 'role': 'STANDARD', 'must_change_password': False}).json()
        project, _, _, job = make_study(admin, 'id,P3\n001,crédito rápido\n002,nueva categoría distinta\n')
        login(staff, 'worker@example.test', 'Synthetic-worker-2026!')
        try:
            assert staff.post(f"/api/v1/jobs/{job['id']}/start").status_code == 200
            assert entered.wait(3)
            assert admin.post(f"/api/v1/jobs/{job['id']}/pause").status_code == 200
            assert staff.post('/api/v1/auth/logout').status_code == 200
        finally:
            release.set()
        assert wait_job(admin, job['id'])['status'] == 'PAUSED'
        events = admin.get('/api/v1/admin/audit?limit=100').json()['events']
        worker_events = [e for e in events if e['action'] in {'job_started', 'job_checkpoint', 'job_paused'}]
        assert len(worker_events) == 3 and all(e['actor_id'] == staff_user['id'] for e in worker_events)
        pause = next(e for e in events if e['action'] == 'job_pause_requested')
        assert pause['actor_id'] != staff_user['id']
        assert admin.post(f"/api/v1/jobs/{job['id']}/resume").status_code == 200
        assert wait_job(admin, job['id'])['status'] == 'COMPLETED'
        new_events = admin.get('/api/v1/admin/audit?limit=100').json()['events']
        assert any(e['action'] == 'job_resumed' and e['actor_id'] == pause['actor_id'] for e in new_events)


def test_login_upgrades_hash_without_weakening_argon2_parameters(factory):
    from argon2 import PasswordHasher, extract_parameters
    app = factory()
    user = app.state.auth.list_users()[0]
    old_hash = PasswordHasher(time_cost=2, memory_cost=32768).hash(ADMIN_PASSWORD)
    with app.state.repository.engine.begin() as conn:
        conn.execute(update(db.users).where(db.users.c.id == user['id']).values(password_hash=old_hash))
    with TestClient(app) as client:
        login(client)
    with app.state.repository.engine.connect() as conn:
        upgraded = conn.scalar(select(db.users.c.password_hash).where(db.users.c.id == user['id']))
    assert upgraded != old_hash
    assert extract_parameters(upgraded).time_cost >= 3 and extract_parameters(upgraded).memory_cost >= 65536


def test_openapi_exposes_the_exact_session_user_and_admin_contract(factory):
    app = factory()
    with TestClient(app) as client:
        schema = client.get('/openapi.json').json()
    definitions = schema['components']['schemas']
    assert set(definitions['User']['properties']) == {'id', 'email', 'name', 'role', 'active', 'must_change_password', 'created_at'}
    assert definitions['User']['properties']['role']['enum'] == ['ADMIN', 'STANDARD']
    assert set(definitions['SessionResponse']['properties']) == {'user', 'csrf_token'}
    assert set(definitions['AdminOverview']['properties']) == {'projects', 'jobs', 'users', 'active_jobs', 'completed_jobs'}
    assert schema['paths']['/api/v1/auth/login']['post']['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/SessionResponse')
    assert schema['paths']['/api/v1/admin/users']['post']['responses']['201']['content']['application/json']['schema']['$ref'].endswith('/User')

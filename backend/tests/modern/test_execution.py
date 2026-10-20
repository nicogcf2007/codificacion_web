import time
import threading
import pytest
from conftest import SessionClient as TestClient
from sqlalchemy import select, update
from test_study import make_study
from modern.engine import Inference, ProviderPaused
from modern import db


class FakeProvider:
    mode='demo'
    def __init__(self, fail_at=None):
        self.calls=[]
        self.fail_at=fail_at
    def code(self, question, text, categories, max_labels):
        self.calls.append(text)
        if len(self.calls) == self.fail_at:
            raise ProviderPaused('Saldo insuficiente o cuota excedida')
        return Inference('77' if 'nuev' in text else '01',10,2)


def wait_job(client, id, statuses=('COMPLETED','PAUSED')):
    until=time.monotonic()+8
    while time.monotonic()<until:
        job=client.get(f'/api/v1/jobs/{id}').json()
        if job['status'] in statuses:
            return job
        time.sleep(0.02)
    raise AssertionError(f'Job did not settle: {job}')


def test_checkpoint_resume_never_repeats_completed_prototypes(factory):
    provider=FakeProvider(fail_at=2)
    with TestClient(factory(provider=provider)) as client:
        _,_,_,job=make_study(client,'id,P3\n001,crédito rápido\n002,crédito rápido\n003,categoría completamente nueva\n004,.\n')
        id=job['id']
        assert client.post(f'/api/v1/jobs/{id}/start').status_code == 200
        paused=wait_job(client,id)
        assert paused['status']=='PAUSED'
        assert paused['processed_records']==3
        assert paused['metrics']['api_calls']==2
        assert client.post(f'/api/v1/jobs/{id}/resume').status_code == 200
        completed=wait_job(client,id)
        assert completed['status']=='COMPLETED'
        assert provider.calls.count('crédito rápido')==1
        assert completed['processed_records']==4
        records=client.get(f'/api/v1/jobs/{id}/records').json()['records']
        assert len(records)==4
        assert records[3]['codes']==['99']
        assert len(client.get(f'/api/v1/jobs/{id}/records?review_only=true').json()['records'])==1
        assert client.post(f'/api/v1/jobs/{id}/start').status_code==409


def test_orphan_inflight_requires_explicit_retry(factory):
    provider=FakeProvider()
    app=factory(provider=provider)
    with TestClient(app) as client:
        *_,job=make_study(client)
        id=job['id']
        with app.state.repository.engine.begin() as conn:
            conn.execute(update(db.jobs).where(db.jobs.c.id==id).values(status='RUNNING'))
            conn.execute(update(db.prototypes).where(db.prototypes.c.job_id==id).values(state='IN_FLIGHT'))
    with TestClient(factory(provider=provider)) as client:
        assert client.get(f'/api/v1/jobs/{id}').json()['status']=='PAUSED'
        assert client.post(f'/api/v1/jobs/{id}/resume').status_code==409
        assert provider.calls==[]
        assert client.post(f'/api/v1/jobs/{id}/resume',json={'retry_uncertain':True}).status_code==200
        assert wait_job(client,id)['status']=='COMPLETED'


def test_pause_is_cooperative_and_duplicate_start_is_rejected(factory):
    entered, release=threading.Event(),threading.Event()
    class Slow(FakeProvider):
        def code(self,*args):
            entered.set()
            assert release.wait(5)
            return super().code(*args)
    provider=Slow()
    with TestClient(factory(provider=provider)) as client:
        *_,job=make_study(client,'id,P3\n001,crédito rápido\n002,nueva categoría distinta\n')
        id=job['id']
        assert client.post(f'/api/v1/jobs/{id}/start').status_code==200
        assert entered.wait(3)
        assert client.post(f'/api/v1/jobs/{id}/start').status_code==409
        assert client.post(f'/api/v1/jobs/{id}/pause').status_code==200
        release.set()
        paused=wait_job(client,id)
        assert paused['status']=='PAUSED'
        assert paused['processed_records']==1
        assert client.post(f'/api/v1/jobs/{id}/resume').status_code==200
        assert wait_job(client,id)['status']=='COMPLETED'
        assert len(provider.calls)==2


def test_real_provider_and_key_update_fail_closed(factory):
    class Real(FakeProvider):
        mode='openai'
    provider=Real()
    with TestClient(factory(provider=provider)) as client:
        *_,job=make_study(client)
        assert client.post(f"/api/v1/jobs/{job['id']}/start").status_code==503
        assert client.post('/api/v1/settings/openai-key',json={'api_key':'synthetic-only'}).status_code==404
        assert provider.calls==[]

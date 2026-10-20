import csv
import io
from conftest import SessionClient as TestClient
from openpyxl import load_workbook
from sqlalchemy import select
from test_study import make_study
from test_execution import FakeProvider, wait_job
from modern import db


def test_human_review_analytics_and_safe_original_export(factory):
    app=factory(provider=FakeProvider())
    with TestClient(app) as client:
        *_,job=make_study(client,'id,P3,metadata\n001,nueva categoría rara,=2+2\n002,nueva categoría rara,00123\n003,crédito rápido,normal\n')
        id=job['id']
        assert client.get(f'/api/v1/jobs/{id}/export?format=csv').status_code==409
        client.post(f'/api/v1/jobs/{id}/start')
        assert wait_job(client,id)['status']=='COMPLETED'
        pending=client.get(f'/api/v1/jobs/{id}/records?review_only=true').json()['records']
        assert len(pending)==2
        first=pending[0]['id']
        assert client.patch(f'/api/v1/jobs/{id}/records/{first}',json={'codes':['22'],'review_status':'APPROVED'}).status_code==422
        approved=client.patch(f'/api/v1/jobs/{id}/records/{first}',json={'codes':['02'],'review_status':'APPROVED'})
        assert approved.status_code==200,approved.text
        batch=client.post(f'/api/v1/jobs/{id}/review/batch',json={'record_ids':[pending[1]['id']],'code':'03','label':'Nueva categoría humana'})
        assert batch.status_code==200,batch.text
        assert batch.json()['updated']==1
        analytics=client.get(f'/api/v1/jobs/{id}/analytics')
        assert analytics.status_code==200,analytics.text
        assert analytics.json()['pending_review']==0
        assert sum(row['count'] for row in analytics.json()['distribution'])==3
        assert '03' in [row['code'] for row in analytics.json()['distribution']]
        exported=client.get(f'/api/v1/jobs/{id}/export?format=csv')
        assert exported.status_code==200,exported.text
        rows=list(csv.DictReader(io.StringIO(exported.content.decode('utf-8-sig'))))
        assert rows[0]['id']=='001'
        assert rows[0]['metadata']=="'=2+2"
        assert rows[1]['metadata']=='00123'
        assert rows[0]['CP3_1']=='02'
        assert rows[1]['CP3_1']=='03'
        excel=client.get(f'/api/v1/jobs/{id}/export?format=xlsx')
        workbook=load_workbook(io.BytesIO(excel.content))
        assert workbook.active['D2'].value=='02'
        assert workbook.active['C2'].data_type=='s'
        assert workbook.active['C2'].value=="'=2+2"
        with app.state.repository.engine.connect() as conn:
            assert len(list(conn.execute(select(db.audit).where(db.audit.c.job_id==id))))==2
        # SSE reconnection gets durable final state, not transient process memory.
        events=client.get(f'/api/v1/jobs/{id}/events')
        assert events.status_code==200
        assert 'event: snapshot' in events.text
        assert 'COMPLETED' in events.text

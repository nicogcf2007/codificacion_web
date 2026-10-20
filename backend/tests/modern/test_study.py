from conftest import SessionClient as TestClient


def make_study(client, text='id,P3,P4\n001,crédito rápido,amabilidad\n002,crédito rápido,.\n003,.,otro\n'):
    project = client.post('/api/v1/projects', json={'name': 'Sintético', 'client': 'Prueba'}).json()
    book = client.post(f"/api/v1/projects/{project['id']}/codebooks", json={'name': 'Catálogo', 'categories': [{'code':'01','label':'Créditos'}, {'code':'02','label':'Atención'}], 'max_labels':2})
    assert book.status_code == 201, book.text
    upload = client.post(f"/api/v1/projects/{project['id']}/surveys", files={'file':('synthetic.csv',text.encode(),'text/csv')})
    assert upload.status_code == 201, upload.text
    survey = upload.json()
    job = client.post('/api/v1/coding/jobs', json={'survey_id':survey['id'], 'name':'Prueba', 'questions':[{'column_name':'P3','question_text':'¿Por qué?','codebook_id':book.json()['id']}]})
    assert job.status_code == 201, job.text
    return project, book.json(), survey, job.json()


def test_survey_codebook_job_are_durable_without_provider_calls(factory):
    with TestClient(factory()) as client:
        project, book, survey, job = make_study(client)
        assert survey['total_records'] == 3
        assert survey['preview'][0]['id'] == '001'
        assert job['status'] == 'PENDING'
        assert job['metrics']['api_calls'] == 0
        assert job['metrics']['purity'] is None
        assert client.get(f"/api/v1/jobs/{job['id']}").json() == job
        assert client.get(f"/api/v1/projects/{project['id']}/surveys").json()['surveys'][0]['id'] == survey['id']
        bad = client.post(f"/api/v1/projects/{project['id']}/codebooks", json={'name':'Bad','categories':[{'code':'1','label':'Bad'}],'max_labels':1})
        assert bad.status_code == 422
        bad = client.post('/api/v1/coding/jobs', json={'survey_id':survey['id'],'name':'Bad','questions':[{'column_name':'not-present','question_text':'X','codebook_id':book['id']}]})
        assert bad.status_code == 422
        assert client.get('/api/v1/jobs').json()['jobs'] == [job]
        assert client.get('/api/temp-files').status_code == 404

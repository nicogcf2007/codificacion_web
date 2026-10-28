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


def test_precoded_rows_are_preserved_without_provider_calls(factory):
    text = (
        'id,P3,CP3\\n'
        '001,servicio muy bueno,02\\n'
        '002,otro motivo,\\n'
        '003,.,\\n'
        '004,atencion rapida,1\\n'
        '005,doble motivo,01;02\\n'
    ).encode().decode('unicode_escape')
    with TestClient(factory()) as client:
        project, book, survey, job = make_study(client, text=text)
        assert job['total_records'] == 5
        # 4 records are approved immediately (001 -> 02, 003 -> 99 empty, 004 -> 01, 005 -> 01;02)
        assert job['processed_records'] == 4
        assert job['status'] == 'PENDING'

        # Check records
        records = client.get(f"/api/v1/jobs/{job['id']}/records").json()['records']
        rec_by_resp = {r['response_id']: r for r in records}

        # Response 0: pre-coded '02'
        assert rec_by_resp[0]['codes'] == ['02']
        assert rec_by_resp[0]['review_status'] == 'APPROVED'

        # Response 2: empty text -> '99'
        assert rec_by_resp[2]['codes'] == ['99']
        assert rec_by_resp[2]['review_status'] == 'APPROVED'

        # Response 3: pre-coded '1' -> zfilled to '01'
        assert rec_by_resp[3]['codes'] == ['01']
        assert rec_by_resp[3]['review_status'] == 'APPROVED'

        # Response 4: pre-coded multi '01;02'
        assert rec_by_resp[4]['codes'] == ['01', '02']
        assert rec_by_resp[4]['review_status'] == 'APPROVED'

        # Response 1 is still pending in prototypes, not in records yet
        assert 1 not in rec_by_resp


def test_all_precoded_rows_immediately_completed_and_exportable(factory):
    text = (
        'id,P3,CP3\\n'
        '001,servicio muy bueno,02\\n'
        '002,atencion rapida,01\\n'
    ).encode().decode('unicode_escape')
    with TestClient(factory()) as client:
        project, book, survey, job = make_study(client, text=text)
        assert job['total_records'] == 2
        assert job['processed_records'] == 2
        assert job['status'] == 'COMPLETED'

        # Should export without running runtime
        export_res = client.get(f"/api/v1/jobs/{job['id']}/export?format=csv")
        assert export_res.status_code == 200
        csv_text = export_res.content.decode('utf-8-sig')
        assert '02' in csv_text
        assert '01' in csv_text

"""Transactional import exercised through the authenticated multipart API."""
from conftest import SessionClient
from test_codebook_excel import workbook_bytes, setup_project, preview, import_book


def test_import_shares_by_key_and_max_labels_persists_source_and_server_actor_on_restart(factory):
    app = factory()
    content = workbook_bytes([
        ['CP3_1-CP3_2-CP8_1-CP8_2', '01', 'Crédito', 'Finanzas', 3, 'Pregunta del libro'],
        ['CP3_1-CP3_2-CP8_1-CP8_2', '02', 'Servicio', 'Atención', None, None],
        ['CP27_1NOM-CP27_2NOM', '03', 'No elegido', None, 27, 'No guardar'],
    ])
    with SessionClient(app) as client:
        project, survey = setup_project(client)
        actor = client.get('/api/v1/auth/me').json()['user']['id']
        key = preview(client, project, content).json()['catalogs'][0]['key']
        selections = [{'column_name': column, 'catalog_key': key, 'max_labels': maximum}
                      for column, maximum in [('P3_1', 1), ('P3_2', 1), ('P8_1', 2)]]
        response = import_book(client, project, survey, content, selections, actor_id='untrusted-browser-actor')
        assert response.status_code == 201, response.text
        imported = response.json()
        assert imported['filename'] == 'libro.xlsx'
        assert len(imported['codebooks']) == 2
        first, second = imported['codebooks']
        assert first['id'] != second['id']
        assert first['max_labels'] == 1 and second['max_labels'] == 2
        assert first['source'] == {'filename': 'libro.xlsx', 'sheet': 'Codificación',
            'field_id': 'CP3_1-CP3_2-CP8_1-CP8_2', 'question_number': '3', 'question_text': 'Pregunta del libro',
            'target_columns': ['P3_1', 'P3_2'], 'groupings': {'01': 'Finanzas', '02': 'Atención'}}
        assert second['source']['target_columns'] == ['P8_1']
        assert imported['mappings'] == [{'column_name': column, 'codebook_id': book['id'], 'question_text': 'Pregunta del libro'}
                                       for column, book in [('P3_1', first), ('P3_2', first), ('P8_1', second)]]
        assert client.get('/api/v1/jobs').json()['jobs'] == [] and app.state.runtime.tasks == {}
        events = client.get('/api/v1/admin/audit?limit=100').json()['events']
        imported_events = [e for e in events if e['action'] == 'codebook_imported']
        assert len(imported_events) == 2
        assert all(e['actor_id'] == actor and e['project_id'] == project and e['job_id'] is None for e in imported_events)
        assert {e['resource_id'] for e in imported_events} == {first['id'], second['id']}
        manual = client.post(f'/api/v1/projects/{project}/codebooks', json={'name': 'Manual', 'categories': [{'code': '01', 'label': 'Manual'}]}).json()
        assert manual.get('source') is None
    with SessionClient(factory()) as client:
        saved = client.get(f'/api/v1/projects/{project}/codebooks').json()['codebooks']
        assert {b['id']: b for b in saved if b.get('source')} == {b['id']: b for b in imported['codebooks']}
        assert next(b for b in saved if b['id'] == manual['id']).get('source') is None

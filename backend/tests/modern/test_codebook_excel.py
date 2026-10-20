"""Synthetic catalog workbooks only; no respondent files or provider calls."""
import io
import json

from openpyxl import Workbook
from sqlalchemy import select, func
from conftest import SessionClient
from modern import db

HEADERS = ['Id campo', 'Cod', 'Label', 'Agrupación', '# Pregunta del formulario', 'Nombre de la Pregunta']


def workbook_bytes(rows, *, extra_sheets=None):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Codificación'
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    for name, values in (extra_sheets or {}).items():
        extra = book.create_sheet(name)
        for row in values:
            extra.append(row)
    output = io.BytesIO()
    try:
        book.save(output)
        return output.getvalue()
    finally:
        book.close()
        output.close()


def setup_project(client, columns=('P3_1', 'P3_2', 'P8_1', 'P8_2')):
    project = client.post('/api/v1/projects', json={'name': 'Libro sintético'}).json()
    text = ','.join(columns) + '\n' + ','.join('.' for _ in columns) + '\n'
    response = client.post(f"/api/v1/projects/{project['id']}/surveys", files={'file': ('base.csv', text.encode(), 'text/csv')})
    assert response.status_code == 201, response.text
    return project['id'], response.json()['id']


def preview(client, project, content, filename='libro.xlsx'):
    return client.post(f'/api/v1/projects/{project}/codebooks/preview', files={'file': (filename, content)})


def import_book(client, project, survey, content, selections, filename='libro.xlsx', **extra):
    return client.post(f'/api/v1/projects/{project}/codebooks/import',
                       files={'file': (filename, content)},
                       data={'survey_id': survey, 'selections': json.dumps(selections), **extra})


def test_preview_real_headers_composite_ids_inherited_question_and_no_database_writes(factory):
    app = factory()
    content = workbook_bytes([
        ['CP3_1-CP3_2-CP8_1-CP8_2', '01', 'Crédito', 'Finanzas', 3, '¿Motivo sintético?'],
        ['CP3_1-CP3_2-CP8_1-CP8_2', '02', 'Servicio', 'Atención', None, None],
        ['CP27_1NOM-CP27_2NOM', '03', 'Otro', None, 27, 'Otra pregunta'],
    ], extra_sheets={'Identificación': [['id', 'nombre'], ['synthetic', 'ignore']], 'Notas': [['auxiliar']]})
    with SessionClient(app) as client:
        project, _ = setup_project(client)
        with app.state.repository.engine.connect() as conn:
            before = {table.name: conn.scalar(select(func.count()).select_from(table)) for table in db.metadata.sorted_tables}
        response = preview(client, project, content, 'C:\\fakepath\\libro.xlsx')
        assert response.status_code == 200, response.text
        value = response.json()
        assert value['filename'] == 'libro.xlsx'
        assert value['sheets'] == ['Codificación']
        assert len(value['catalogs']) == 2
        catalog = value['catalogs'][0]
        assert catalog['field_id'] == 'CP3_1-CP3_2-CP8_1-CP8_2'
        assert catalog['candidate_columns'] == ['CP3_1', 'P3_1', 'CP3_2', 'P3_2', 'CP8_1', 'P8_1', 'CP8_2', 'P8_2']
        assert catalog['question_number'] == '3'
        assert catalog['question_text'] == '¿Motivo sintético?'
        assert catalog['categories'] == [{'code': '01', 'label': 'Crédito'}, {'code': '02', 'label': 'Servicio'}]
        assert catalog['compatible'] is True and catalog['issues'] == []
        assert value['catalogs'][1]['candidate_columns'] == ['CP27_1NOM', 'P27_1NOM', 'CP27_2NOM', 'P27_2NOM']
        repeated = preview(client, project, content).json()
        assert [c['key'] for c in repeated['catalogs']] == [c['key'] for c in value['catalogs']]
        assert client.get(f'/api/v1/projects/{project}/codebooks').json()['codebooks'] == []
        with app.state.repository.engine.connect() as conn:
            assert before == {table.name: conn.scalar(select(func.count()).select_from(table)) for table in db.metadata.sorted_tables}
        assert app.state.runtime.tasks == {}

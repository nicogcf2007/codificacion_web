"""Group-local validation: never repair incompatible textual codes."""
import io

from conftest import SessionClient
from openpyxl import load_workbook
from test_codebook_excel import workbook_bytes, setup_project, preview, import_book


def test_preview_marks_only_invalid_groups_and_selected_import_does_not_block_valid_ones(factory):
    rows = [
        ['CP3', 1, 'Válida', 'Grupo', 3, 'Primera'],
        ['CNPS', '1', 'Uno', None, 4, 'NPS'],
        ['CNPS', '2', 'Dos', None, None, None],
        ['CNPS', '3', 'Tres', None, None, None],
        ['CT32T_1', '001', 'Tres dígitos', None, 32, 'T'],
        ['CT32T_4', '101', 'Tres dígitos', None, None, None],
        ['CP_DUP', '01', 'Uno', None, 7, 'Duplicada'],
        ['CP_DUP', '01', 'Otro', None, None, None],
        ['CP_LABEL', '01', '', None, 8, 'Etiqueta'],
        ['CP_FORMULA', '01', '=1+1', None, 9, 'Fórmula'],
        ['CP_ERROR', '01', '#DIV/0!', None, 10, 'Error'],
        ['CP_CONFLICT', '01', 'Uno', None, 11, 'Texto A'],
        ['CP_CONFLICT', '02', 'Dos', None, 11, 'Texto B'],
        ['CP_LONG', '01', 'Larga', None, 12, 'x' * 2001],
        ['CP_EMPTY', '01', 'Sin pregunta', None, None, None],
        ['CP_GENERAL', 1, 'General no inferir cero', None, 13, 'General'],
        ['CP_PAD3', 1, 'Formato 000', None, 14, 'Triple'],
        ['CP_DECIMAL', 1.5, 'Decimal', None, 15, 'Decimal'],
        ['CP_SPACES', ' 01 ', 'Espacios no reparar', None, 16, 'Espacios'],
        ['CP_UNICODE', '０１', 'No ASCII', None, 17, 'Unicode'],
    ]
    book = load_workbook(io.BytesIO(workbook_bytes(rows)))
    try:
        book.active['B2'].number_format = '00'
        book.active['B18'].number_format = '000'
        output = io.BytesIO()
        book.save(output)
        content = output.getvalue()
        output.close()
    finally:
        book.close()
    with SessionClient(factory()) as client:
        project, survey = setup_project(client, ('P3', 'CNPS', 'P_EMPTY'))
        response = preview(client, project, content)
        assert response.status_code == 200, response.text
        catalogs = {c['field_id']: c for c in response.json()['catalogs']}
        assert {c['field_id'] for c in catalogs.values() if c['compatible']} == {'CP3', 'CP_EMPTY'}
        assert catalogs['CP3']['categories'][0]['code'] == '01'
        assert catalogs['CNPS']['categories'] == [{'code': '1', 'label': 'Uno'}, {'code': '2', 'label': 'Dos'}, {'code': '3', 'label': 'Tres'}]
        assert catalogs['CT32T_1']['categories'][0]['code'] == '001'
        assert catalogs['CT32T_4']['categories'][0]['code'] == '101'
        assert catalogs['CP_GENERAL']['categories'][0]['code'] == '1'
        assert catalogs['CP_PAD3']['categories'][0]['code'] == '001'
        assert catalogs['CP_SPACES']['categories'][0]['code'] == ' 01 '
        assert catalogs['CP_LONG']['question_text'] == 'x' * 2001
        assert catalogs['CP_EMPTY']['question_text'] == ''
        for catalog in catalogs.values():
            if not catalog['compatible']:
                assert catalog['issues']
        valid = {'column_name': 'P3', 'catalog_key': catalogs['CP3']['key'], 'max_labels': 1}
        invalid = {'column_name': 'CNPS', 'catalog_key': catalogs['CNPS']['key'], 'max_labels': 1}
        assert import_book(client, project, survey, content, [valid, invalid]).status_code == 422
        assert client.get(f'/api/v1/projects/{project}/codebooks').json()['codebooks'] == []
        response = import_book(client, project, survey, content, [valid])
        assert response.status_code == 201, response.text
        assert response.json()['codebooks'][0]['categories'] == [{'code': '01', 'label': 'Válida'}]
        empty = import_book(client, project, survey, content, [{'column_name': 'P_EMPTY', 'catalog_key': catalogs['CP_EMPTY']['key'], 'max_labels': 1}])
        assert empty.status_code == 201, empty.text
        assert empty.json()['mappings'][0]['question_text'] == ''

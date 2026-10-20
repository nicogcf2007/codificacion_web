"""Pure Excel catalog adapter: no database, providers or formula evaluation."""
from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from pathlib import PurePosixPath

from openpyxl import load_workbook

MAX_BYTES = 50 * 1024 * 1024


def safe_filename(filename):
    return PurePosixPath(filename.replace('\\', '/')).name


def normalized(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).lower().split())


def cell_text(cell, *, code=False):
    value = cell.value
    if value is None:
        return ''
    if isinstance(value, (float, int)) and not isinstance(value, bool) and float(value).is_integer():
        text = str(int(value))
        if code and int(value) >= 0 and re.fullmatch(r'0{2,}', cell.number_format):
            return text.zfill(len(cell.number_format))
        return text
    return str(value)


def catalog_key(sheet, field_id):
    material = json.dumps([sheet, field_id], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(material).hexdigest()


def candidate_columns(field_id):
    candidates = []
    for identifier in field_id.split('-'):
        identifier = identifier.strip()
        if identifier not in candidates:
            candidates.append(identifier)
        counterpart = identifier[1:] if identifier.startswith('CP') else 'C' + identifier if identifier.startswith('P') else None
        if counterpart and counterpart not in candidates:
            candidates.append(counterpart)
    return candidates


def read_codebook(filename, content):
    filename = safe_filename(filename)
    if not content or len(content) > MAX_BYTES:
        raise ValueError('Archivo vacío o superior a 50 MB')
    if PurePosixPath(filename).suffix.lower() != '.xlsx':
        raise ValueError('Solo se aceptan libros .xlsx y .xls')
    result = dict(filename=filename, sheets=[], catalogs=[], warnings=[])
    with io.BytesIO(content) as stream:
        workbook = load_workbook(stream, read_only=True, data_only=False, keep_links=False)
        try:
            for sheet in workbook:
                if normalized(sheet.title) == 'identificacion':
                    continue
                headers = None
                groups = {}
                for row in sheet.iter_rows():
                    if headers is None:
                        names = {normalized(cell.value): index for index, cell in enumerate(row)}
                        if {'id campo', 'cod', 'label'} <= names.keys():
                            headers = names
                            result['sheets'].append(sheet.title)
                        continue
                    def text(name):
                        return cell_text(row[headers[name]], code=name == 'cod') if name in headers and headers[name] < len(row) else ''
                    field_id = text('id campo').strip()
                    if not field_id:
                        continue
                    if field_id not in groups:
                        groups[field_id] = dict(key=catalog_key(sheet.title, field_id), sheet=sheet.title,
                            field_id=field_id, question_number='', question_text='', categories=[],
                            compatible=True, issues=[], candidate_columns=candidate_columns(field_id), groupings={})
                    catalog = groups[field_id]
                    def issue(message):
                        if message not in catalog['issues']:
                            catalog['issues'].append(message)
                        catalog['compatible'] = False
                    for name in ('# pregunta del formulario', 'nombre de la pregunta'):
                        target = 'question_number' if name.startswith('#') else 'question_text'
                        value = text(name)
                        if value:
                            if catalog[target] and catalog[target] != value:
                                issue('Datos de pregunta en conflicto dentro del catálogo')
                            else:
                                catalog[target] = value
                    if len(catalog['question_text']) > 2000:
                        issue('Pregunta superior a 2000 caracteres')
                    for name in headers:
                        if name in {'id campo', 'cod', 'label', 'agrupacion', '# pregunta del formulario', 'nombre de la pregunta'}:
                            cell = row[headers[name]]
                            if cell.data_type == 'f':
                                issue('Fórmula no permitida en el catálogo')
                            elif cell.data_type == 'e':
                                issue('Error Excel en el catálogo')
                    code, label = text('cod'), text('label')
                    if code or label:
                        if not re.fullmatch(r'[0-9]{2}', code):
                            issue('Código incompatible: se requieren exactamente dos dígitos ASCII')
                        if not label.strip():
                            issue('Categoría sin etiqueta')
                        if any(category['code'] == code for category in catalog['categories']):
                            issue('Código duplicado o en conflicto')
                        catalog['categories'].append(dict(code=code, label=label))
                        grouping = text('agrupacion')
                        if grouping:
                            catalog['groupings'][code] = grouping
                result['catalogs'].extend(groups.values())
        finally:
            workbook.close()
    if not result['sheets']:
        raise ValueError('Ninguna hoja contiene encabezados de libro de códigos')
    return result


def public_preview(parsed):
    return {**parsed, 'catalogs': [{key: value for key, value in catalog.items() if key != 'groupings'}
                                 for catalog in parsed['catalogs']]}

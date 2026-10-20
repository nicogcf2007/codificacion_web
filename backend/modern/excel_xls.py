"""Bounded BIFF Excel reader; never writes files or executes workbook content."""
import io
import struct
import xlrd
from xlrd.compdoc import CompDocError

MAX_CELLS = 2_000_000


def cell_value(cell, datemode):
    if cell.ctype in (xlrd.XL_CELL_EMPTY,xlrd.XL_CELL_BLANK):return ''
    if cell.ctype==xlrd.XL_CELL_DATE:return xlrd.xldate_as_datetime(cell.value,datemode).isoformat()
    if cell.ctype==xlrd.XL_CELL_BOOLEAN:return bool(cell.value)
    if cell.ctype==xlrd.XL_CELL_ERROR:return xlrd.biffh.error_text_from_code.get(cell.value,'#ERROR!')
    if cell.ctype==xlrd.XL_CELL_NUMBER and cell.value.is_integer():return int(cell.value)
    return cell.value


def legacy_sheets(content, first_only=True, max_rows=50000, max_columns=500):
    book=None
    try:
        book=xlrd.open_workbook(file_contents=content,on_demand=True,logfile=io.StringIO())
        if not book.nsheets:raise ValueError('Excel sin hojas')
        sheets=[];cells=0
        for index in range(1 if first_only else book.nsheets):
            sheet=book.sheet_by_index(index)
            if sheet.nrows>max_rows+1:raise ValueError('Límite de 50.000 registros por hoja')
            if sheet.ncols>max_columns:raise ValueError('Máximo 500 columnas por hoja')
            cells+=sheet.nrows*sheet.ncols
            if cells>MAX_CELLS:raise ValueError('Excel excede el límite de 2.000.000 celdas')
            rows=[[cell_value(sheet.cell(row,col),book.datemode) for col in range(sheet.ncols)] for row in range(sheet.nrows)]
            sheets.append((sheet.name,rows))
            book.unload_sheet(index)
        return sheets
    except (xlrd.XLRDError,CompDocError,OSError,IndexError,KeyError,TypeError,struct.error,AssertionError,UnicodeError) as exc:
        raise ValueError('Excel .xls inválido o no compatible') from exc
    finally:
        if book is not None:book.release_resources()

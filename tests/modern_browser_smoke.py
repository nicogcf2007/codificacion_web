"""Real-browser integration against an explicitly isolated local demo server.
Run with backend/venv/Scripts/python.exe tests/modern_browser_smoke.py URL OUTPUT.
Never targets a public host, an OpenAI job, or an existing production database.
"""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
from openpyxl import load_workbook


def run(url, output):
    parsed=urlparse(url)
    if parsed.hostname not in {'127.0.0.1','localhost'}:
        raise ValueError('Solo se permite una instancia local de QA')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    errors=[];unexpected=[];checks=[]
    with sync_playwright() as browser_tool:
        browser=browser_tool.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        def guard(route):
            if urlparse(route.request.url).hostname not in {'127.0.0.1','localhost'}:
                unexpected.append(route.request.url);route.abort()
            else:
                route.continue_()
        context.route('**/*',guard)
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        health=context.request.get(url+'/api/v1/health').json()
        assert health['provider_mode']=='demo' and not health['auth_required'],health
        # Do not run against an instance with pre-existing projects.
        assert context.request.get(url+'/api/v1/projects').json()['projects']==[], 'Use a new scratch DB for every browser test'
        page.goto(url,wait_until='networkidle')
        expect(page.get_by_role('heading',name='Espacio de proyectos')).to_be_visible()
        page.get_by_role('button',name='Tema oscuro').click()
        page.get_by_label('Nombre del estudio',exact=True).fill('Experiencia de clientes · QA sintético')
        page.get_by_label('Cliente',exact=True).fill('CNC · Datos sintéticos')
        with page.expect_response(lambda response:response.request.method=='POST' and response.url.endswith('/api/v1/projects')) as create_response:
            page.get_by_role('button',name='Crear proyecto',exact=True).click()
        project=create_response.value.json()
        expect(page.get_by_role('heading',name='Preparar codificación')).to_be_visible()
        responses=['crédito ágil','atención cordial','requisitos excesivos','tasas elevadas','horarios extendidos','plataforma estable','cercanía territorial','información confusa','cobros inesperados','solución de reclamos','diversidad de productos','seguridad digital','beneficios promocionales','transacciones lentas','cajeros disponibles','seguros útiles','asesoría especializada','comunicación frecuente','soporte permanente','nada por ahora','.','crédito ágil']
        csv_buffer=io.StringIO(newline='');writer=csv.writer(csv_buffer);writer.writerow(['id','P3','=1+1'])
        for index,text in enumerate(responses,start=1):writer.writerow([f'{index:04d}',text,'=2+2' if index==1 else '00123'])
        with page.expect_response(lambda response:response.request.method=='POST' and response.url.endswith('/surveys')) as uploaded:
            page.get_by_label('Subir base de respuestas').set_input_files({'name':'synthetic.csv','mimeType':'text/csv','buffer':csv_buffer.getvalue().encode('utf-8')})
        assert uploaded.value.status==201,uploaded.value.text()
        expect(page.get_by_text(f'{len(responses)} registros · 3 columnas',exact=True)).to_be_visible()
        page.get_by_label('Nombre del catálogo',exact=True).fill('Catálogo sintético QA')
        page.get_by_label('Máximo de códigos').fill('2')
        page.get_by_label('Etiqueta 1',exact=True).fill('Crédito')
        page.get_by_role('button',name='Categoría',exact=True).click()
        page.get_by_label('Código 2',exact=True).fill('02');page.get_by_label('Etiqueta 2',exact=True).fill('Atención')
        with page.expect_response(lambda response:response.request.method=='POST' and response.url.endswith('/codebooks')) as book_response:
            page.get_by_role('button',name='Guardar catálogo',exact=True).click()
        assert book_response.value.status==201,book_response.value.text()
        page.locator('.column-option').filter(has_text='P3').locator('input').check()
        page.get_by_label('Pregunta P3',exact=True).fill('¿Qué mejorarías de tu entidad financiera?')
        page.screenshot(path=str(output/'01-configuracion-oscura.png'),full_page=True)
        with page.expect_response(lambda response:response.request.method=='POST' and response.url.endswith('/coding/jobs')) as job_response:
            page.get_by_role('button',name='Preparar ejecución',exact=True).click()
        assert job_response.value.status==201,job_response.value.text()
        job=job_response.value.json();job_id=job['id'];assert job['metrics']['api_calls']==0 and job['status']=='PENDING'
        expect(page.get_by_role('button',name='Iniciar codificación',exact=True)).to_be_enabled()
        page.get_by_role('button',name='Iniciar codificación',exact=True).click()
        expect(page.get_by_role('button',name='Pausar',exact=True)).to_be_visible()
        page.get_by_role('button',name='Pausar',exact=True).click()
        expect(page.get_by_role('dialog')).to_be_visible(timeout=12000)
        paused=context.request.get(url+f'/api/v1/jobs/{job_id}').json();assert paused['status']=='PAUSED'
        assert paused['processed_records']>0
        page.get_by_role('dialog').get_by_role('button',name='Reanudar codificación',exact=True).click()
        expect(page.get_by_text('Completado',exact=True)).to_be_visible(timeout=20000)
        expect(page.get_by_role('progressbar')).to_have_attribute('aria-valuenow','100')
        assert float(page.locator('.monitor-grid aside').evaluate("element => parseFloat(getComputedStyle(element).paddingLeft)"))>=18
        expect(page.get_by_text('Plan preparado. Todavía no se ha llamado al proveedor.',exact=True)).not_to_be_visible()
        completed=context.request.get(url+f'/api/v1/jobs/{job_id}').json()
        assert completed['processed_records']==len(responses) and completed['metrics']['cost_usd']==0
        assert completed['metrics']['api_calls']==len(responses)-completed['metrics']['saved_calls']
        page.screenshot(path=str(output/'02-monitor-oscuro.png'),full_page=True)
        checks.extend(['project creation','CSV upload','catalogue creation','question assignment','persisted plan without provider calls','cooperative pause and resume','SSE completion and progress'])
        sidebar=page.locator('.app-sidebar')
        sidebar.get_by_role('button',name='Revisión humana',exact=True).click()
        expect(page.locator('blockquote')).to_be_visible()
        pending=context.request.get(url+f'/api/v1/jobs/{job_id}/records?review_only=true').json()['records']
        first=pending[0]['id']
        with page.expect_response(lambda response:response.request.method=='PATCH' and response.url.endswith('/'+first)) as approved:
            page.keyboard.press('2');page.keyboard.press('Enter')
        assert approved.value.status==200 and approved.value.json()['codes']==['02']
        expect(page.locator('.review-row')).to_have_count(len(pending)-1)
        queue=context.request.get(url+f'/api/v1/jobs/{job_id}/records?review_only=true').json()['records']
        selected_ids=[queue[0]['id'],queue[1]['id']]
        page.locator('.review-row input').nth(0).check();page.locator('.review-row input').nth(1).check()
        page.get_by_role('button',name='Nueva categoría en lote',exact=False).click()
        dialog=page.get_by_role('dialog');dialog.get_by_label('Nuevo código',exact=True).fill('03');dialog.get_by_label('Etiqueta de la categoría',exact=True).fill('Motivo emergente QA')
        with page.expect_response(lambda response:response.request.method=='POST' and response.url.endswith('/review/batch')) as batch_response:
            dialog.get_by_role('button',name='Aplicar a 2 registros',exact=True).click()
        assert batch_response.value.status==200 and batch_response.value.json()['updated']==2
        expect(page.get_by_role('dialog')).not_to_be_visible()
        stored=context.request.get(url+f'/api/v1/jobs/{job_id}/records').json()['records']
        assert len(stored)==len(responses)
        assert all(record['codes']==['03'] for record in stored if record['id'] in selected_ids)
        assert next(record for record in stored if record['id']==first)['review_status']=='APPROVED'
        page.screenshot(path=str(output/'03-revision-oscura.png'),full_page=True)
        checks.extend(['numeric/Enter keyboard review','audited batch new category','record decisions read back'])
        sidebar.get_by_role('button',name='Resultados',exact=True).click()
        expect(page.locator('.bar-row').first).to_be_visible()
        page.locator('.bar-row').first.click();expect(page.locator('.chart-detail')).to_be_visible()
        for format in ('csv','xlsx'):
            with page.expect_download() as download_info:
                page.get_by_role('button',name='CSV' if format=='csv' else 'Excel',exact=True).click()
            download=download_info.value;destination=output/download.suggested_filename;download.save_as(str(destination))
            if format=='csv':
                with destination.open(encoding='utf-8-sig',newline='') as stream: rows=list(csv.DictReader(stream))
                assert len(rows)==len(responses) and rows[0]['id']=='0001'
                assert rows[0]["'=1+1"]=="'=2+2" and rows[1]["'=1+1"]=='00123'
                assert 'CP3_1' in rows[0] and 'CP3_2' in rows[0]
            else:
                workbook=load_workbook(destination,data_only=False)
                assert workbook.active['A2'].value=='0001'
                assert not any(cell.data_type=='f' for row in workbook.active for cell in row)
                assert workbook.active['D1'].value=='CP3_1';workbook.close()
        page.screenshot(path=str(output/'04-resultados-oscuros.png'),full_page=True)
        checks.extend(['interactive question-scoped chart','CSV and Excel browser downloads','all original rows, leading zeroes, CNC columns and formula safety'])
        page.get_by_role('button',name='Proyectos',exact=True).last.click()
        expect(page.locator('.project-name strong').filter(has_text=project['name'])).to_be_visible()
        page.screenshot(path=str(output/'05-proyectos-oscuros.png'),full_page=True)
        page.get_by_role('button',name='Tema claro').click();page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
        assert page.locator('.settings-nav span').evaluate("element => getComputedStyle(element).display")=='none'
        expect(page.get_by_role('button',name='Conexión y ajustes',exact=True)).to_be_visible()
        page.screenshot(path=str(output/'06-movil-claro.png'),full_page=True)
        page.reload(wait_until='networkidle')
        expect(page.locator('.project-name strong').filter(has_text=project['name'])).to_be_visible()
        assert page.evaluate("localStorage.getItem('cnc-theme')")=='light'
        assert page.evaluate('Object.keys(localStorage)')==['cnc-theme']
        page.set_viewport_size({'width':1440,'height':1000});page.get_by_role('button',name='Tema oscuro').click()
        page.locator('.app-sidebar').get_by_role('button',name='Ejecuciones',exact=True).click()
        expect(page.get_by_role('button',name='Abrir',exact=True)).to_be_visible()
        page.get_by_role('button',name='Abrir',exact=True).click()
        expect(page.get_by_text('Completado',exact=True)).to_be_visible()
        checks.extend(['dark/light theme persistence only','390px responsive layout without horizontal overflow','completed job restored after browser reload'])
        assert errors==[],errors
        assert unexpected==[],unexpected
        result={'passed':True,'provider':'explicit demo (no OpenAI)','project_id':project['id'],'job_id':job_id,'records':len(responses),'checks':checks,'page_errors':errors,'unexpected_network':unexpected,'screenshots':[str(path) for path in sorted(output.glob('*.png'))]}
        (output/'browser-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2));browser.close()


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: modern_browser_smoke.py http://127.0.0.1:8765 scratch-output')
    run(sys.argv[1].rstrip('/'),sys.argv[2])

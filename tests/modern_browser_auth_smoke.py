"""Browser authorization regression; local blocked provider and synthetic token only."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

TOKEN='synthetic-ui-auth-only'


def run(url,output):
    if urlparse(url).hostname not in {'127.0.0.1','localhost'}:
        raise ValueError('Solo una instancia local aislada')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as tool:
        browser=tool.chromium.launch(headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        health=context.request.get(url+'/api/v1/health').json()
        assert health['provider_mode']=='blocked' and health['auth_required']
        assert context.request.get(url+'/api/v1/projects').status==401
        errors=[];external=[]
        def guard(route):
            if urlparse(route.request.url).hostname not in {'127.0.0.1','localhost'}:
                external.append(route.request.url);route.abort()
            else:route.continue_()
        context.route('**/*',guard)
        page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(url,wait_until='networkidle')
        expect(page.get_by_role('alert')).to_contain_text('Token de acceso inválido o ausente')
        page.get_by_role('button',name='Conexión y ajustes',exact=True).click()
        page.get_by_label('Token de acceso',exact=True).fill(TOKEN)
        with page.expect_response(lambda response:response.url.endswith('/api/v1/projects') and response.status==200):
            page.get_by_role('button',name='Conectar y actualizar',exact=True).click()
        expect(page.get_by_role('alert')).not_to_be_visible()
        expect(page.get_by_label('Token de acceso',exact=True)).to_have_value('')
        page.locator('.app-sidebar').get_by_role('button',name='Proyectos',exact=True).click()
        page.get_by_label('Nombre del estudio',exact=True).fill('Autorización · QA sintético')
        with page.expect_response(lambda response:response.request.method=='POST' and response.url.endswith('/api/v1/projects')) as created:
            page.get_by_role('button',name='Crear proyecto',exact=True).click()
        assert created.value.status==201
        assert created.value.request.headers.get('authorization')=='Bearer '+TOKEN
        project=created.value.json()
        assert context.request.get(url+f"/api/v1/projects/{project['id']}/surveys",headers={'Authorization':'Bearer '+TOKEN}).status==200
        page.reload(wait_until='networkidle')
        expect(page.get_by_role('alert')).to_contain_text('Token de acceso inválido o ausente')
        assert page.evaluate('Object.keys(localStorage)')==['cnc-theme']
        assert errors==[] and external==[]
        result={'passed':True,'provider':'blocked','checks':['private resources require authorization','settings form authorizes actual API requests','project POST carries Bearer header','resource read-back with authorization','token cleared from form','token not persisted after reload','theme is only localStorage key'],'project_id':project['id'],'page_errors':errors,'unexpected_network':external}
        (output/'browser-auth-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False,indent=2));browser.close()


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: modern_browser_auth_smoke.py URL SCRATCH_OUTPUT')
    run(sys.argv[1].rstrip('/'),sys.argv[2])

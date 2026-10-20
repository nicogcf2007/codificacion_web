from conftest import SessionClient as TestClient
from test_study import make_study
from test_execution import FakeProvider, wait_job


def test_same_code_across_questions_keeps_its_own_label(factory):
    with TestClient(factory(provider=FakeProvider())) as client:
        project, book, survey, _=make_study(client,'id,P3,P4\n001,crédito rápido,personal amable\n')
        book2=client.post(f"/api/v1/projects/{project['id']}/codebooks",json={'name':'Trato','categories':[{'code':'01','label':'Amabilidad'}],'max_labels':1}).json()
        job=client.post('/api/v1/coding/jobs',json={'survey_id':survey['id'],'name':'Dos preguntas','questions':[{'column_name':'P3','question_text':'Crédito','codebook_id':book['id']},{'column_name':'P4','question_text':'Atención','codebook_id':book2['id']}]}).json()
        client.post(f"/api/v1/jobs/{job['id']}/start")
        assert wait_job(client,job['id'])['status']=='COMPLETED'
        data=client.get(f"/api/v1/jobs/{job['id']}/analytics").json()
        actual={(item['column_name'],item['code'],item['label']):item['count'] for item in data['distribution']}
        assert actual=={('P3','01','Créditos'):1,('P4','01','Amabilidad'):1}

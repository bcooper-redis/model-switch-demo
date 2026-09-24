from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import create_app
from app.core import Application
from test_application import MemoryStore, Answer, Retrieval, Managed


def client():
    service=Application(MemoryStore(), Answer(), Retrieval(), Managed())
    return TestClient(create_app(service)),service


def test_rejects_foreign_origin_and_headerless_mutation():
    c,_=client()
    assert c.post('/api/conversations',json={}).status_code==403
    assert c.post('/api/conversations',json={},headers={
        'X-Demo-Request':'1','Origin':'https://unrelated.example'}).status_code==403
    assert c.get('/api/state',headers={'Host':'unrelated.example'}).status_code==400


def test_api_turn_retry_and_reset_scope():
    c,service=client();headers={'X-Demo-Request':'1'}
    cid=c.post('/api/conversations',headers=headers,json={}).json()['id']
    body={'request_id':str(uuid4()),'text':'My name is Test Person.'}
    for _ in range(2):
        assert c.post(f'/api/conversations/{cid}/turns',headers=headers,json=body).status_code==200
    state=c.get('/api/state').json()
    assert len(state['conversations'][0]['messages'])==2
    assert len(state['jobs'])==1
    reset={'generation':state['generation'],'confirmation':'wrong'}
    assert c.post('/api/reset',headers=headers,json=reset).status_code==422
    assert c.get('/api/state').json()['conversations']
    reset['confirmation']='RESET'
    assert c.post('/api/reset',headers=headers,json=reset).status_code==200
    assert not c.get('/api/state').json()['conversations']


def test_storage_failure_does_not_call_provider_or_expose_exception(monkeypatch):
    c,service=client();headers={'X-Demo-Request':'1'}
    cid=c.post('/api/conversations',headers=headers,json={}).json()['id']
    def fail(_):raise RuntimeError('secret-bearing diagnostics must not reach browser')
    monkeypatch.setattr(service.store,'save',fail)
    response=c.post(f'/api/conversations/{cid}/turns',headers=headers,
                    json={'request_id':str(uuid4()),'text':'Hello'})
    assert response.status_code==503 and 'secret-bearing' not in response.text
    assert not service.provider.calls

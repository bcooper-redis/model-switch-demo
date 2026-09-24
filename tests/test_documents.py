import copy
import pytest
from app.documents import preview, approve
from app.core import Problem
from app.memory_lifecycle import sync_one, change
from test_milestone4 import app

TEXT='''TEST PROFILE
Compiled 2026-09-23
ABOUT THIS FILE
Historical account; some details are uncertain.
PROFESSIONAL INTERESTS
- You prefer practical examples.
- You may explore a new role; this is not confirmed.
HEALTH HISTORY
Self-reported history, not current status.
- A private excluded passage.
'''

def save(app, passage='6', text='You prefer practical examples.'):
    p=preview('profile.txt',TEXT)
    passage=p['sections'][0]['passages'][0]['id'] if passage=='6' else passage
    return approve(app,'profile.txt',TEXT,p['content_hash'],app.store.state['generation'],
                   [dict(passage_id=passage,text=text,category='about_me')])

def test_preview_pure_preserves_qualifiers_and_lines():
    p=preview('profile.txt',TEXT)
    assert p['sections'][0]['recommended']
    assert not p['sections'][1]['recommended']
    assert 'not confirmed' in p['sections'][0]['passages'][1]['text']
    assert 'Historical account' in str(p['sections'][0]['notes'])
    assert p['sections'][0]['passages'][0]['line']==6
    assert preview('renamed.txt',TEXT.replace('\n','\r\n'))['content_hash']==p['content_hash']

def test_approve_atomic_excludes_unselected_and_syncs_managed(app):
    result=save(app)
    assert result['queued']==1
    s=app.store.state
    assert len(s['memory_ops'])==len(s['memories'])==1
    assert 'private excluded' not in str(s)
    assert not s['conversations'] and not s['jobs']
    assert not app.managed.memories
    sync_one(app,app.store.load())
    record=next(iter(app.store.state['memories'].values()))
    assert record['sync_status']=='synced' and record['source_kind']=='document'
    assert app.managed.memories[0].text==record['text']
    assert not app.provider.calls
    assert app.export()['documents'][0]['content_hash']==preview('profile.txt',TEXT)['content_hash']

def test_reimport_does_not_duplicate_overwrite_edit_or_resurrect(app):
    save(app);sync_one(app,app.store.load());mid=next(iter(app.store.state['memories']))
    assert save(app)['skipped']==1
    change(app,mid,1,'I now prefer diagrams.');sync_one(app,app.store.load())
    assert save(app)['skipped']==1
    assert app.store.state['memories'][mid]['text']=='I now prefer diagrams.'
    change(app,mid,2,delete=True);sync_one(app,app.store.load())
    assert save(app)['skipped']==1
    assert app.store.state['memories'][mid]['status']=='deleted'

def test_invalid_or_stale_batch_never_partially_writes(app):
    p=preview('profile.txt',TEXT);original=copy.deepcopy(app.store.state)
    for content_hash,generation,items in [
        ('changed',original['generation'],[dict(passage_id='6',text='x',category='about_me')]),
        (p['content_hash'],'old',[dict(passage_id='6',text='x',category='about_me')]),
        (p['content_hash'],original['generation'],[dict(passage_id='6',text='x',category='about_me'),dict(passage_id='999',text='x',category='about_me')])]:
        with pytest.raises(Problem):approve(app,'profile.txt',TEXT,content_hash,generation,items)
        assert app.store.state==original

def test_reset_includes_document_sessions(app):
    r=save(app)
    app.reset(app.store.state['generation'])
    assert r['document_id'] in app.store.state['retired'][-1]['sessions']
    assert not app.store.state.get('documents') and not app.store.state.get('memory_ops')

def test_unsupported_inputs_rejected():
    for filename,text in [('x.pdf',TEXT),('x.txt','No bullet points'),('x.txt','\x00'),('x.txt','a'*200001)]:
        with pytest.raises(Problem):preview(filename,text)

def test_api_preview_does_not_touch_store(app,monkeypatch):
    from fastapi.testclient import TestClient
    from app.api import create_app
    def forbidden(*args,**kwargs):raise AssertionError('preview accessed storage')
    monkeypatch.setattr(app.store,'load',forbidden);monkeypatch.setattr(app.store,'save',forbidden)
    c=TestClient(create_app(app));r=c.post('/api/documents/preview',headers={'X-Demo-Request':'1'},json={'filename':'profile.txt','text':TEXT})
    assert r.status_code==200 and r.json()['sections']

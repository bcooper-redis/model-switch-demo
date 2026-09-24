import copy
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import pytest

from app.core import Application, Problem, uid
from app.memory_review import review
from app.memory_lifecycle import change
from app.worker import step
from test_application import MemoryStore, Answer, Retrieval, Managed, Missing, new_turn

class Managed4(Managed):
    def search_long_term_memory(self, request):
        owner=request['filter']['owner_id']['eq']; session=request['filter']['session_id']['eq']
        return NS(items=[m for m in self.memories if m.owner_id==owner and m.session_id==session], next_page_token=None)
    def get_long_term_memory(self, memory_id):
        item=next((m for m in self.memories if m.id==memory_id),None)
        if item is None: raise Missing()
        return item
    def bulk_create_long_term_memories(self, memories):
        for m in memories:
            self.memories=[x for x in self.memories if x.id!=m['id']]
            self.memories.append(NS(**m, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc), attributes=None))

@pytest.fixture
def app(): return Application(MemoryStore(),Answer(),Retrieval(),Managed4())

def candidate(app):
    cid,_=new_turn(app,'I enjoy kayaking.');step(app)
    app.managed.bulk_create_long_term_memories([dict(id='family-fact',text="User enjoys kayaking.",owner_id=app.store.state['owner_id'],session_id=cid,memory_type='semantic')])
    job=next(iter(app.store.state['jobs'].values()));app.retry_job(job['id']);step(app)
    return copy.deepcopy(app.store.state['candidates']['family-fact'])

def accept(app,c):
    return review(app,c['id'],c['version'],c['sources'][0]['message_id'],'family',[],True)

def test_broad_fact_quarantined_then_explicitly_confirmed(app):
    c=candidate(app)
    assert not app.store.state['memories']
    assert all(s['text']!='A test response.' for s in c['sources'])
    with pytest.raises(Problem):review(app,c['id'],c['version'],'invalid','family',[],True)
    accept(app,c);accept(app,c)
    record=app.store.state['memories'][c['id']]
    assert record['category']=='family' and record['people']==[]
    assert record['attribution_method']=='user_confirmed'
    assert len(app.store.state['memories'])==1

def test_dismissal_and_stale_confirmation(app):
    c=candidate(app)
    with pytest.raises(Problem):review(app,c['id'],'stale',c['sources'][0]['message_id'],'family',[],True)
    review(app,c['id'],c['version'],'','family',[],False)
    job=next(iter(app.store.state['jobs'].values()));app.retry_job(job['id']);step(app)
    assert app.store.state['candidates'][c['id']]['status']=='dismissed'
    assert not app.store.state['memories']

def test_name_does_not_supersede_family(app):
    c=candidate(app);accept(app,c)
    cid,_=new_turn(app,'My name is Test Person.');step(app)
    app.managed.bulk_create_long_term_memories([dict(id='name-fact',text="User's name is Test Person.",owner_id=app.store.state['owner_id'],session_id=cid,memory_type='semantic')])
    job=list(app.store.state['jobs'].values())[-1];app.retry_job(job['id']);step(app)
    assert len([m for m in app.store.state['memories'].values() if m['status']=='active'])==2

def test_private_never_touches_store_retrieval_or_managed(app,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('private persistence accessed')
    for name in ('load','save','lock'):monkeypatch.setattr(app.store,name,forbidden)
    monkeypatch.setattr(app.retrieval,'search',forbidden)
    monkeypatch.setattr(app.managed,'add_session_event',forbidden)
    result=app.private_answer([dict(role='USER',text='Private fictional fact')],'openai','test-model')
    assert result['text']=='A test response.' and app.provider.calls[-1][1]==[]
    assert not app.store.writes

def test_private_rejects_bad_or_oversized_history(app):
    for history in ([dict(role='ASSISTANT',text='bad')],[dict(role='USER',text='x'*16001)]):
        with pytest.raises(Problem):app.private_answer(history,'openai','test-model')
    assert not app.provider.calls

def test_edit_durable_retry_stale_revision_and_no_old_history(app,monkeypatch):
    c=candidate(app);accept(app,c)
    cid=c['conversation_id'];old_ids=app.store.state['memories'][c['id']]['managed_ids'][:]
    change(app,c['id'],1,'User prefers hiking now.')
    assert app.store.state['memories'][c['id']]['text']=='User prefers hiking now.'
    assert app.store.state['memories'][c['id']]['revision']==2
    with pytest.raises(Problem):change(app,c['id'],1,'stale')
    original=app.managed.bulk_delete_long_term_memories
    def fail(**kwargs):raise TimeoutError()
    monkeypatch.setattr(app.managed,'bulk_delete_long_term_memories',fail)
    step(app);assert app.store.state['memory_ops']
    monkeypatch.setattr(app.managed,'bulk_delete_long_term_memories',original)
    app.store.state['memory_ops'][c['id']]['next_poll']=0
    restarted=Application(app.store,app.provider,app.retrieval,app.managed)
    step(restarted);assert not app.store.state['memory_ops']
    assert not any(m.id in old_ids for m in app.managed.memories)
    app.send(cid,uid(),'What do I enjoy?')
    assert len(app.provider.calls[-1][0])==1
    assert list(app.store.state['jobs'].values())[-1]['session_id']!=cid

def test_delete_suppresses_late_promotions_and_preserves_other_facts(app):
    c=candidate(app);accept(app,c)
    old_session=c['conversation_id']
    change(app,c['id'],1,delete=True)
    assert app.snapshot()['memories']==[]
    step(app);step(app)
    assert not app.managed.memories and old_session not in app.managed.events
    app.managed.bulk_create_long_term_memories([dict(id='late-paraphrase',text='User likes kayaking.',owner_id=app.store.state['owner_id'],session_id=old_session,memory_type='semantic')])
    app.store.state['retired'][0]['next_poll']=0;step(app)
    assert not app.managed.memories
    assert app.store.state['memories'][c['id']]['text']==''
    assert all(j.get('disabled') for j in app.store.state['jobs'].values())

def test_export_excludes_secrets_and_private_calls(app):
    new_turn(app)
    before=app.export()
    app.private_answer([dict(role='USER',text='private sentinel')],'openai','test-model')
    after=app.export()
    assert before['conversations']==after['conversations']
    assert 'private sentinel' not in str(after) and 'OPENAI_MODEL' not in str(after)

def test_cache_only_fixed_prompts_and_exact_attributes(app):
    from app.cache_example import run, PROMPTS
    app.store.c.update(LANGCACHE_BASE_URL='https://example.invalid',LANGCACHE_CACHE_ID='test',LANGCACHE_API_KEY='fake')
    calls=[];stored=[];hits=[]
    class Cache:
        def __init__(self,**kwargs):assert kwargs['ttl']==3600
        def check(self,**kwargs):calls.append(kwargs);return hits
        def store(self,**kwargs):stored.append(kwargs)
    first=run(app,'openai','test-model',cache_factory=Cache,enabled=True)
    assert first['status']=='miss' and stored[0]['prompt'] in PROMPTS
    assert stored[0]['metadata']==calls[0]['attributes']
    hits.append(dict(response='Paris.',metadata=stored[0]['metadata']))
    second=run(app,'openai','test-model',variant=1,cache_factory=Cache,enabled=True)
    assert second['status']=='hit' and len(app.provider.calls)==1
    hits[0]['metadata']={**hits[0]['metadata'],'model':'different-model'}
    assert run(app,'openai','test-model',cache_factory=Cache,enabled=True)['status']=='miss'
    with pytest.raises(Problem):run(app,'openai','test-model',variant=99,cache_factory=Cache,enabled=True)
    assert not app.store.writes

def test_stale_projection_never_supplies_fact(app,monkeypatch):
    import app.core as core
    c=candidate(app);accept(app,c)
    state=app.store.load();memory=state['memories'][c['id']]
    retrieval=core.Retrieval.__new__(core.Retrieval);retrieval.store=app.store
    app.store.r=object()
    monkeypatch.setattr(core,'EmbeddingsCache',lambda **kwargs:None)
    retrieval.vectorizer=NS(embed=lambda text:[0.0],cache=None)
    hits=[dict(id='prefix:'+memory['id'],text=memory['text'],revision=1)]
    retrieval.index=NS(query=lambda _:hits)
    assert retrieval.search(state,'question')==[memory]
    memory['revision']=2
    assert retrieval.search(state,'question')==[]
    hits[0]['revision']=2;hits[0]['text']='stale text'
    assert retrieval.search(state,'question')==[]


def test_cache_disabled_skips_reads_and_writes_without_credentials(app):
    from app.cache_example import run
    def forbidden(**kwargs): raise AssertionError('Cache must not be constructed')
    result=run(app,'openai','test-model',cache_factory=forbidden,enabled=False)
    assert result['status']=='bypassed' and result['cache_ms']==0
    assert len(app.provider.calls)==1 and not app.store.writes

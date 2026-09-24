import copy
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace as NS

import pytest

from app.core import Application, OpenAIProvider, Problem, Store, uid
from app.worker import deliver, step


class MemoryStore:
    empty = Store.empty
    def __init__(self):
        self.c = {'OPENAI_MODEL': 'test-model', 'EMBEDDING_MODEL': 'test-embeddings'}
        self.prefix = 'isolated-test:app'
        self.state = self.empty()
        self.mutex = threading.Lock()
        self.writes = []
    @contextmanager
    def lock(self):
        with self.mutex:
            yield
    def load(self):
        return copy.deepcopy(self.state)
    def save(self, state):
        self.state = copy.deepcopy(state)
        self.writes.append(copy.deepcopy(state))


class Answer:
    def __init__(self): self.calls = []; self.fail = False
    def answer(self, history, memories):
        self.calls.append(copy.deepcopy((history, memories)))
        if self.fail: raise TimeoutError('simulated provider outage')
        return 'A test response.'


class Retrieval:
    def __init__(self): self.fail = False; self.records = {}; self.results = []
    def search(self, state, text):
        if self.fail: raise TimeoutError('simulated recall outage')
        return self.results
    def put(self, state, record): self.records[record['id']] = copy.deepcopy(record)


class Missing(Exception): status_code = 404


class Managed:
    def __init__(self): self.events = {}; self.lose_ack = False; self.memories = []
    def get_session_memory(self, *, session_id, **_):
        if session_id not in self.events: raise Missing()
        events = self.events[session_id]
        return NS(events=events, owner_id=events[0].actor_id)
    def add_session_event(self, **kwargs):
        event = NS(event_id=uid(), actor_id=kwargs['actor_id'], role=kwargs['role'],
                   metadata=kwargs['metadata'], content=[NS(text=kwargs['content'][0]['text'])])
        self.events.setdefault(kwargs['session_id'], []).append(event)
        if self.lose_ack:
            self.lose_ack = False
            raise TimeoutError('accepted, response lost')
        return NS(event=event)
    def search_long_term_memory(self, **_): return NS(items=self.memories, next_page_token=None)
    def delete_session_memory(self, *, session_id): self.events.pop(session_id, None)
    def bulk_delete_long_term_memories(self, *, memory_ids):
        self.memories = [m for m in self.memories if m.id not in memory_ids]


@pytest.fixture
def app():
    return Application(MemoryStore(), Answer(), Retrieval(), Managed())


def new_turn(app, text='My name is Test Person.'):
    cid=app.new_conversation()['id']; rid=uid()
    app.send(cid,rid,text)
    return cid,rid


def test_saved_user_precedes_generation_and_answer_outbox_are_atomic(app):
    cid,_=new_turn(app)
    saved = [s for s in app.store.writes if s['conversations'].get(cid,{}).get('messages')]
    assert saved[0]['conversations'][cid]['messages'][0]['status']=='generating'
    assert not saved[0]['jobs']
    for s in saved:
        if any(m['role']=='ASSISTANT' for m in s['conversations'][cid]['messages']):
            assert len(s['jobs'])==1


def test_duplicate_submission_returns_existing_answer(app):
    cid,rid=new_turn(app)
    app.send(cid,rid,'My name is Test Person.')
    assert len(app.provider.calls)==1
    assert len(app.store.state['conversations'][cid]['messages'])==2
    assert len(app.store.state['jobs'])==1
    with pytest.raises(Problem): app.send(cid,rid,'different payload')


def test_generation_failure_preserves_user_and_retries_cleanly(app):
    app.provider.fail=True; cid=app.new_conversation()['id']; rid=uid()
    with pytest.raises(Problem): app.send(cid,rid,'Hello')
    assert app.store.state['conversations'][cid]['messages'][0]['status']=='generation_failed'
    assert not app.store.state['jobs']
    app.provider.fail=False;app.send(cid,rid,'Hello')
    assert len(app.store.state['conversations'][cid]['messages'])==2


def test_recall_failure_requires_explicit_bypass(app):
    app.retrieval.fail=True;cid=app.new_conversation()['id'];rid=uid()
    with pytest.raises(Problem): app.send(cid,rid,"What's my name?")
    assert not app.provider.calls
    app.send(cid,rid,"What's my name?",without_recall=True)
    assert app.store.state['conversations'][cid]['messages'][-1]['recall_bypassed']


def test_fresh_conversation_never_replays_previous_transcript(app):
    new_turn(app)
    cid=app.new_conversation()['id']
    app.send(cid,uid(),"What's my name?")
    history,_=app.provider.calls[-1]
    assert len(history)==1 and history[0]['text']=="What's my name?"
    assert 'Test Person' not in str(history)


def test_lost_service_ack_is_reconciled_without_duplicate(app):
    cid,_=new_turn(app);app.managed.lose_ack=True
    step(app)
    job=next(iter(app.store.state['jobs'].values()))
    assert job['delivery']=='uncertain'
    assert len(app.managed.events[cid])==1
    app.retry_job(job['id']);step(app)
    assert len(app.managed.events[cid])==2
    assert app.store.state['jobs'][job['id']]['delivery']=='confirmed'
    app.retry_job(job['id']);step(app)
    assert len(app.managed.events[cid])==2


def test_uncertain_absent_event_is_not_blindly_replayed(app):
    cid,_=new_turn(app)
    job=next(iter(app.store.state['jobs'].values()))
    job['attempted'][job['message_ids'][0]]='prior uncertain attempt'
    step(app)
    assert not app.managed.events
    assert app.store.state['jobs'][job['id']]['delivery']=='uncertain'


def test_zero_extraction_results_remain_pending(app):
    new_turn(app,'Hello.');step(app)
    job=next(iter(app.store.state['jobs'].values()))
    assert job['delivery']=='confirmed' and job['extraction']=='pending'
    assert job['saved_memory_ids']==[]


def test_reset_invalidates_jobs_and_preserves_owner(app):
    cid,_=new_turn(app);before=app.snapshot()
    app.reset(before['generation']);step(app)
    after=app.snapshot()
    assert after['owner_id']==before['owner_id']
    assert after['generation']!=before['generation']
    assert after['conversations']==[] and after['jobs']==[] and after['memories']==[]
    assert not app.managed.events
    assert app.store.state['retired'][0]['sessions']==[cid]
    with pytest.raises(Problem): app.send(cid,uid(),'old request')
    with pytest.raises(Problem): app.reset(before['generation'])


def test_memory_reconciliation_requires_user_evidence_and_is_idempotent(app):
    cid,_=new_turn(app);step(app)
    t=datetime.now(timezone.utc)
    app.managed.memories=[NS(id='managed-name',text="User's name is Test Person.",
        owner_id=app.store.state['owner_id'],session_id=cid,created_at=t,updated_at=t,
        memory_type='semantic',attributes=None)]
    job=next(iter(app.store.state['jobs'].values()))
    for _ in range(2):app.retry_job(job['id']);step(app)
    assert len(app.store.state['memories'])==1
    record=next(iter(app.store.state['memories'].values()))
    assert record['source_message_id']==job['id']
    assert app.store.state['jobs'][job['id']]['saved_memory_ids']==['managed-name']


def test_openai_request_excludes_source_transcript_and_provider_chains():
    calls=[]
    def create(**kwargs):
        calls.append(kwargs)
        return NS(status='completed',output_text='Your name is Test Person.')
    provider=OpenAIProvider.__new__(OpenAIProvider)
    provider.model='test-model';provider.client=NS(responses=NS(create=create))
    provider.answer([{'role':'USER','text':"What's my name?"}],
        [dict(id='memory-1',text="User's name is Test Person.",revision=1,
              source_message_id='source-1',source_text='My name is Test Person.')])
    request=calls[0]
    assert request['store'] is False and 'previous_response_id' not in request
    assert request['input']==[{'role':'user','content':"What's my name?"}]
    assert 'My name is Test Person.' not in request['instructions']
    assert "User's name is Test Person." in request['instructions']


def test_generation_restart_resumes_saved_turn(app):
    cid=app.new_conversation()['id'];rid=uid()
    app.provider.fail=True
    with pytest.raises(Problem): app.send(cid,rid,'Hello')
    app.store.state['conversations'][cid]['messages'][0]['status']='generating'
    restarted=Application(app.store, Answer(), app.retrieval, app.managed)
    restarted.send(cid,rid,'Hello')
    assert len(app.store.state['conversations'][cid]['messages'])==2
    assert len(app.store.state['jobs'])==1


def test_switching_routes_and_preserves_context_without_transcript(app, monkeypatch):
    import app.core as core
    app.provider = None
    app.store.c.update(OPENAI_API_KEY='test', ANTHROPIC_API_KEY='test', ANTHROPIC_MODEL='claude-test')
    calls = []
    class Adapter:
        def __init__(self, config):
            self.config=config
            self.client=NS(close=lambda:None)
        def answer(self, history, memories):
            calls.append((self.config, copy.deepcopy(history), copy.deepcopy(memories)))
            return 'Test Person'
    monkeypatch.setattr(core, 'OpenAIProvider', Adapter)
    monkeypatch.setattr(core, 'AnthropicProvider', Adapter)
    original = copy.deepcopy(app.store.state)
    memory={'id':'existing','text':"User's name is Test Person.",'revision':1,'source_message_id':'source'}
    app.retrieval.results=[memory]
    for provider, model in [('openai','test-model'),('anthropic','claude-test'),('openai','gpt-4.1-mini')]:
        cid=app.new_conversation()['id']
        result=app.send(cid,uid(),"What's my name?",provider=provider,model=model)
        answer=result['messages'][-1]
        assert (answer['provider'],answer['model'])==(provider,model)
        assert len(calls[-1][1])==1 and calls[-1][2]==[memory]
        assert calls[-1][0][provider.upper()+'_MODEL']==model
    assert app.store.state['owner_id']==original['owner_id']
    assert app.store.state['generation']==original['generation']
    assert app.store.state['memories']==original['memories']


def test_retry_is_pinned_to_saved_provider_model(app):
    cid=app.new_conversation()['id']; rid=uid()
    app.store.c['ANTHROPIC_MODEL']='claude-test'
    app.provider.fail=True
    with pytest.raises(Problem):
        app.send(cid,rid,'Hello',provider='anthropic',model='claude-test')
    with pytest.raises(Problem, match='original provider'):
        app.send(cid,rid,'Hello',provider='openai',model='test-model')
    app.provider.fail=False
    result=app.send(cid,rid,'Hello')
    assert result['messages'][-1]['provider']=='anthropic'
    assert result['messages'][-1]['model']=='claude-test'
    assert len(result['messages'])==2


def test_unconfigured_provider_and_unlisted_model_rejected_before_write(app):
    cid=app.new_conversation()['id'];app.provider=None
    before=copy.deepcopy(app.store.state)
    for provider,model in [('anthropic','claude-test'),('unknown','model'),('openai','unlisted')]:
        with pytest.raises(Problem, match='not configured'):
            app.send(cid,uid(),'Hello',provider=provider,model=model)
        assert app.store.state==before


def test_anthropic_payload_and_truncation(monkeypatch):
    import httpx
    from app.core import AnthropicProvider
    adapter=AnthropicProvider({'ANTHROPIC_API_KEY':'fake','ANTHROPIC_MODEL':'claude-test',
                              'ANTHROPIC_WORKSPACE_ID':'workspace-test'})
    assert adapter.client.headers['anthropic-workspace-id']=='workspace-test'
    adapter.client.close()
    captured=[]
    stop=['end_turn']
    def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200,json={'stop_reason':stop[0],'content':[{'type':'text','text':'Test Person'}]})
    adapter.client=httpx.Client(base_url='https://api.anthropic.com',transport=httpx.MockTransport(handler))
    memory={'id':'m','text':"User's name is Test Person.",'revision':1,'source_message_id':'s',
            'source_text':'Original transcript must not be sent'}
    assert adapter.answer([{'role':'USER','text':"What's my name?"}],[memory])=='Test Person'
    assert captured[0]['model']=='claude-test'
    assert 'Original transcript' not in captured[0]['system']
    assert captured[0]['messages']==[{'role':'user','content':"What's my name?"}]
    stop[0]='max_tokens'
    with pytest.raises(Problem): adapter.answer([{'role':'USER','text':'Hello'}],[])
    adapter.client.close()


def test_anthropic_failure_never_falls_back_to_openai(app, monkeypatch):
    import app.core as core
    app.provider=None
    app.store.c.update(OPENAI_API_KEY='test', ANTHROPIC_API_KEY='test', ANTHROPIC_MODEL='claude-test')
    called=[]
    class Failed:
        def __init__(self, config): self.client=NS(close=lambda:None)
        def answer(self, history, memories):
            called.append('anthropic')
            raise TimeoutError('private upstream error')
    def forbidden(config):
        called.append('openai')
        raise AssertionError('No fallback allowed')
    monkeypatch.setattr(core,'AnthropicProvider',Failed)
    monkeypatch.setattr(core,'OpenAIProvider',forbidden)
    cid=app.new_conversation()['id']
    with pytest.raises(Problem) as error:
        app.send(cid,uid(),'Hello',provider='anthropic',model='claude-test')
    assert called==['anthropic']
    assert 'private upstream error' not in error.value.message
    messages=app.store.state['conversations'][cid]['messages']
    assert len(messages)==1 and messages[0]['status']=='generation_failed'
    assert messages[0]['provider']=='anthropic'
    assert not app.store.state['jobs']


def test_local_outage_persists_selection_and_recovers_without_fallback(app, monkeypatch):
    import app.core as core
    app.provider=None
    app.store.c.update(LOCAL_MODEL='qwen3:4b')
    offline=[True];calls=[]
    class Local:
        def __init__(self,config):
            self.client=NS(close=lambda:None)
            self.evidence={'execution':'local'}
        def answer(self,history,memories):
            calls.append('local')
            if offline[0]: raise ConnectionError('offline')
            return 'Hello'
    def forbidden(config):
        calls.append('cloud')
        raise AssertionError('No cloud fallback')
    monkeypatch.setattr(core,'LocalProvider',Local)
    monkeypatch.setattr(core,'OpenAIProvider',forbidden)
    monkeypatch.setattr(core,'AnthropicProvider',forbidden)
    cid=app.new_conversation()['id'];rid=uid()
    with pytest.raises(Problem,match='Local generation failed'):
        app.send(cid,rid,'Hello',provider='local',model='qwen3:4b')
    user=app.store.state['conversations'][cid]['messages'][0]
    assert user['provider']=='local' and user['status']=='generation_failed'
    with pytest.raises(Problem,match='original provider'):
        app.send(cid,rid,'Hello',provider='openai',model='test-model')
    offline[0]=False
    result=app.send(cid,rid,'Hello')
    assert calls==['local','local'] and len(result['messages'])==2
    assert result['messages'][-1]['local_execution']=={'execution':'local'}

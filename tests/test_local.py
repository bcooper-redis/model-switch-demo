import json
import httpx
import pytest

from app.core import LocalProvider, Problem, local_url, local_status, provider_options


@pytest.mark.parametrize('url', ['https://api.ollama.com', 'http://localhost:11434',
                                'http://127.0.0.1.evil.test', 'http://user:pass@127.0.0.1',
                                'http://127.0.0.1/remote', 'http://127.0.0.1?proxy=1'])
def test_local_requires_literal_loopback(url):
    with pytest.raises(Problem): local_url({'LOCAL_BASE_URL':url})


def adapter_with_transport(handler):
    adapter=LocalProvider({'LOCAL_MODEL':'qwen3:4b'})
    adapter.client.close()
    adapter.client=httpx.Client(base_url='http://127.0.0.1:11434',transport=httpx.MockTransport(handler))
    return adapter


def test_local_generation_uses_shared_memory_and_records_loaded_model():
    captured=[]
    def handler(request):
        captured.append(request)
        if request.url.path=='/api/show':
            return httpx.Response(200,json={'details':{'format':'gguf'}})
        if request.url.path=='/api/ps':
            return httpx.Response(200,json={'models':[{'name':'qwen3:4b','size':1000,'size_vram':1000,'digest':'hash'}]})
        return httpx.Response(200,json={'model':'qwen3:4b','done':True,'done_reason':'stop',
                             'message':{'content':'Your name is Test Person.'},'eval_count':6})
    adapter=adapter_with_transport(handler)
    memory={'id':'m','text':"User's name is Test Person.",'revision':1,'source_message_id':'s',
            'source_text':'Do not replay source transcript'}
    assert 'Test Person' in adapter.answer([{'role':'USER','text':"What's my name?"}],[memory])
    payload=json.loads(captured[1].content)
    assert len(payload['messages'])==2
    assert 'Do not replay' not in payload['messages'][0]['content']
    assert payload['stream'] is False and payload['think'] is False
    assert adapter.evidence['execution']=='local' and adapter.evidence['digest']=='hash'
    assert all(r.url.host=='127.0.0.1' for r in captured)
    adapter.client.close()


@pytest.mark.parametrize('failure',['cloud','truncated','not_loaded','wrong_model'])
def test_unverified_local_answers_are_rejected(failure):
    def handler(request):
        if request.url.path=='/api/show':
            return httpx.Response(200,json={'details':{'format':'gguf'},'remote_host':'ollama.com' if failure=='cloud' else ''})
        if request.url.path=='/api/ps':
            return httpx.Response(200,json={'models':[]})
        return httpx.Response(200,json={'model':'other' if failure=='wrong_model' else 'qwen3:4b',
            'done':True,'done_reason':'length' if failure=='truncated' else 'stop','message':{'content':'Answer'}})
    adapter=adapter_with_transport(handler)
    with pytest.raises(Problem): adapter.answer([{'role':'USER','text':'Hello'}],[])
    assert adapter.evidence is None
    adapter.client.close()


def test_local_catalog_does_not_require_api_key_and_health_failure_is_safe(monkeypatch):
    option=next(p for p in provider_options({'LOCAL_MODEL':'qwen3:4b','LOCAL_MODELS':'qwen3:1.7b'}) if p['id']=='local')
    assert option['available'] and option['models']==['qwen3:4b','qwen3:1.7b']
    def unavailable(*args,**kwargs): raise httpx.ConnectError('internal endpoint details')
    monkeypatch.setattr(httpx.Client,'get',unavailable)
    assert local_status({})=={'reachable':False,'installed_models':[],'status':'Local runtime unavailable'}


def test_qwen_reasoning_is_not_returned_as_the_answer():
    def handler(request):
        if request.url.path=='/api/show': return httpx.Response(200,json={'details':{'format':'gguf'}})
        if request.url.path=='/api/ps':
            return httpx.Response(200,json={'models':[{'name':'qwen3:4b','size':1000,'digest':'hash'}]})
        return httpx.Response(200,json={'model':'qwen3:4b','done':True,'done_reason':'stop',
                                       'message':{'content':'Internal reasoning</think>\nFinal answer.'}})
    adapter=adapter_with_transport(handler)
    assert adapter.answer([{'role':'USER','text':'Hello'}],[])=='Final answer.'
    adapter.client.close()

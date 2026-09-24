"""Live local-generation acceptance. Requires the existing Brian name proof."""
import json
import os
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import LocalProvider
from scripts.milestone0 import settings


def main():
    c=settings()
    local=LocalProvider(c)
    try:
        baseline=local.answer([{'role':'USER','text':"What's my name?"}],[])
        assert 'Brian' not in baseline
        baseline_execution=local.evidence
    finally:
        local.client.close()
    print(json.dumps({'local_without_memory':baseline}),flush=True)
    with httpx.Client(base_url=f"http://127.0.0.1:{os.environ.get('DEMO_PORT','8765')}",
                      headers={'X-Demo-Request':'1'},timeout=150,trust_env=False) as client:
        def post(path,body):
            response=client.post(path,json=body);response.raise_for_status();return response.json()
        before=client.get('/api/state').json()
        assert before['memories'], 'Save Brian as a memory first.'
        runs=[];ids=None
        for provider in ['openai','anthropic','local','openai']:
            cid=post('/api/conversations',{})['id']
            body=dict(request_id=str(uuid.uuid4()),text="What's my name?",provider=provider,model=c[provider.upper()+'_MODEL'])
            conversation=post(f'/api/conversations/{cid}/turns',body)
            answer=conversation['messages'][-1]
            actual=[m['id'] for m in answer['memories']]
            assert actual and (ids is None or ids==actual)
            ids=actual
            assert 'Brian' in answer['text'] and len(answer['history_message_ids'])==1
            assert answer['provider']==provider and answer['model']==body['model']
            if provider=='local':
                assert answer['local_execution']['execution']=='local'
                assert answer['local_execution']['digest']==baseline_execution['digest']
            assert post(f'/api/conversations/{cid}/turns',body)==conversation
            runs.append(dict(provider=provider,model=answer['model'],answer=answer['text'],memory_ids=actual,
                             history_messages=1,local_execution=answer.get('local_execution'),retry_deduplicated=True))
            print(json.dumps(runs[-1]),flush=True)
        after=client.get('/api/state').json()
        assert before['owner_id']==after['owner_id'] and before['generation']==after['generation']
        assert before['memories']==after['memories']
        report=dict(passed=True,baseline=baseline,baseline_execution=baseline_execution,runs=runs,
                    owner_unchanged=True,memories_unchanged=True,generation_unchanged=True)
        (Path(__file__).resolve().parents[1]/'.artifacts/milestone3.json').write_text(json.dumps(report,indent=2))
        print('Milestone 3 live acceptance passed.')


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('Acceptance failed: '+type(exc).__name__)
        sys.exit(1)

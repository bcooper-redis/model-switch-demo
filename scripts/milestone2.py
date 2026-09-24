"""Live provider-switch acceptance against the running demo; preserves existing memories."""
import json
import os
import sys
import uuid
from pathlib import Path

import httpx


def main():
    base = f"http://127.0.0.1:{os.environ.get('DEMO_PORT', '8765')}"
    with httpx.Client(base_url=base, headers={'X-Demo-Request': '1'}, timeout=90) as client:
        def post(path, data):
            response = client.post(path, json=data)
            response.raise_for_status()
            return response.json()
        before = client.get('/api/state').json()
        if not before['memories']:
            raise RuntimeError('Save a name memory through the demo before running acceptance.')
        options = {p['id']:p for p in before['providers']}
        sequence = [('openai', options['openai']['default_model']),
                    ('anthropic', options['anthropic']['default_model']),
                    ('openai', options['openai']['default_model'])]
        # Also exercise each provider's other configured UI model choices.
        sequence += [(p['id'], m) for p in before['providers'] for m in p['models']
                     if m != p['default_model']]
        runs = []
        expected_ids = None
        for provider, model in sequence:
            cid = post('/api/conversations', {})['id']
            request = dict(request_id=str(uuid.uuid4()), text="What's my name?", provider=provider, model=model)
            conversation = post(f'/api/conversations/{cid}/turns', request)
            answer = conversation['messages'][-1]
            ids = [m['id'] for m in answer['memories']]
            assert ids and (expected_ids is None or ids == expected_ids)
            expected_ids = ids
            assert len(answer['history_message_ids']) == 1
            assert answer['provider'] == provider and answer['model'] == model
            assert 'Brian' in answer['text'], 'Run this acceptance with the Brian name proof.'
            retry = post(f'/api/conversations/{cid}/turns', request)
            assert retry == conversation
            runs.append(dict(provider=provider, model=model, answer=answer['text'],
                             memory_ids=ids, history_messages=1, retry_deduplicated=True))
            print(json.dumps(runs[-1]), flush=True)
        after = client.get('/api/state').json()
        assert after['owner_id'] == before['owner_id']
        assert after['generation'] == before['generation']
        assert after['memories'] == before['memories']
        report = dict(passed=True, owner_unchanged=True, generation_unchanged=True,
                      memories_unchanged=True, runs=runs)
        path = Path(__file__).resolve().parents[1] / '.artifacts/milestone2.json'
        path.write_text(json.dumps(report, indent=2))
        print('Milestone 2 live acceptance passed.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Do not print SDK/HTTP payloads or secrets.
        print('Acceptance failed: ' + type(exc).__name__)
        sys.exit(1)

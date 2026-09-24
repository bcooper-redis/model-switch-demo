"""Isolated fictional fixture proof, not a claim of automatic extraction accuracy."""
import json
import os
from pathlib import Path

from app.core import Application, Store, uid, now
from app.memory_lifecycle import change, sync_one
from app.worker import cleanup
from scripts.milestone0 import settings


def main():
    namespace='m4-proof-'+uid()[:12]
    os.environ['DEMO_TEST_NAMESPACE']=namespace
    app=Application(Store(settings()))
    source_id, memory_id, cid=uid(),uid(),uid()
    s=app.store.load()
    fact="The test user enjoys kayaking."
    source=dict(id=source_id,request_id=uid(),role='USER',text=fact,status='complete',created_at=now())
    s['conversations'][cid]=dict(id=cid,title='Fictional M4 fixture',created_at=now(),messages=[source])
    memory=dict(id=memory_id,text=fact,status='active',revision=1,category='interests',people=[],
        managed_ids=[memory_id],source_message_id=source_id,source_event_id=None,
        source_text=fact,source_created_at=source['created_at'],conversation_id=cid,
        attribution_method='user_confirmed',saved_at=now())
    s['memories'][memory_id]=memory
    app.store.save(s)  # Record cleanup scope before crossing the remote write boundary.
    results=[]
    try:
        app.managed.bulk_create_long_term_memories(memories=[dict(id=memory_id,text=fact,
            owner_id=s['owner_id'],session_id=cid,memory_type='semantic')])
        app.retrieval.put(s,memory);app.store.save(s)
        for phase,expected in [('original','kayaking'),('corrected','hiking')]:
            if phase=='corrected':
                change(app,memory_id,1,"The test user prefers hiking now.")
                state=app.store.load();sync_one(app,state)
                assert not app.store.load().get('memory_ops'), 'Correction has not synced'
                app=Application(app.store)  # Fresh application instance after correction.
            for provider in ('openai','anthropic','local'):
                conversation=app.new_conversation()
                answer=app.send(conversation['id'],uid(),'What activity do I enjoy?',
                    provider=provider,model=app.store.c[provider.upper()+'_MODEL'])['messages'][-1]
                assert len(answer['history_message_ids'])==1
                assert len(answer['memories'])==1
                assert expected in answer['text'].lower(), f'{provider} did not recall the {phase} fact'
                results.append(dict(phase=phase,provider=provider,revision=answer['memories'][0]['revision'],
                                    recall_ms=answer['recall_ms'],generation_ms=answer['generation_ms']))
                print(json.dumps(results[-1]),flush=True)
        exported=app.export()
        path=Path('.artifacts/milestone4-fixture-export.json')
        path.write_text(json.dumps(exported,indent=2))
        assert json.loads(path.read_text())==exported
        change(app,memory_id,2,delete=True)
        state=app.store.load();sync_one(app,state)
        assert not app.store.load().get('memory_ops'), 'Deletion has not synced'
        assert not app.retrieval.search(app.store.load(),'preferred activity')
        print(json.dumps({'deletion_verified':True,'export_roundtrip_verified':True}),flush=True)
        Path('.artifacts/milestone4-proof.json').write_text(json.dumps(results,indent=2))
    finally:
        # No session events are delivered by this fixture harness, so no promotion work
        # is submitted. Cleanup is restricted to this newly generated owner/namespace.
        state=app.store.load();app.reset(state['generation']);state=app.store.load()
        for retired in state['retired']:
            cleanup(app,state,retired)
        app.retrieval.index.delete(drop=True)
        app.store.r.delete(app.store.key)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'failed':type(exc).__name__}),flush=True)
        raise SystemExit(1)

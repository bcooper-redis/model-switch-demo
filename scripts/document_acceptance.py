"""Explicit generic import proof in a disposable namespace; no personal profile read."""
import os
from app.core import Application, Store, uid
from app.documents import preview, approve
from app.memory_lifecycle import sync_one
from app.worker import cleanup
from scripts.milestone0 import settings


def main():
    os.environ['DEMO_TEST_NAMESPACE']='document-proof-'+uid()[:12]
    app=Application(Store(settings()))
    text='PROFESSIONAL INTERESTS\n- You prefer diagrams when learning a technical concept.\n'
    parsed=preview('generic-test.txt',text)
    try:
        result=approve(app,'generic-test.txt',text,parsed['content_hash'],app.store.load()['generation'],
            [dict(passage_id='2',text=parsed['sections'][0]['passages'][0]['text'],category='interests')])
        assert result['queued']==1
        s=app.store.load();sync_one(app,s)
        assert not app.store.load().get('memory_ops')
        hits=app.retrieval.search(app.store.load(),'How do I prefer to learn technical concepts?')
        assert len(hits)==1 and hits[0]['source_kind']=='document' and hits[0]['source_line']==2
        for provider in ['openai','anthropic','local']:
            c=app.new_conversation()
            answer=app.send(c['id'],uid(),'How do I prefer to learn technical concepts?',provider=provider,
                           model=app.store.c[provider.upper()+'_MODEL'])['messages'][-1]
            assert len(answer['history_message_ids'])==1 and len(answer['memories'])==1
            assert 'diagram' in answer['text'].lower()
            print(provider+': source-linked document recall passed',flush=True)
    finally:
        app.reset(app.store.load()['generation']);s=app.store.load()
        for retired in s['retired']:cleanup(app,s,retired)
        app.retrieval.index.delete(drop=True)
        app.store.r.delete(app.store.key)
        print('Isolated fixture cleaned up.',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Proof failed: '+type(exc).__name__,flush=True)
        raise SystemExit(1)

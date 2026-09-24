"""Durable outbox delivery and asynchronous managed-memory reconciliation."""
import json
import time
from datetime import datetime

from app.core import build, now, Problem
from scripts.milestone0 import memory_record
from scripts.provenance import verify_name_source
from app.memory_review import queue_candidate


def not_found(exc):
    return getattr(exc, 'status_code', None) == 404


def search_session(app, owner, session):
    result, token = [], None
    while True:
        page = app.managed.search_long_term_memory(request={
            'filter': {'owner_id': {'eq': owner}, 'session_id': {'eq': session}},
            'limit': 100, 'page_token': token})
        result.extend(memory_record(m) for m in page.items)
        token = page.next_page_token
        if not token:
            return result


def deliver(app, state, job):
    conversation = state['conversations'][job['conversation_id']]
    session = job.get('session_id', conversation['id'])
    try:
        current = app.managed.get_session_memory(session_id=session, include_summarised_events=True)
        remote = current.events
        if current.owner_id != state['owner_id']:
            raise Problem('owner_mismatch', 'Managed session owner does not match this demo.')
    except Exception as exc:
        if not not_found(exc):
            raise
        remote = []
    for mid in job['message_ids']:
        message = next(m for m in conversation['messages'] if m['id'] == mid)
        matches = [e for e in remote if isinstance(e.metadata, dict) and e.metadata.get('app_message_id') == mid]
        if len(matches) > 1:
            raise Problem('duplicate_event', 'Duplicate service events need review; delivery is paused.')
        if matches:
            event = matches[0]
            if event.role != message['role'] or ''.join(p.text for p in event.content) != message['text']:
                raise Problem('event_conflict', 'Managed event content differs from its archived source.')
            job['events'][mid] = event.event_id
            app.store.save(state)
            continue
        if mid in job['events']:
            # Known accepted event may have expired; never duplicate its delivery.
            continue
        if mid in job['attempted']:
            job['delivery'] = 'uncertain'
            raise Problem('delivery_uncertain', 'An earlier delivery may have succeeded. No matching event is visible; automatic re-send is paused.')
        job['attempted'][mid] = now()
        job['delivery'] = 'sending'
        app.store.save(state)  # Intent checkpoint before the uncertain network boundary.
        try:
            event = app.managed.add_session_event(
                session_id=session, actor_id=state['owner_id'] if message['role'] == 'USER' else 'assistant',
                role=message['role'], content=[{'text': message['text']}],
                created_at=datetime.fromisoformat(message['created_at']),
                namespace=f"demo-{state['generation']}",
                metadata={'app_message_id': mid, 'generation': state['generation']}).event
        except Exception as exc:
            if getattr(exc, 'status_code', None) in (400, 401, 403, 404, 422, 429):
                job['attempted'].pop(mid, None)  # Explicitly rejected; safe to retry later.
                job['delivery'] = 'failed'
            else:
                job['delivery'] = 'uncertain'
            app.store.save(state)
            raise
        job['events'][mid] = event.event_id
        app.store.save(state)
    job['delivery'] = 'confirmed'
    app.store.save(state)


def reconcile(app, state, job):
    cid = job['conversation_id']
    session = job.get('session_id', cid)
    candidates = search_session(app, state['owner_id'], session)
    events = []
    for related in state['jobs'].values():
        if related.get('session_id', related['conversation_id']) != session:
            continue
        for mid, eid in related['events'].items():
            message = next(m for m in state['conversations'][cid]['messages'] if m['id'] == mid)
            events.append({'message_id': mid, 'managed_event_id': eid,
                           'role': message['role'], 'text': message['text'], 'created_at': message['created_at']})
    for memory in candidates:
        if any(memory['id'] in m.get('managed_ids', []) for m in state['memories'].values()):
            continue
        source = verify_name_source(memory, events, state['owner_id'], session)
        if not source:
            queue_candidate(state, memory, cid, events, session)
            continue
        # Equivalent name facts use one application record, while retaining managed IDs.
        existing = next((m for m in state['memories'].values()
                         if m['text'].casefold() == memory['text'].casefold()), None)
        mid = existing['id'] if existing else memory['id']
        if existing:
            existing['managed_ids'] = sorted(set(existing['managed_ids'] + [memory['id']]))
            record = existing
        else:
            record = dict(id=mid, text=memory['text'], status='active', revision=1,
                managed_ids=[memory['id']], managed_updated_at=memory['updated_at'],
                source_message_id=source['message_id'], source_event_id=source['managed_event_id'],
                conversation_id=cid, source_text=source['text'], source_created_at=source['created_at'],
                attribution_method='application_verified', category='about_me',
                fact_kind='name', people=[], saved_at=now())
        # For the name-only demo, a later explicit name statement supersedes an earlier one.
        for older in state['memories'].values():
            if older['id'] == mid or older['status'] != 'active':
                continue
            if older.get('fact_kind', 'name' if older.get('attribution_method') == 'application_verified' else None) != 'name':
                continue
            if older['source_created_at'] > record['source_created_at']:
                record['status'] = 'superseded'
            elif record['status'] == 'active':
                older['status'] = 'superseded'
                app.retrieval.put(state, older)
        app.retrieval.put(state, record)
        state['memories'][mid] = record
        for related in state['jobs'].values():
            if source['message_id'] in related['message_ids']:
                related['saved_memory_ids'] = sorted(set(related['saved_memory_ids'] + [mid]))
                related['extraction'] = 'observed'
    # No inferred "complete with zero memories" state: the service has no such signal.
    job['last_checked_at'] = now()
    app.store.save(state)


def cleanup(app, state, retired):
    from redisvl.extensions.cache.embeddings import EmbeddingsCache
    # Only recorded application session IDs are eligible; never enumerate the store broadly.
    for session in retired['sessions']:
        try:
            app.managed.delete_session_memory(session_id=session)
        except Exception as exc:
            if not not_found(exc):
                raise
        memories = search_session(app, state['owner_id'], session)
        protected = {mid for m in state['memories'].values() if m['status'] == 'active'
                     for mid in m.get('managed_ids', [])} if retired.get('preserve_active') else set()
        memories = [m for m in memories if m['id'] not in protected]
        if memories:
            app.managed.bulk_delete_long_term_memories(memory_ids=[m['id'] for m in memories])
        if any(m['id'] not in protected for m in search_session(app, state['owner_id'], session)):
            raise Problem('cleanup_pending', 'Managed memories are still visible; cleanup will retry.')
    for key in retired.get('projection_keys', []):
        app.store.r.delete(key)
    if hasattr(app.store, 'r') and not retired.get('preserve_active'):
        EmbeddingsCache(name=f"{app.store.prefix}:embeddings:{retired['generation']}",
                        redis_client=app.store.r).clear()
    retired['verified_empty_at'] = now()
    # Retain only opaque suppression metadata to remove any late managed promotion.
    retired['next_poll'] = time.time() + 60
    retired['error'] = None


def step(app):
    with app.store.lock():
        state = app.store.load()
        state['worker_at'] = now()
        app.store.save(state)
        from app.memory_lifecycle import sync_one
        if sync_one(app, state):
            return
        retired = next((r for r in state['retired'] if r['next_poll'] <= time.time()), None)
        if retired:
            try:
                cleanup(app, state, retired)
            except Exception as exc:
                retired['error'] = type(exc).__name__
                retired.pop('verified_empty_at', None)
                retired['next_poll'] = time.time() + 30
            app.store.save(state)
            return
        due = sorted((j for j in state['jobs'].values() if not j.get('disabled') and j['next_poll'] <= time.time()),
                     key=lambda j: j['next_poll'])
        if not due:
            return
        job = due[0]
        try:
            if job['delivery'] != 'confirmed':
                deliver(app, state, job)
            reconcile(app, state, job)
            job['error'] = None
        except Exception as exc:
            job['error'] = exc.message if isinstance(exc, Problem) else (
                f'Memory service operation failed ({type(exc).__name__}). Your conversation remains saved.')
        job['next_poll'] = time.time() + 20
        app.store.save(state)


def main():
    app = build()
    print('Memory worker started.', flush=True)
    while True:
        try:
            step(app)
        except Exception as exc:
            # Never print SDK errors, request content, endpoints, or credentials.
            print(json.dumps({'worker_error': type(exc).__name__}), flush=True)
        time.sleep(3)


if __name__ == '__main__':
    main()

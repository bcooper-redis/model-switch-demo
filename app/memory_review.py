"""Explicit source confirmation for managed facts outside the strict name verifier."""
import hashlib
import json

CATEGORIES = ('about_me', 'family', 'interests', 'experiences', 'current_life')


def fingerprint(memory):
    return hashlib.sha256(json.dumps({k: memory.get(k) for k in
        ('id', 'text', 'owner_id', 'session_id', 'updated_at')}, sort_keys=True).encode()).hexdigest()


def queue_candidate(state, memory, cid, events, session=None):
    # A service filter is not sufficient evidence of ownership or event lineage.
    if memory.get('owner_id') != state['owner_id'] or memory.get('session_id') != (session or cid):
        return
    if not memory.get('text') or len(memory['text']) > 4000:
        return
    sources = [dict(message_id=e['message_id'], event_id=e['managed_event_id'],
                    text=e['text'], created_at=e['created_at'])
               for e in events if e['role'] == 'USER']
    if not sources:
        return
    candidates = state.setdefault('candidates', {})
    previous = candidates.get(memory['id'])
    version = fingerprint(memory)
    if previous and previous['version'] == version:
        if previous['status'] == 'review':
            previous['sources'] = sources
        return
    candidates[memory['id']] = dict(id=memory['id'], text=memory['text'],
        conversation_id=cid, version=version, status='review', sources=sources,
        managed_updated_at=memory.get('updated_at'))


def review(app, candidate_id, version, source_id, category, people, accept):
    from app.core import Problem, now
    with app.store.lock():
        state = app.store.load()
        candidate = state.get('candidates', {}).get(candidate_id)
        if not candidate or candidate['version'] != version:
            raise Problem('candidate_changed', 'This candidate changed. Refresh before reviewing.')
        if candidate['status'] != 'review':
            return {'status': candidate['status']}
        if not accept:
            candidate.update(status='dismissed', reviewed_at=now())
            app.store.save(state)
            return {'status': 'dismissed'}
        source = next((s for s in candidate['sources'] if s['message_id'] == source_id), None)
        conversation = state['conversations'].get(candidate['conversation_id'])
        if not source or not conversation or not any(m['id'] == source_id and m['role'] == 'USER'
                and m['text'] == source['text'] for m in conversation['messages']):
            raise Problem('invalid_source', 'Select an original user message from this conversation.', 422)
        if category not in CATEGORIES:
            raise Problem('invalid_category', 'Choose a memory category.', 422)
        people = list(dict.fromkeys(p.strip() for p in people if p.strip()))
        # Identity is explicit and conservative: labels never automatically merge people.
        record = dict(id=candidate_id, text=candidate['text'], status='active', revision=1,
            category=category, people=people, managed_ids=[candidate_id],
            managed_updated_at=candidate['managed_updated_at'], source_message_id=source_id,
            source_event_id=source['event_id'], source_text=source['text'],
            source_created_at=source['created_at'], conversation_id=candidate['conversation_id'],
            attribution_method='user_confirmed', confirmed_at=now(), saved_at=now())
        # A failed projection leaves the candidate reviewable; retry uses the same ID.
        app.retrieval.put(state, record)
        state['memories'][candidate_id] = record
        candidate.update(status='accepted', reviewed_at=now())
        for job in state['jobs'].values():
            if source_id in job['message_ids']:
                job['saved_memory_ids'] = sorted(set(job['saved_memory_ids'] + [candidate_id]))
                job['extraction'] = 'observed'
        app.store.save(state)
        return {'status': 'accepted'}

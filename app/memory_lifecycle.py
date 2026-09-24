"""Canonical edits first; durable, retryable cleanup through the managed API."""
import time


def change(app, memory_id, revision, text=None, delete=False):
    from app.core import Problem, now, uid
    with app.store.lock():
        s = app.store.load()
        memory = s['memories'].get(memory_id)
        if not memory or memory['status'] != 'active' or memory['revision'] != revision:
            raise Problem('memory_changed', 'This memory changed. Refresh before editing.')
        if not delete and (not text or not text.strip()):
            raise Problem('empty_memory', 'Enter the corrected fact.', 422)
        if memory_id in s.get('memory_ops', {}):
            raise Problem('memory_sync_pending', 'Wait for the previous change to finish syncing.')
        old_ids = memory['managed_ids'][:]
        cid = memory['conversation_id']
        sessions = {j.get('session_id', j['conversation_id']) for j in s['jobs'].values()
                    if not j.get('disabled')}
        # Retire whole extraction sessions because the service does not provide reliable
        # per-fact source-event lineage. Keep other already accepted long-term facts.
        if sessions:
            s['retired'].append(dict(generation=s['generation'], sessions=sorted(sessions),
                next_poll=0, error=None, projection_keys=[], preserve_active=True))
        for job in s['jobs'].values():
            if job.get('session_id', job['conversation_id']) in sessions:
                job.update(disabled=True, extraction='cancelled')
        for candidate in s.get('candidates', {}).values():
            if candidate['status'] == 'review':
                candidate['status'] = 'retired'
        # Old transcript remains visible, but is excluded from future answering context.
        # Apply the boundary to every existing chat, including answers that quoted it.
        for conversation in s['conversations'].values():
            conversation['history_floor'] = len(conversation['messages'])
            conversation['managed_session_id'] = uid()
        memory['revision'] += 1
        memory['sync_status'] = 'pending'
        if delete:
            memory.update(status='deleted', text='', source_text='', people=[], managed_ids=[])
        else:
            edit_cid, source_id, remote_id = uid(), uid(), uid()
            edited_at = now()
            s['conversations'][edit_cid] = dict(id=edit_cid, title='Memory correction',
                created_at=edited_at, messages=[dict(id=source_id, request_id=uid(), role='USER',
                    text=text.strip(), status='complete', created_at=edited_at)])
            memory.update(text=text.strip(), source_text=text.strip(), source_message_id=source_id,
                source_kind='edit',
                source_event_id=None, conversation_id=edit_cid, source_created_at=edited_at,
                attribution_method='user_edited', managed_ids=[remote_id])
        # Remove obsolete copied memory payloads from historical inspector evidence.
        for conversation in s['conversations'].values():
            for message in conversation['messages']:
                if any(m['id'] == memory_id for m in message.get('memories', [])):
                    message['memories'] = [m for m in message['memories'] if m['id'] != memory_id]
                    message['evidence_invalidated'] = True
        s.setdefault('memory_ops', {})[memory_id] = dict(old_ids=old_ids, next_poll=0, error=None)
        app.store.save(s)
        return {'status': memory['status'], 'sync_status': 'pending'}


def sync_one(app, state):
    from app.core import now
    operation = next(((mid, op) for mid, op in state.get('memory_ops', {}).items()
                      if op['next_poll'] <= time.time()), None)
    if operation is None:
        return False
    mid, op = operation
    memory = state['memories'][mid]
    try:
        if memory['status'] == 'active':
            app.retrieval.put(state, memory)
        elif hasattr(app.store, 'r'):
            app.store.r.delete(f'{app.store.prefix}:memory:{mid}')
        # Cached embeddings are derived personal data; clear this generation's cache.
        if hasattr(app.store, 'r') and op['old_ids']:
            from redisvl.extensions.cache.embeddings import EmbeddingsCache
            EmbeddingsCache(name=f"{app.store.prefix}:embeddings:{state['generation']}",
                            redis_client=app.store.r).clear()
        if op['old_ids']:
            app.managed.bulk_delete_long_term_memories(memory_ids=op['old_ids'])
            for old_id in op['old_ids']:
                try:
                    app.managed.get_long_term_memory(memory_id=old_id)
                except Exception as exc:
                    if getattr(exc, 'status_code', None) != 404:
                        raise
                else:
                    raise RuntimeError('managed_deletion_pending')
        if memory['status'] == 'active':
            app.managed.bulk_create_long_term_memories(memories=[dict(id=memory['managed_ids'][0],
                text=memory['text'], owner_id=state['owner_id'], session_id=memory['conversation_id'],
                memory_type='semantic', topics=[memory.get('category', 'about_me')])])
            # Verify the saved value, not merely a successful write acknowledgement.
            from app.worker import search_session
            saved = search_session(app, state['owner_id'], memory['conversation_id'])
            if not any(m['id'] in memory['managed_ids'] and m['text'] == memory['text'] for m in saved):
                raise RuntimeError('managed_verification_pending')
        memory.update(sync_status='synced', synced_at=now())
        memory.pop('sync_error', None)
        del state['memory_ops'][mid]
    except Exception as exc:
        op.update(next_poll=time.time()+20, error=type(exc).__name__)
        memory['sync_status'] = 'pending'
        memory['sync_error'] = 'Sync failed; the worker will retry automatically.'
    app.store.save(state)
    return True

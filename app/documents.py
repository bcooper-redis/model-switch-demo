"""Deterministic text preview and explicit approval; no model executes document text."""
import hashlib
from pathlib import PurePath
from app.memory_review import CATEGORIES


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def preview(filename, text):
    from app.core import Problem
    if not filename.lower().endswith('.txt') or '\x00' in text or len(text.encode('utf-8')) > 200000:
        raise Problem('invalid_document', 'Choose a UTF-8 .txt file up to 200 KB.', 422)
    text = text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    sections = []
    section = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.isupper() and not line.startswith('- '):
            section = dict(id=str(number), title=line, notes=[], passages=[], recommended=('PROFESSIONAL' in line or 'WORK WITH AI' in line))
            sections.append(section)
        elif line.startswith('- '):
            if section is None:
                section = dict(id='0', title='Document', notes=[], passages=[], recommended=False)
                sections.append(section)
            if len(line) > 4000:
                raise Problem('passage_too_long', 'A bullet exceeds 4,000 characters. Split it before importing.', 422)
            section['passages'].append(dict(id=str(number), line=number, text=line[2:].strip()))
        elif section:
            section['notes'].append(line)
    provenance_notes = [n for s in sections if not s['passages'] and
                        (s['title'] == 'ABOUT THIS FILE' or 'PROFILE' in s['title']) for n in s['notes']]
    sections = [s for s in sections if s['passages']]
    for section in sections:
        section['notes'] = provenance_notes + section['notes']
    if not sections or sum(len(s['passages']) for s in sections) > 300:
        raise Problem('invalid_document', 'Use section headings and up to 300 dash-prefixed bullet points.', 422)
    return dict(filename=PurePath(filename).name[:200], content_hash=digest(text), sections=sections)


def approve(app, filename, text, content_hash, generation, selections):
    from app.core import Problem, now
    parsed = preview(filename, text)
    if parsed['content_hash'] != content_hash:
        raise Problem('document_changed', 'The document changed. Preview it again.')
    passages = {p['id']: (s, p) for s in parsed['sections'] for p in s['passages']}
    if not selections or len({p['passage_id'] for p in selections}) != len(selections):
        raise Problem('invalid_selection', 'Select distinct facts to save.', 422)
    for item in selections:
        if item['passage_id'] not in passages or item['category'] not in CATEGORIES or not item['text'].strip():
            raise Problem('invalid_selection', 'Review the selected facts and categories.', 422)
    with app.store.lock():
        state = app.store.load()
        if generation != state['generation']:
            raise Problem('generation_changed', 'The demo was reset. Preview the document again.')
        doc_id = digest(state['owner_id'] + generation + content_hash)[:32]
        documents = state.setdefault('documents', {})
        document = documents.setdefault(doc_id, dict(id=doc_id, filename=parsed['filename'],
            content_hash=content_hash, imported_at=now(), passages={}))
        count = skipped = 0
        for item in selections:
            section, passage = passages[item['passage_id']]
            mid = digest(doc_id + ':' + passage['id'])[:32]
            # The same source can never silently replace a correction or resurrect a deletion.
            if mid in state['memories']:
                skipped += 1
                continue
            source = dict(passage, section=section['title'], notes=section['notes'])
            document['passages'][passage['id']] = source
            state['memories'][mid] = dict(id=mid, text=item['text'].strip(), status='active', revision=1,
                category=item['category'], people=[], managed_ids=[mid], sync_status='pending',
                source_kind='document', document_id=doc_id, source_message_id=passage['id'],
                source_event_id=None, conversation_id=doc_id, source_text=passage['text'],
                source_section=section['title'], source_line=passage['line'], source_notes=section['notes'],
                source_created_at=now(), attribution_method='document_confirmed', saved_at=now())
            state.setdefault('memory_ops', {})[mid] = dict(old_ids=[], next_poll=0, error=None)
            count += 1
        app.store.save(state)  # Facts, provenance, and outbox commit together.
        return dict(document_id=doc_id, queued=count, skipped=skipped)

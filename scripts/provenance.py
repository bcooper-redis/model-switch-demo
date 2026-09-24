"""Conservative evidence validation for the name-only milestone.

This never creates a memory from source text. It accepts only an existing managed
memory whose entire claim matches an explicit user statement in the same session.
Attribution is application-verified, not a claim of native managed event lineage.
Unsupported wording, compound facts, or ambiguous sources stay quarantined.
"""
import re

NAME = r"([A-Za-z]+(?:[ '-][A-Za-z]+)*)"
USER_NAME = re.compile(r'My name is ' + NAME + r'\.?', re.IGNORECASE)
MEMORY_NAME = re.compile(r"(?:The )?user(?:'s|’s) name is " + NAME + r'\.?', re.IGNORECASE)


def verify_name_source(memory, events, owner_id, session_id):
    if memory.get('owner_id') != owner_id or memory.get('session_id') != session_id:
        return None
    claim = MEMORY_NAME.fullmatch(memory.get('text', '').strip())
    if not claim:
        return None
    matches = []
    for event in events:
        if event.get('role') != 'USER':
            continue
        stated = USER_NAME.fullmatch(event.get('text', '').strip())
        if stated and stated[1].casefold() == claim[1].casefold():
            matches.append(event)
    return matches[0] if len(matches) == 1 else None

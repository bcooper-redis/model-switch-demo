from datetime import datetime, timezone
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from contracts import MemoryProjection, eligible


def record(**changes):
    now = datetime.now(timezone.utc)
    data = dict(id='memory-1', owner_id='owner-1', managed_memory_id='managed-1',
                managed_updated_at=now, text='A supported fact', category='about_me',
                status='active', sources=[dict(message_id='message-1',
                    conversation_id='conversation-1', managed_event_id='event-1',
                    evidence_type='user_statement', attribution_method='application_verified')],
                created_at=now, updated_at=now, revision=1,
                embedding_model='text-embedding-3-small', embedding_dimensions=1536)
    return MemoryProjection(**(data | changes))


def test_unattributed_memory_cannot_be_active():
    with pytest.raises(ValidationError):
        record(sources=[])


@pytest.mark.parametrize('status', ['pending', 'superseded', 'removal_pending', 'deleted'])
def test_ineligible_states_are_not_recalled(status):
    assert not eligible(record(status=status), 'owner-1', 1)


def test_other_owner_and_stale_revision_are_excluded():
    memory = record()
    assert eligible(memory, 'owner-1', 1)
    assert not eligible(memory, 'owner-2', 1)
    assert not eligible(memory, 'owner-1', 2)

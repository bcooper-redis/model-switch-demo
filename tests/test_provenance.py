import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from provenance import verify_name_source


@pytest.mark.parametrize('name', ['Maren', 'Brian', 'Alex Rivera', "Jean-Luc"])
def test_name_validation_is_not_hardcoded(name):
    memory = dict(owner_id='o', session_id='s', text=f"The user's name is {name}.")
    event = dict(role='USER', text=f'My name is {name}.')
    assert verify_name_source(memory, [event], 'o', 's') == event


@pytest.mark.parametrize('text', ['Imagine my name is Maren.', '"My name is Maren."',
                                 'My name is Alex.', 'Maren is my friend.'])
def test_hypothetical_quoted_or_different_claim_is_rejected(text):
    memory = dict(owner_id='o', session_id='s', text="The user's name is Maren.")
    assert verify_name_source(memory, [dict(role='USER', text=text)], 'o', 's') is None


def test_assistant_compound_claims_and_ambiguous_sources_are_rejected():
    memory = dict(owner_id='o', session_id='s', text="The user's name is Maren.")
    event = dict(role='USER', text='My name is Maren.')
    assert verify_name_source(memory, [event | {'role': 'ASSISTANT'}], 'o', 's') is None
    assert verify_name_source(memory, [event, event], 'o', 's') is None
    assert verify_name_source(memory, [event], 'other', 's') is None
    assert verify_name_source(memory, [event], 'o', 'other') is None
    memory['text'] += ' They live in Paris.'
    assert verify_name_source(memory, [event], 'o', 's') is None

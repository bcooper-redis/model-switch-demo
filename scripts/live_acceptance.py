"""Explicit opt-in live test. Creates and resets its own isolated test namespace."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core import build, uid
from app.worker import step

os.environ['DEMO_TEST_NAMESPACE'] = 'm1-test-' + uid()
app = build()
results = {'namespace': app.store.namespace}
destination = Path('.artifacts/live-acceptance.json')


def record(label, value):
    results[label] = value
    destination.write_text(json.dumps(results, indent=2))
    print(json.dumps({label: value}), flush=True)


try:
    first = app.new_conversation()['id']
    baseline = app.send(first, uid(), "What's my name?")['messages'][-1]
    assert not baseline['memories'] and 'Test Person' not in baseline['text']
    record('empty_baseline', baseline['text'])
    rid = uid()
    app.send(first, rid, 'My name is Test Person.')
    record('introduction_saved', True)
    deadline = time.monotonic() + 660
    while not app.snapshot()['memories'] and time.monotonic() < deadline:
        step(app)
        time.sleep(3)
    assert app.snapshot()['memories'], 'Managed extraction did not reconcile before deadline'
    record('source_linked_memory', app.snapshot()['memories'])
    app.send(first, rid, 'My name is Test Person.')
    assert len(app.store.load()['conversations'][first]['messages']) == 4
    record('duplicate_request_deduplicated', True)
    fresh = app.new_conversation()['id']
    recalled = app.send(fresh, uid(), "What's my name?")['messages'][-1]
    assert 'Test Person' in recalled['text'] and len(recalled['history_message_ids']) == 1
    assert len(recalled['memories']) == 1
    record('fresh_recall', recalled['text'])
    before = app.snapshot()
    app.reset(before['generation'])
    step(app)
    after = app.snapshot()
    assert not after['memories'] and not after['conversations'] and not after['jobs']
    assert before['owner_id'] == after['owner_id'] and before['generation'] != after['generation']
    assert not after['reset_cleanup_pending']
    new = app.new_conversation()['id']
    unknown = app.send(new, uid(), "What's my name?")['messages'][-1]
    assert not unknown['memories'] and 'Test Person' not in unknown['text']
    record('reset_baseline', unknown['text'])
    # Clear the final test question too; keep tombstones for the reset verification.
    app.reset(app.snapshot()['generation']);step(app)
    record('passed', True)
except Exception as exc:
    record('failed', type(exc).__name__)
    raise SystemExit(1)

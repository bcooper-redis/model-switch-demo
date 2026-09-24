# Redis shared context demo

Milestone 4 is in progress: reviewed family/interests/experience memories, corrections,
deletion, private chat, export, and service evidence now accompany the three providers.
Durable conversations, a separate memory worker, and source-linked recall use
Redis Agent Memory and RedisVL.
Names can be source-verified automatically. Broader managed facts require explicit
user confirmation of the fact and supporting message before recall. See
[Milestone 4 status](docs/milestone-4.md) and [new-service setup](docs/milestone-4-setup.md).

## Setup

Python 3.12 is the validated runtime. Install the pinned dependencies:

```sh
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.lock
```

Populate `.env` using `.env.example`. Credentials are backend-only. Never commit
`.env`, use frontend credential variables, or print SDK exception payloads.

Build the UI once (and again after frontend changes):

```sh
cd frontend
npm ci
npm run build
cd ..
```

Start the API and worker together:

```sh
.venv/bin/python scripts/run.py
```

Open http://127.0.0.1:8765/. Ctrl-C stops both processes. To choose another port,
use `DEMO_PORT=8766 .venv/bin/python scripts/run.py`. The launcher checks for an
occupied port before starting either process. Port 8000 was already used by a
Docker service on the development machine.

Ask “What's my name?”, introduce yourself with your name, and wait for the fact
to appear under **Saved in Redis**. Start a new conversation, optionally switch
providers, and ask again. The evidence panel shows the memory supplied to the
model and links to its supporting user message. Reset demo starts a clean generation.

### Presenter note: extraction timing

The presenter changed Agent Memory's extraction cadence to **60 seconds** on
September 23, 2026. Confirm this setting in the service's Configuration tab before
a demo; the default is **5 minutes**. Earlier milestone reports describe that
original default configuration.

This is a background extraction interval, not a promise that a memory will be
ready exactly 60 seconds after a message. Extraction and application reconciliation
add processing time. Use **Saved in Redis** as the readiness signal before starting
the fresh-conversation recall step. Facts under **Needs source review** require
review and approval before recall.

Suggested narration: “The conversation is saved immediately. Redis Agent Memory
extracts durable facts in the background; this demo checks on a one-minute cadence.
Once the fact is ready, we'll open a new conversation with another model to show
that the saved context carries over.”

**Memories supplied** records what a selected answer received when it was generated;
old answers do not gain memories afterward. An answer in the same conversation can
use chat history even when this count is zero. Keep LangCache off for the personal
memory proof; cached answers are not evidence of memory recall.

See [Milestone 2](docs/milestone-2.md) for provider configuration and switching validation,
and [Milestone 1](docs/milestone-1.md) for memory behavior and limitations.

For local generation, start `.venv/bin/python scripts/local_runtime.py serve` in a
separate terminal. See [Milestone 3](docs/milestone-3.md) for runtime setup, local
execution evidence, and the cloud services that remain in use.

## Upload personal context

Choose **Upload context** in the sidebar, select your text profile, review the
sections/facts, and save the approved memories. Wait for cloud sync, then start
a fresh conversation with another provider. See [document import](docs/document-import.md)
for source tracking, supported format, and lifecycle behavior. No profile is preloaded.

## Validation

```sh
.venv/bin/python -m pytest -q
```

The optional `.venv/bin/python scripts/live_acceptance.py` uses real services and
a unique disposable test namespace. It can take up to eleven minutes while
waiting for extraction and cleans its own test records through scoped reset.

## Milestone 0 probe

Run from this directory:

```sh
.venv/bin/python scripts/milestone0.py connect
.venv/bin/python scripts/milestone0.py start
.venv/bin/python scripts/milestone0.py poll
.venv/bin/python scripts/milestone0.py deliver
.venv/bin/python scripts/milestone0.py projection
.venv/bin/python scripts/milestone0.py recall
.venv/bin/python -m pytest -q
```

`start` creates a unique probe owner, two scripted fictional conversations, and
scoped application records. It saves messages and durable outbox entries in one
Redis transaction, then submits the events through Agent Memory's supported API.
It does not create a long-term memory directly or implement a substitute extractor.
`deliver` resumes using message IDs in managed event metadata to avoid re-sending
already observed events. It is a single-process probe, not a concurrency-safe
production synchronizer. Do not run concurrent probe commands.

`poll` checks extraction without re-sending events. Results are saved in ignored
`.artifacts/`; an empty result is pending, not confirmed zero-result completion.
Repeated polling does not prove the service's processing job succeeded.

Once a managed name memory appears, `projection` validates its evidence, loads it
through RedisVL twice to test replay, and checks owner/status filtering.
`recall` starts a fresh process and retrieves from the persisted index; it compares
an OpenAI answer with no memories to an answer with retrieved memories. Neither
request includes the source transcript or a previous-response chain.

The `.artifacts/milestone0.json` checkpoint preserves the probe's identifiers.
Do not delete it to reset data: cloud records would remain. No broad database or
store reset is performed. The Milestone 1 name proof must use a different, empty
owner/namespace and must not reuse these scripted fixtures.

See `docs/milestone-0.md` for results, API limitations, and Milestone 1 contracts.

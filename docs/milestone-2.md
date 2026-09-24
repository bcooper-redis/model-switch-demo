# Milestone 2 — Anthropic and model switching

Implemented September 22, 2026. Milestone 3 has not started.

## Behavior

The header has separate answering-provider and model selectors. Each provider
remembers its selected model while the page stays open; a reload restores the
configured defaults. New conversations retain the current selection. Switching
inside an existing conversation shares that conversation's bounded history with
the selected provider. Use a **new conversation** for the portability proof.

Every new user turn saves its provider and model before generation. Retries reuse
that pair, and conflicting retry parameters are rejected. The selectors are locked
while a turn is running or unfinished. Assistant messages display the provider and
model that actually answered, independently of the current selector. A provider
error preserves the saved user turn and never falls back to another provider.

Both adapters use the same memory instructions, current-conversation history,
owner, RedisVL retrieval, and existing memory records. Source quotations remain
in the evidence UI and are excluded from model requests. Switching the answering
model does not re-embed stored memories or change Redis-managed extraction.

## Configuration

Server-side `.env` settings:

```dotenv
ANTHROPIC_API_KEY='your-key'
ANTHROPIC_MODEL=claude-sonnet-5
# Needed for keys that are not scoped to a workspace:
ANTHROPIC_WORKSPACE_ID='your-workspace-id'
# Optional additional model IDs allowed in the selectors:
OPENAI_MODELS=gpt-4.1-mini
ANTHROPIC_MODELS=claude-haiku-4-5-20251001
```

Each default model is always included. If the optional lists are omitted, the
additional defaults are GPT-4.1 mini and Claude Haiku 4.5. To restrict a provider
to its default model, set its plural list to the default model's ID. Restart after
changing configuration. Models must support the adapter's text-generation API;
configuration is an allowlist, not automatic account-wide model discovery.
Providers without a key and default model are disabled in the selector. Configured
models can still fail due to access, quota, or availability; errors are shown.

Anthropic uses its Messages REST API through pinned HTTPX, with the API key and
optional workspace header held server-side. OpenAI continues using the Responses
SDK. No new Redis keys, memory schema, or managed-store configuration is required.

## Validation

- All 35 automated tests pass, including routing, immutable retry selection, no
  transcript replay, invalid selections before writes, Claude response/payload
  validation, and failure without provider fallback. Production frontend build passes.
- Live API acceptance passes OpenAI → Claude → OpenAI, plus both alternative
  configured models, all recalling Brian from the same existing memory ID.
- Each acceptance conversation supplies exactly one history message; duplicate
  submission returns the same saved response. Owner, generation, and canonical
  memories remain unchanged.
- Browser validation exercises the provider/model controls and source evidence.

Run the existing demo with `.venv/bin/python scripts/run.py`, then optionally run:

```sh
.venv/bin/python scripts/milestone2.py
```

The live acceptance expects the existing Brian name proof. It creates visible
conversations and uses real provider APIs; it does not reset the demo or seed new
memories. Its report is ignored at `.artifacts/milestone2.json`.

Milestone 1's name-only verification and pending-extraction limitations still
apply. Local generation, broader personal facts, memory editing, private mode,
Context Retriever, and LangCache remain later milestones.

API references: [Anthropic Messages](https://platform.claude.com/docs/en/api/messages/create),
[Anthropic authentication](https://platform.claude.com/docs/en/manage-claude/authentication),
[OpenAI models](https://developers.openai.com/api/docs/models).

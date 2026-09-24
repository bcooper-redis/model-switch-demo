# Milestone 4 — in progress

Implemented and validated on 2026-09-22:

- Managed extraction remains the only automatic memory producer. Facts beyond the strict name verifier enter a review queue; the user confirms the entire fact and selects a supporting user message from the same managed session. These are labeled **user confirmed**, not application-verified. Assistant messages cannot be selected. Dismissals and review-version conflicts are persisted. Unreviewed candidates never enter recall.
- Five categories: about me, family, interests, experiences, current life. Optional person labels and case-insensitive text/person search. Labels do not merge identities automatically. Category selection currently occurs during candidate review.
- Edit/delete with revision checks, durable retry state, immediate canonical invalidation, and live managed read-back verification. A correction is a new explicit source record; the old managed record is deleted and its replacement is created idempotently through the official SDK. RedisVL owns the application projection.
- Retrieval checks current text and revision after owner/generation/status-filtered vector search. Stale index hits cannot supply an old fact.
- Private chat uses a separate browser component and server path with no store/retrieval/managed-memory calls. The normal polling component unmounts. History lives only in browser component memory, closes on reload/close, and expires after 30 minutes. Provider retention still applies; browser/process memory is not forensic erasure. No server or browser persistent private history is created.
- JSON export of saved conversations and memories with provenance, excluding credentials/private chat. This is a readable export, **not** a complete operational backup or restore system.
- Collapsible per-answer service evidence and a separate fixed public-fact LangCache example via RedisVL `LangCacheSemanticCache`. Both cache lookup and storage use task, prompt_version, provider, model, settings attributes and a one-hour TTL. Personal/private chat never reaches the cache example path. No arbitrary user text is accepted by that endpoint.

## Correction/deletion boundaries

### Demo progression controls

The non-personal example has a LangCache switch, initially off. Off calls the
selected answering model with no cache read/write; on uses managed cache lookup
and stores misses. Switching off never clears entries. The result reports the
actual bypass/hit/miss and timings. Personal/private chat remains cache-ineligible.

Planned progression: fresh chat without recall → RedisVL memory recall → Context
Retriever relationship retrieval → LangCache on an eligible public example.
Context Retriever's planned switch controls retrieval, not data ingestion/deletion;
its off state retains RedisVL recall. The service integration is still pending.
Prefix search and typeahead belong to the separate search demo and are outside this application’s scope.

The service does not expose authoritative per-fact source lineage. A change therefore retires **all currently open extraction sessions**, stops their pending jobs, dismisses their unreviewed candidates, rotates sessions for future messages, and removes old chat history from future answering prompts. Other accepted memories are preserved. The UI explains this before confirmation.

The worker deletes retired session events/summaries and unprotected long-term records, then retains opaque tombstones and checks every minute for late promotion. Cleanup remains visibly pending on failure. Managed mutation retry state survives restart. Historical conversation text is retained and remains exportable; deleting a memory does not delete its original conversation. Copied obsolete memory payloads are removed from historical inspector evidence.

This conservative policy avoids presenting stale personal facts, but sacrifices pending extraction after a correction. A narrower policy needs verified managed-service lineage support. User-edited memories use their edit record as source; there is no invented managed source-event ID.

## Validation

- 67 automated tests passed, including source review, stale confirmation, private storage isolation, provider/model cache scoping, revision rejection, correction retry across application restart, late-promotion cleanup, and export exclusion.
- Frontend TypeScript/Vite build passed.
- `python -m scripts.milestone4` passed against the configured Redis, Agent Memory, OpenAI, Anthropic, and local Ollama. An isolated explicit fictional fixture recalled kayaking at revision 1 and hiking at revision 2 in fresh conversations across all three providers, with one history message each. Managed correction/deletion and an exported JSON encode/decode round trip passed. Fixture namespace/index and remote records were cleaned up. This is **not** evidence of automatic broad extraction or a restore drill.
- Browser private-chat test returned a fictional codeword; a durable conversations/memories/candidates fingerprint was unchanged, and reload discarded the private session.

Run automated checks:

```sh
.venv/bin/python -m pytest -q
cd frontend && npm run build
```

Optional live fixture proof (uses real answering providers, no extractor session events):

```sh
.venv/bin/python -m scripts.milestone4
```

## Remaining before milestone sign-off

- Provision Context Retriever and LangCache using [setup instructions](milestone-4-setup.md).
- Implement and prove Context Retriever entity relationships, generated-tool routing, owner/access enforcement, and revision/deletion checks against the live service. No fabricated MCP tool names are used; the UI explicitly says not integrated.
- Validate real LangCache hit/miss/TTL/attribute behavior; currently contract-tested with a fake service only.
- The text-document upload/review/source flow is implemented and validated; see [document import](document-import.md). Complete structured entity/relationship modeling and the presenter’s real-profile demo after user approval. The fictional family-trip narrative is superseded.
- Verify restore into an isolated target and deletion reconciliation; the current JSON round trip proves serialization only.

Milestone 5 automated backups, broader retention administration, and production readiness are not claimed.

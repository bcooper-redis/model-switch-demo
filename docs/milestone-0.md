# Milestone 0: configuration and contracts

Date: September 21, 2026. Scope: real service probes and implementation contracts;
no chat UI, provider switching, Context Retriever, or LangCache implementation.

## Configuration

| Setting | Selected / observed |
|---|---|
| Runtime | Python 3.12 (local probe uses 3.12.9) |
| RedisVL | 0.27.2 |
| Agent Memory SDK | redis-agent-memory 0.4.1 |
| OpenAI SDK | 3.16.2 |
| Redis client | redis-py 8.1.0 |
| Answering model | OpenAI gpt-5.4-mini |
| Projection embeddings | OpenAI text-embedding-3-small, 1536 dimensions, FLOAT32, COSINE |
| Projection index | FLAT for the initial small dataset; schema v1 in schemas/memory-v1.yaml |
| Cloud Redis | 8.6.2; authenticated TLS; noeviction; one connected replica observed |
| Database persistence | AOF enabled; last AOF write and RDB save status reported OK |
| Managed extraction credentials | Redis-managed (user confirmed) |
| Agent Memory short-term TTL | 1 day (user confirmed and screenshot) |
| Agent Memory long-term TTL | 365 days (user confirmed and screenshot) |
| Extraction cadence | Default; current documentation defines this as 5 minutes |
| Summarization | Enabled after 20 messages; retain 10 recent messages (screenshot) |
| Custom memory types | None (screenshot) |

Dependencies, including transitive dependencies, are pinned in requirements.lock.
No production recovery-point guarantee is inferred from Redis INFO. Backup schedule,
export, recovery testing, and retention beyond 365 days remain later work. Canonical
application messages have no automatic TTL; managed session expiration is separate.
Managed extraction model identities are not exposed by the data-plane SDK. Record
them if the service makes them available; do not imply they match the answering model.

## Verification status

Live connectivity passed for Redis PING, Agent Memory store health, OpenAI generation,
and OpenAI embeddings. Measured initial round trips: Redis 0.32 s, Agent Memory
health 0.53 s, OpenAI generation plus embedding 4.63 s. These are individual observations,
not latency targets or benchmarks.

Two fictional scripted completed turns were archived atomically with outbox entries:
one says `My name is Maren.`; the other is a greeting without a proposed durable fact.
Both were delivered through the official managed API. Each session contained two
events after delivery and after restarting the probe and retrying delivery.

**Milestone 0 passed for the name-only contract, with the limitations below.**

| Live check | Result |
|---|---|
| Managed name extraction | `User's name is Maren.` created at 19:00:01 UTC from a turn submitted at 18:55:30 UTC; about 271 seconds |
| Managed owner/session | Matched the opaque probe owner and originating session |
| Source verification | Exact name claim validated against the canonical user statement; application message ID and managed event ID retained |
| RedisVL projection | Real managed record indexed and retrieved for `What's my name?` |
| Projection replay | Two loads of the same managed ID yielded one searchable record |
| Owner/status isolation | Other-owner and superseded-record queries returned no results |
| Fresh-process recall without memory | OpenAI: `I don't know your name.` |
| Fresh-process recall with RedisVL context | OpenAI: `Your name is Maren.` |
| Transcript/provider chain | Neither request included the original conversation or a previous-response ID |
| Greeting-only extraction | No memory observed; no completion signal, so it remains pending rather than being labeled completed with zero results |
| Local validation | 15 tests passed, including source rejection, owner isolation, inactive states, stale revisions, and multiple fictional names |

The name was learned through managed extraction, not inserted directly into the
managed memory store. The full Milestone 1 UI, empty-namespace Brian demonstration,
and robust background worker remain unimplemented. Raw fictional evidence and
checkpoints are local, ignored files in `.artifacts/`.

## Verified API boundaries and implementation decisions

### Delivery and retry

The SDK's add_session_event accepts application IDs in metadata, but assigns event IDs
server-side and exposes no explicit idempotency-key parameter. Do not automatically
retry uncertain POSTs. Preserve application message IDs, returned event IDs, and
delivery intent in Redis. After an uncertain result, inspect the managed session,
including summarized events where supported, for the same app_message_id. Do not
blindly replay a message after compaction or expiration prevents reconciliation.

The probe's read-before-write retry check passed in a single process; it does not
establish exactly-once delivery under concurrency. Milestone 1 must serialize delivery
per session, reclaim abandoned work safely, retain uncertain state, and test the
crash-after-service-acceptance case. Use one stable actor/owner ID for user messages.

### Extraction and status

The installed SDK exposes store health and session/long-term-memory retrieval, but
no per-turn promotion status endpoint. A successful event write establishes delivery,
not extraction. Empty search results cannot distinguish a pending job, failure, or
successful run with no facts. Keep `Memory processing pending` unless source-linked
usable records or a verified service completion signal justify a stronger status.
Finding one fact does not prove that every extractor has completed a turn.

Represent these independently:

- Delivery: queued / sending / uncertain / confirmed / failed.
- Extraction: pending / observed / complete / failed. `complete` requires a real
  completion signal and is not currently inferred from searches.
- Projection: pending / ready / quarantined / failed.

### Provenance

The current MemoryRecord schema includes owner_id, session_id, timestamps, and
attributes, but no standard source-event ID. Session-level lineage alone is not
sufficient to attribute an arbitrary claim to a particular message.

For the name-only milestone, a conservative application adapter validates the entire
managed name claim against exactly one explicit `My name is ...` user statement in
the referenced canonical session. The record must already exist in Agent Memory;
the adapter never independently extracts or creates a memory. Unsupported wording,
assistant-only evidence, compound claims, ambiguous matches, and wrong owners stay
quarantined. Mark this as `application_verified` attribution. Never label it as
native event-level provenance supplied by Agent Memory.

This deliberately narrow adapter is not a general biography reconciler. Broader
source attribution must be verified before enabling expanded memory types. Custom
source fields, if used later, must also be validated against actual source text.

### Projection and context

The application owns the versioned projection schema. Keep managed memory IDs and
updated timestamps alongside source message/event IDs and correction revisions.
Apply owner and active-status filters through RedisVL before vector ranking; recheck
source/control revisions before releasing an answer. Superseded or deleted records
cannot be active recall candidates. All stored embeddings use one model/dimension
configuration regardless of the answering provider.

Use RedisVL vectorizers and EmbeddingsCache (bounded TTL) for projection embeddings.
Agent Memory's internal embeddings are a separate vector space. Do not read or modify
managed internal Redis keys. Querying managed APIs is the only managed-data access path.

Compatibility findings: the SDK's generated serializers return camelCase JSON even
when Python field names use snake_case; the adapter normalizes explicit fields.
RedisVL 0.27.2's OpenAITextVectorizer determines dimensions by a real embedding call;
passing `dims` to its constructor is forwarded to the OpenAI client and fails.
The probe therefore checks the observed dimensions against the versioned schema.

### Outbox and atomicity

Store completed answers and synchronization tasks in one Redis transaction. Key names
for keys involved in that transaction share an opaque owner hash tag to allow same-slot
operations on a clustered database. The probe uses a unique run hash tag for isolation.
No distributed transaction is assumed between Redis and managed services. Delivery
acknowledgement and later extraction/projection checkpoints are independent.

## Integration matrix

| Operation | Interface | Reason |
|---|---|---|
| Index lifecycle, loading, filtered vector queries | RedisVL IndexSchema, SearchIndex, VectorQuery, Tag | Required RedisVL application retrieval path |
| Projection embeddings and embedding cache | RedisVL OpenAITextVectorizer, EmbeddingsCache | Supported RedisVL AI operations |
| Canonical archive, ID maps, transactions, durable outbox | redis-py | Ordinary Redis primitives, not managed AI operations |
| Session events, session reconciliation, managed memory search/fetch | Official redis-agent-memory SDK | Managed service API boundary |
| Answer generation | Official OpenAI SDK Responses API with store=False | Stateless answering interface; no previous-response chain |
| Context Retriever and LangCache | Deferred to Milestone 4 | Not prerequisites for first proof |

## Milestone 1 handoff

Implement the minimal OpenAI UI and durable synchronizer only after this milestone's
review. Use a new opaque demo owner and empty namespace, not this probe's owner or
fixtures. Add unknown-name baseline, real completed turns, source disclosure, fresh
conversation recall, process restart, explicit recall-failure handling, retry tests,
and scoped reset. Do not let reset jobs resurrect old data. Keep LangCache bypassed.

## References checked during implementation

- [Agent Memory developer guide](https://redis.io/docs/latest/develop/ai/context-engine/agent-memory/developer-guide/)
- [Agent Memory configuration and extraction cadence](https://redis.io/docs/latest/operate/iris/agent-memory/create-service/)
- [Managed model credentials](https://redis.io/docs/latest/operate/iris/agent-memory/model-configuration/)
- [RedisVL documentation](https://docs.redisvl.com/en/latest/)
- [OpenAI answering model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)

The Redis skill's older fixed-cadence description is superseded by current official
documentation, which permits a 60–600 second cadence setting. The user's service is
currently set to Default. No Cloud configuration was changed by this probe.

# Product requirements: Redis Shared Context Demo — Personal Chatbot

Status: Draft for review  
Version: 0.5 — RedisVL-first, model-independent context demo  
Date: September 21, 2026

## 1. Product purpose

**Objective: Demonstrate portable personal context across interchangeable AI models using Redis Cloud.**

Use a RedisVL-first Python application. The personal chatbot is the demo experience: it remembers family, interests, and life experiences while Redis supplies a shared context layer independent of the answering provider.

The main proof is continuity: information learned while using one model remains available after switching to another, with visible provenance and consistent corrections. This reduces model-provider dependence; it does not guarantee identical answers or capabilities across models, or eliminate dependence on the selected Redis platform.

The user chats in one application and can choose OpenAI, Anthropic, or supported local models. The application owns the conversation history and memory, so changing models does not require starting over.

Redis Cloud is the selected data and context platform, with access to Agent Memory, Context Retriever, and LangCache. Service availability is an accepted planning assumption; endpoint configuration and integration behavior will be verified during implementation. The chat application may initially run locally, but ordinary personal data and managed memory processing reside in cloud services. Local answering models do not make this an entirely local system.

The first release prioritizes a small collection of accurate, traceable memories that the assistant uses appropriately. It should feel familiar without inventing familiarity, making unsupported assumptions, or bringing up personal details unnecessarily.

## 2. Target user and needs

The initial product is a single-user Redis capability demonstration for technical evaluators and presenters. It uses a fictional personal biography by default and can later serve one adult managing their own history. People mentioned in conversations are subjects of memories, not additional users or accounts.

Primary needs:

- Avoid repeating personal background in every conversation.
- Discuss family, interests, and experiences with an assistant that recalls relevant context.
- Understand exactly what the assistant remembers and where it learned it.
- Correct, remove, or temporarily withhold information easily.
- Keep personal history independent of the answering model.
- Recover saved history after an application or host restart and from a backup.

## 3. Delivery scope: OpenAI first, then provider switching

**Scope precedence:** The first deliverable is the OpenAI-only name-memory proof below. The broader requirements in this document describe the eventual Redis capability demo and personal-use hardening; they must not block this small first milestone unless explicitly listed in its exit criteria. Provider switching is added in order: Anthropic, then a locally running model.

### First working demo: My name is Brian

1. Start with an empty demo memory namespace and an opaque user ID. Ask the selected OpenAI model What's my name? It must say the name is not known; the application must not inject Brian from account metadata, fixtures, or a hardcoded profile.
2. Say My name is Brian. Persist the source message in Redis Cloud and submit the completed turn to Agent Memory. Show processing status until a source-linked name memory is reconciled into the RedisVL-managed application projection.
3. Ask What's my name? using the same OpenAI model. Retrieve the persisted fact through RedisVL before generation and show the supporting record/source in a small memory panel.
4. Start a fresh conversation, retain the same opaque owner ID and selected OpenAI model, and ask What's my name? again. Supply the retrieved memory, but do not supply the original conversation, provider conversation IDs, or a previous-response chain. The answer must identify Brian from Redis-backed context.
5. Restart the application and repeat the fresh-conversation recall. Redis remains the durable source.

The same-conversation turn illustrates the experience; the fresh-conversation turn is the proof that the answer depends on saved memory rather than transcript replay. The initial unknown-name check proves the fact was not seeded. LangCache is bypassed throughout this flow.

### First-milestone requirements

- A minimal chat UI, one configurable OpenAI model, New conversation, memory save/pending/error status, and a source-linked retrieved-memory panel.
- Redis Cloud canonical messages plus a durable delivery/reconciliation task; managed Agent Memory extraction; RedisVL index creation and retrieval over reconciled application-owned memory records.
- A stable opaque owner ID across conversations. The owner ID and application title must not reveal the tested name to the model.
- One provider interface implemented for OpenAI. Future provider adapters reuse the same owner, memory schema, and retrieval function.
- Visible errors, retry-safe writes, persistence across app restart, and an explicit reset limited to this demo's records. Do not call a queued extraction a saved memory.
- A targeted test of unknown-name -> save -> fresh recall, source attribution, retry without duplication, and no hardcoded name. A separate fictional name can be used to rule out Brian-specific logic.
- Cloud credentials remain server-side. Only the first milestone's endpoints and configured models are required.

Not required to pass this first milestone: Anthropic credentials, Ollama installation, local model download, Context Retriever integration, LangCache integration, family-trip data, full category management/editing, private-chat UI, guided onboarding, comprehensive backup automation, or a production evaluation suite. These remain planned later features. Do not present deferred controls as available.

### Eventual demo scope


Included:

- Text chat, model selection, saved conversations, and automatic recall.
- RedisVL-first application-owned indexing, retrieval, embeddings, and supported cache integrations.
- Repeatable fictional demo data and an explicit reset scoped only to the demo namespace.
- An optional demo inspector showing retrieved records, provider/model, memory changes, Redis service calls, cache status, and measured timings.
- Automatic extraction of supported personal memories from ordinary conversations.
- A What I remember view with About Me, People, Interests, Experiences, and Current Life categories.
- Source navigation and edit/delete controls on every memory.
- A discreet extraction status indicator.
- Private chat with no durable conversation or memory storage.
- Optional guided onboarding through conversation.
- Managed Redis Cloud storage and Agent Memory, Context Retriever for structured personal context, and selectively enabled LangCache.
- Automated backups/exports and documented recovery across the database and managed services.
- Downloadable conversation and memory export.

Excluded:

- Multiple users, shared family accounts, or family-wide access permissions.
- Importing or synchronizing native ChatGPT or Claude histories and built-in memories.
- Email, calendar, social media, file, photo, audio, or location ingestion.
- Voice, autonomous actions, reminders, and proactive outreach.
- Model fine-tuning or training on the user's data.
- Public internet deployment and mobile applications.
- A comprehensive genealogy system or automatic psychological profiling.

## 4. Product principles

1. Remember supported information, not plausible guesses.
2. Preserve stories as well as individual facts.
3. Make every saved memory traceable and controllable.
4. Distinguish historical facts from current circumstances.
5. Use personal context only when it helps answer the current question.
6. Clearly distinguish saved data, pending processing, and failed operations.
7. Treat private chat as a separate mode with explicit boundaries.
8. Prefer RedisVL directly for supported application-owned Redis AI operations; document concrete exceptions.
9. Keep answering-provider adapters thin and preserve shared context when changing models.
10. Demonstrate actual service behavior and measured outcomes; label simulated fixtures, cache bypasses, and unavailable features accurately.

## 5. Core user journeys

### 5.1 Begin with guided onboarding

The user can start chatting immediately or choose Help you get to know me. The assistant asks one optional question at a time across background, important people, interests, meaningful experiences, and current life. The user can skip a topic, stop, or return later.

Before onboarding, the application explains that ordinary chats are saved and can create memories, that memories are editable, and that private chat is available. It also identifies the configured providers that process messages and memory extraction.

The same extraction rules apply to onboarding and ordinary conversation. Completion is not required to use the product.

### 5.2 Have an ordinary conversation

The user starts or reopens a conversation and chooses a configured model. The application saves each message, retrieves relevant existing memories, supplies bounded context to the selected model, and saves the answer. Agent Memory processes synchronized session events for extraction. The application reconciles resulting memories with source references and user corrections before making them eligible for recall.

After successful extraction, a quiet indicator such as Saved 2 memories appears beside the relevant turn. Selecting it opens those memories. A successful run with nothing worth remembering does not produce a distracting notification.

### 5.3 Recall a shared experience

The user asks about an activity with a family member. The assistant recalls relevant experiences and preferences, identifies uncertainty or age where material, and distinguishes remembered information from its new suggestions. The user can expand a context disclosure to inspect the memories supplied for that answer.

### 5.4 Inspect and correct a memory

The user opens What I remember, navigates a category or searches, and selects a memory. The detail view shows its content, relevant people and dates, source, and last update. Editing updates the searchable memory and any derived profile content. The edit is recorded as a direct user correction.

### 5.5 Forget information

The user deletes a memory. The application removes it from recall and derived summaries, cancels or invalidates affected pending extraction, and prevents automatic recreation from already-processed source content. The UI explains that the original conversation remains unless separately deleted.

Deleting a conversation removes its messages and linked derived content. If a memory has another independent source, the application explains that it may remain and provides a way to delete it as well.

### 5.6 Start a private chat

The user deliberately starts a new private conversation. The interface remains visibly marked Private. No stored personal memories are retrieved, no new memories are extracted, and messages are held only for that active session. Reloading or closing the private session discards its history.

Private mode does not change the selected model provider's processing or retention policies. The interface explains this distinction before the first private message. Existing saved conversations cannot silently be relabeled private.

## 6. Functional requirements

### Chat and conversation history

- CHAT-01: Support creating, listing, reopening, and deleting conversations.
- CHAT-02: Support configured OpenAI, Anthropic, and local-model adapters. Show availability and the selected model; never silently switch providers.
- CHAT-03: Allow changing the answering model while retaining the conversation and shared memories.
- CHAT-04: Save ordinary user messages before generation and answers after successful generation. Save timestamps, roles, model identity, and completion/failure state.
- CHAT-05: Retrieve context before each ordinary answer. If recall fails, show the failure and require an explicit continuation without recall rather than presenting normal memory-enabled behavior.
- CHAT-06: Keep requests within a configured context budget. Preserve complete stored history even when only a subset or summary is supplied to the model.
- CHAT-07: Handle retry and duplicate submission without duplicating messages or extraction jobs.
- CHAT-08: Display generation failure clearly and retain the saved user message for retry. Never label an incomplete response as complete.

### Memory creation and organization

- MEM-01: Submit completed ordinary turns to Agent Memory for asynchronous extraction through a durable synchronization queue. Reconcile extracted records into application-visible memories. Do not depend on browser-close events, and do not run a duplicate custom extraction pipeline by default.
- MEM-02: Save durable, user-grounded facts, relationships, interests, meaningful experiences, and current circumstances. Do not save every sentence as a separate memory.
- MEM-03: Preserve a coherent experience record when isolated facts would lose the story's meaning.
- MEM-04: Treat assistant statements, role-play, quoted examples, and hypothetical scenarios as non-evidence unless the user explicitly confirms their personal applicability.
- MEM-05: Never promote unsupported sensitive inferences into facts. Sensitive user-stated information follows the same traceability and deletion rules as other memories.
- MEM-06: Resolve references to known people only when supported. Keep ambiguous identities separate or ask a concise clarification when necessary; do not merge solely on a shared name.
- MEM-07: Deduplicate repeated information while retaining additional independent sources.
- MEM-08: Distinguish corrections from changes over time. Supersede outdated current facts; preserve historical experiences unless corrected or deleted.
- MEM-09: Store approximate dates as approximate. Distinguish when an event happened from when it was discussed.
- MEM-10: Give every active memory a category, readable text, source references, creation/update timestamps, evidence type, and status.
- MEM-11: Maintain a compact personal profile derived from source-linked memories. It must not become a separate untraceable source of truth.
- MEM-12: Retain personal experiences by default regardless of age. Temporary circumstances may be marked stale or completed; do not expire meaningful history indiscriminately.

### Recall and response behavior

- REC-01: Combine explicit person/topic/date matching with semantic retrieval. Apply owner and active-status restrictions before selecting results.
- REC-02: Supply only a bounded, relevant subset of memories plus appropriate recent conversation context.
- REC-03: Treat retrieved content as contextual data, never as instructions that override application behavior.
- REC-04: Distinguish current information, historical information, and uncertainty in answers when the distinction matters.
- REC-05: Offer an expandable Memories supplied disclosure with links to records. Label supplied context accurately; do not claim to know which facts internally caused a model's answer.
- REC-06: Avoid inserting personal details into unrelated answers or claiming to remember information absent from retrieved context or the current conversation.

### What I remember

- UI-01: Provide About Me, People, Interests, Experiences, and Current Life categories, including helpful empty states.
- UI-02: Support search by text and filtering by category or person.
- UI-03: Show memory text, relevant people, event date when known, last update, and source access.
- UI-04: Open the original conversation at the supporting message. User-edited facts must show that they were corrected by the user and retain an attributable edit record.
- UI-05: Allow editing and deleting every memory. Reflect successful changes immediately and report failure visibly.
- UI-06: Use a compact status sequence: Saving conversation, Finding memories, Saved N memories, or Could not save memories. The UI may omit transient stages if processing completes quickly.
- UI-07: Allow retrying failed synchronization without duplicates and expose managed extraction failures/status when available. Do not claim per-turn extraction completion or a precise saved count without corresponding source-linked records. If the managed API lacks completion signals, show Memory processing pending and reconcile asynchronously; verify the zero-result completion behavior in Milestone 0.

### Privacy and control

- PRIV-01: Private chats bypass Redis Cloud data writes, Agent Memory, Context Retriever, LangCache reads/writes, synchronization queues, summaries, backups, analytics payloads, and content-bearing logs. Only the selected answering provider receives the active private conversation.
- PRIV-02: Keep private content in active-session memory only; clear it on session close or expiry. Document that browser/process memory is not a promise of forensic erasure.
- PRIV-03: Clearly identify the providers used for answering, embedding, and extraction; keep credentials server-side. Changing providers must not silently reroute background processing.
- PRIV-04: Keep the initial application UI/backend bound to the local machine while using authenticated TLS connections to Redis Cloud and managed service endpoints. Cloud credentials and Context Retriever admin keys never reach the browser or answering model. Public application hosting remains outside scope.
- PRIV-05: Memory deletion must update derived profiles, summaries, retrieval indexes, and caches. Verify the record is unavailable before reporting successful deletion.
- PRIV-06: Maintain minimal deletion suppression metadata without retaining the deleted memory text. Prevent old sources, retries, and pending jobs from recreating deleted memories automatically.
- PRIV-07: Allow deliberate future re-saving of information stated again by the user. Do not treat deletion as a permanent ban on the topic.
- PRIV-08: Export readable conversations and structured memories with provenance, excluding private chats and secrets.

## 7. Redis Cloud architecture and data ownership

### 7.1 Component responsibilities

| Component | Planned responsibility | Boundary |
|---|---|---|
| Application backend | Save turns, enforce private mode, orchestrate recall, apply corrections/deletions, build prompts, and call providers | Required memory behavior is application-controlled, not dependent on the answering model choosing a tool |
| RedisVL | Preferred Python interface for application-owned index schemas/lifecycle, vector and filtered retrieval, vectorization, embedding caching, and supported LangCache integration | Does not replace managed-service APIs or ordinary Redis transaction/Stream operations |
| Redis Cloud application database | Canonical conversation archive, people/relationship records, provenance, revisions, synchronization queue, deletion controls | Application-owned schema, separate from undocumented managed-service internal keys |
| Redis Agent Memory | Working session context, managed long-term extraction and memory search | Use supported APIs; verify provenance, mutation, lifecycle, and completion behavior before relying on them |
| Redis Context Retriever | Governed retrieval over modeled people, relationships, interests, experiences, and current-life records | Reads the application-owned structured projection; no assumed direct integration with Agent Memory internals |
| Redis LangCache | Reuse responses for explicitly approved, context-independent tasks | Not the source of personal memory; ordinary personalized answers and private chats bypass it by default |
| OpenAI / Anthropic / local runtime | Generate answers from the context supplied by the application | Answering model selection is independent of managed extraction and embedding configuration |

Agent Memory is the managed memory engine. The application database is the authority for original messages, user edits, deletion state, and identity mapping. Structured records exposed through Context Retriever are versioned projections of reconciled memories, not an independently learned second biography. Explicit user corrections take precedence over older extracted content.

### 7.2 Ordinary-turn flow

1. Store the user message in the application database with an idempotent request ID. Load the current personal-data revision.
2. Retrieve recent context from the canonical archive and, where useful, Agent Memory session context. Search Agent Memory for long-term memories through its supported API. Use RedisVL for filtered semantic/keyword retrieval over the reconciled application-owned memory projection; preserve the managed memory ID and revision so results can be merged without creating independent facts.
3. Call Context Retriever through the backend's MCP client for applicable entity paths, such as person -> experiences or person -> current interests. Define and inspect actual generated tools during setup; these paths are design examples, not assumed API names.
4. Validate all retrieved result sets against current owner, source, correction/deletion state, and projection versions. Exclude stale or untraceable content, merge duplicates, and build a bounded prompt. Recheck the revision before returning an answer if a concurrent correction/deletion occurred.
5. Bypass LangCache for the ordinary personalized answer. Call the selected answering model and persist the completed answer plus an outbox task atomically in the application database.
6. Deliver the completed turn to Agent Memory using stable application-to-service ID mappings and retry-safe synchronization. There is no distributed transaction across the database and service APIs; the durable outbox and reconciliation close that gap.
7. Observe managed extraction results, validate provenance and current control state, and update structured projections and the memory revision. Show Saved N memories only for newly reconciled, usable records attributable to that turn.

Recent canonical messages cover the interval before managed extraction finishes. A managed-service outage never silently converts the application into a different memory system. Memory synchronization can remain pending while ordinary saved chat continues, with the state shown clearly. Retrieval failures follow CHAT-05.

### 7.3 Record placement

| Record | Authority and location | Derived representation |
|---|---|---|
| Original conversation/messages | Redis Cloud application database; individually addressable, ordered, with model and status | Agent Memory session events for managed context/extraction; source history is retained independently of session compaction |
| Extracted personal memory | Agent Memory through its supported API; application control records govern eligibility | Source-linked projection used by What I remember and Context Retriever |
| Person and relationships | Application-owned JSON with stable IDs and supported relationship sources | Context Retriever entity definitions and generated retrieval tools |
| Experience, interest, current circumstance | Projection of reconciled memory with original memory ID and revision | Context Retriever relationship paths and category views |
| User correction/deletion | Application-owned durable control records | Propagated to managed memories, projections, summaries, and cache invalidation |
| Synchronization task | Redis Stream/outbox metadata | Managed service IDs, attempt state, and reconciliation checkpoint |
| Cached eligible response | LangCache | Disposable optimization, never an authoritative personal record |

Never directly modify Agent Memory's internal Redis keys. If an API cannot represent a required field, store the additional metadata in the application database linked to the managed memory ID. Verify source-message attribution in Milestone 0 and safe edit/delete behavior before the expanded demo. Records without adequate provenance must not enter active recall.

Configure custom memory types corresponding to About Me, People, Interests, Experiences, and Current Life where supported. Keep application category mapping separate from service-specific type names. Define extraction instructions for fictional examples, assistant suggestions, ambiguous identities, approximate dates, and sensitive inference. Evaluate actual results rather than assuming instructions guarantee compliance.

Managed embedding/extraction models are configured at the service level. Verify supported providers, region, retention, and migration behavior; do not assume Redis Cloud can call a laptop's Ollama instance. Changing the answering model must not change the memory store.

### 7.4 RedisVL-first implementation requirements

- RVL-01: Use a Python backend and RedisVL as the primary application library for Redis AI features. Pin and validate a supported version in Milestone 0.
- RVL-02: Define application-owned search schemas and index lifecycle through RedisVL IndexSchema and SearchIndex/AsyncSearchIndex. Keep schema definitions versioned. Do not hand-build FT.CREATE/FT.SEARCH command strings for features RedisVL supports.
- RVL-03: Build vector, text/hybrid, and metadata-filtered queries through supported RedisVL query/filter abstractions. Apply owner and eligibility filters before ranking. Verify exact APIs against the pinned release.
- RVL-04: Use RedisVL vectorizers and EmbeddingsCache for application-owned projection embeddings where applicable. Track embedding model/version and keep its vector space separate from managed Agent Memory internals. No private content enters these caches.
- RVL-05: Prefer RedisVL LangCacheSemanticCache for the managed LangCache integration. This uses the hosted service; do not substitute RedisVL SemanticCache backed directly by Redis and label it LangCache. Validate attribute filters, deletion support, and score/threshold conventions for the chosen wrapper.
- RVL-06: Evaluate RedisVL rerankers when retrieval evaluation shows a benefit. SemanticRouter may route eligible demo requests if useful, but neither routing nor reranking is required merely to increase feature count. Do not use probabilistic routing alone to decide private-mode or personal-cache eligibility.
- RVL-07: Use official Agent Memory SDK/REST APIs for managed session/memory behavior and the official Context Retriever SDK/CLI/MCP interfaces for entity definitions and retrieval. Do not assume RedisVL wraps all managed services. Prefer a supported RedisVL integration if one is verified at implementation time.
- RVL-08: Use redis-py for ordinary JSON/hash/message operations, Streams, transactions, and other unsupported primitives. Avoid framework wrappers that hide RedisVL; introduce another orchestration framework only for a specific demonstrated need.
- RVL-09: Keep one small integration matrix identifying each operation, RedisVL class or managed SDK used, and reasons for exceptions. Exceptions must reflect a capability gap rather than convenience.
- RVL-10: The normal demo must exercise RedisVL retrieval over real application-owned data. RedisVL must not be present only as an unused dependency or optional benchmark path. Projection records remain derived, versioned, and reconstructible from authoritative memory and correction state.

### 7.5 LangCache policy

- Include LangCache in the architecture and validate it against an approved non-personal workload, such as standalone product-help explanations.
- Semantic caching of personalized chat answers is disabled by default. Similar wording is insufficient evidence that personal context, time, or conversation intent is unchanged.
- Eligible searches must match task, prompt version, provider/model, and relevant settings using configured exact attributes. Use bounded retention and evaluated similarity thresholds; failure or cache miss proceeds to generation.
- If personal response caching is enabled in a later approved scope, retrieve current context first and bind entries to owner, personal-data revision, context fingerprint, conversation state, and model configuration. Never serve a result solely on prompt similarity.
- Private chat never searches or populates LangCache. Memory extraction does not use a response cache that could transplant facts between conversations.
- Corrections/deletions invalidate affected entries; unknown dependencies require broad invalidation for the owner. Cached outputs never become evidence for new memories.

### 7.6 Capability verification before building user flows

Service access is assumed. Verify capabilities when their delivery stage begins: Milestone 0 covers name extraction, source attribution, synchronization, and search; the expanded demo covers the remaining lifecycle and service behaviors. The full verification inventory is: source/event identifiers, custom memory fields, listing/search pagination, update/delete operations, promotion timing, prevention of re-promotion after deletion, session compaction, export/recovery, Context Retriever schemas and access scopes, and LangCache filters/deletion.

Where a service lacks a required lifecycle control, use an explicit application adapter or mark the behavior as an implementation blocker. In particular, hiding a deleted record from recall is not equivalent to deleting managed copies. Until all copies are removed, show removal pending. Do not weaken privacy or provenance requirements silently.

## 8. Persistence and recovery

- DATA-01: Use Redis Cloud persistence, high availability, and backup settings appropriate to the selected plan. Keep application personal records on a no-eviction configuration and cache data logically separate. Remove local Redis-volume and fixed AOF assumptions from the deployment plan.
- DATA-02: Atomically save a completed answer and its service-synchronization outbox task in the application database. Across managed services use stable IDs, retry-safe writes, and reconciliation rather than assuming shared transactions.
- DATA-03: Acknowledge synchronization work after confirmed delivery; separately track managed processing and projection completion. Preserve restart-safe checkpoints and visible failures. Verify native idempotency support and implement reconciliation where unavailable.
- DATA-04: Configure automated backups of the application database and a verified backup/export strategy for Agent Memory data and service configuration. Do not assume a database backup includes managed-service state. Target daily recoverable copies with seven-day retention, using supported scheduling and independent encrypted storage.
- DATA-05: Show last successful backup/export per authoritative store and report partial failures. Back up Context Retriever schemas, extraction settings, ID mappings, and control records. Recreate LangCache empty after restoration.
- DATA-06: Restore into a clean environment, reconstruct projections, reconcile service IDs and pending jobs, and verify original sources before reopening recall. A valid conversation backup alone is not a complete memory restore.
- DATA-07: Old backups may retain deleted information until expiration. Keep minimal deletion metadata independently recoverable and apply it before restored data is available. Document provider-managed retention and deletion limitations explicitly.
- DATA-08: Target a recovery point of at most 24 hours for full recovery and measure recovery time in a restore drill. Set crash/failover data-loss expectations only after validating the selected Cloud/service configurations; do not carry forward the local one-second AOF assumption.

## 9. Acceptance scenarios

| Scenario | Required result |
|---|---|
| Cross-model recall | Tell one model a fictional family fact; retrieve it in a fresh conversation using another model, with the correct source. |
| Experience preservation | Describe a trip; preserve the event and user-stated significance without inventing dates or interests. |
| Unsupported inference | Mention that a relative enjoyed one hike; do not save a general lifelong outdoor preference. |
| Ambiguous identity | Mention two people with the same name; do not merge their memories automatically. |
| Correction | Correct an event year; subsequent recall uses the corrected year and identifies the user correction. |
| Changed preference | State a changed interest; current recommendations use the new preference while historical experiences remain available. |
| Repetition | Repeat a fact across turns; maintain one equivalent active memory with attributable sources. |
| Delete memory | Delete a fact; confirm it is absent from recall and derived content, including after queued jobs retry. |
| Delete conversation | Delete a source conversation; remove its exclusively supported memories and explain independently supported survivors. |
| Private chat | Discuss a unique fictional fact; confirm it never reaches durable records, queues, backups, or later recall. |
| Extraction failure | Fail service delivery or managed processing; retain the conversation, show pending/failure accurately, and reconcile without duplicate usable memories. |
| Generation failure | Fail the provider request; retain the user turn and permit a clean retry. |
| Restart | Restart app/synchronizer and simulate Cloud connectivity loss; reopen conversations and resume pending synchronization without duplicate events. |
| Restore | Restore a backup into a clean instance, reconcile subsequent deletions, and verify recall and provenance. |
| Export | Export ordinary history and memories; verify readable content and source IDs, with no private content or credentials. |
| Structured context | Resolve an identified family member through Context Retriever and retrieve only current, source-linked related records. |
| Cross-service deletion | Delete a fact while promotion is pending; ensure no stale managed record, projection, summary, or cached result becomes usable again. |
| Cache eligibility | Demonstrate a hit on approved non-personal help and a bypass on personalized and private conversations. |
| Correction during retrieval | Change a memory while a reply is in progress; prevent an obsolete cached or retrieved fact from being returned as current. |
| Service recovery | Restore application and managed memory state, reconstruct Context Retriever definitions/projections, and start LangCache empty. |
| RedisVL integration | Normal recall uses RedisVL-managed application indexes and query/filter abstractions, with source IDs and result traces. |
| Model portability | Switch OpenAI -> Anthropic -> local generation without changing memory ownership, re-ingesting biography data, or re-embedding because of the answering-model change. |
| Honest observability | The inspector distinguishes managed-memory search, RedisVL search, Context Retriever results, LangCache hit/miss/bypass, and provider generation. |

## 10. Quality and success criteria

Before the production-hardening release, create a reviewed test collection containing at least 30 fictional conversations covering family relationships, interests, experiences, corrections, ambiguous names, hypotheticals, and private chats.

Production-hardening release targets (the first demo uses the focused criteria below):

- Every saved memory has a valid source or attributable direct user edit.
- At least 95% of saved factual claims in the reviewed collection are directly supported by their sources. Model-generated confidence is not a substitute for review.
- At least 90% of labeled answerable recall questions receive the expected supporting memory within the configured retrieval budget.
- All acceptance scenarios involving private storage, deletion suppression, idempotency, and restoration pass.
- No silent provider fallback, save failure, or extraction failure.
- No more than one equivalent active memory per repeated fact in the deduplication scenarios.

Measure retrieval, generation, and extraction latency separately on the selected hardware and models. Set numerical latency targets after the first representative end-to-end measurement; extraction must remain outside the answer's critical path.

### Expanded signature demo: after the three provider milestones

1. Tell an OpenAI model about a fictional family trip.
2. Switch to Claude and ask a follow-up requiring that memory.
3. Switch to a local model and request a related suggestion.
4. Correct a detail and demonstrate that all three use the updated context.
5. Show the Redis services involved at each step.

Step 5 is visible throughout the walkthrough, with a recap at the end. The demo inspector must show actual service activity, selected provider/model, source-linked retrieved memories, and correction revisions. It must distinguish RedisVL (the application library) from Redis Cloud services and show LangCache hit, miss, or bypass honestly; every service need not be called on every turn.

Use clearly labeled fictional data and wait for observable extraction/reconciliation completion before demonstrating recall. At least one follow-up must occur in a fresh conversation without the original transcript so the demonstration proves shared long-term context rather than only re-sent chat history. After the correction, explicitly test the updated detail with OpenAI, Claude, and the local model. All three must receive the current context and answer consistently with the corrected fact; their wording and suggestions may differ. A configured model must actually run for its step to pass—no silent replacement or simulated response.

A short supporting capability demonstration uses two eligible non-personal questions to show managed LangCache through RedisVL. Personalized and private requests visibly bypass caching. This supports the five-step story without making cached answers look like cross-model memory.

### Demo essentials versus production hardening

| Stage | Required outcome | Deferred work |
|---|---|---|
| First build: OpenAI only | Save Brian's name in Redis, retrieve it through RedisVL with the same model in a fresh chat, and show the source | Other providers, full family story, Context Retriever, LangCache, and full memory-management UI |
| Second build: Anthropic | Switch to Claude, ask What's my name? in a fresh chat, and retrieve the existing memory | Local inference and broader capability demo |
| Third build: local model | Switch to a genuinely local model, ask the same question, and reuse the unchanged Redis context | Expanded family-trip presentation and production hardening |
| Expanded Redis demo | Five-step family-trip story, correction across all three providers, Context Retriever paths, LangCache through RedisVL, memory controls, private mode, and service inspector | Broad operational hardening |
| Production hardening | Automated recovery, full retention/deletion administration, larger evaluation suite, fault testing, and guided onboarding | Outside the first working demo |

Facts and service activity must be truthful at every stage. A feature counts only when implemented and exercised, not because a dependency or service is available. Basic Cloud persistence is required immediately; a verified backup/export precedes use for real personal history, and automated recovery belongs to hardening.

## 11. Delivery milestones

### Milestone 0: Minimal configuration and contracts

Select one OpenAI answering model and obtain its API access, Redis Cloud database credentials, and Agent Memory service/store credentials. Verify source attribution, delivery/reconciliation behavior, and one extraction of a fictional name. Pin RedisVL and configure the application projection's embedding model/provider and dimensions. Check whether managed extraction/embedding requires additional service-side model credentials. Do not require Context Retriever, LangCache, Anthropic, or local runtime configuration at this stage.

### Milestone 1: Working OpenAI memory demo

Implement exactly the section 3 name-memory flow and first-milestone requirements. Agent Memory creates the source-linked fact; RedisVL manages the application-owned projection and retrieves it before OpenAI generation. Demonstrate both same-conversation recall and fresh-conversation recall, plus application restart. Complete this vertical slice before implementing another answering provider.

Exit: OpenAI answers Brian in a fresh conversation using a displayed persisted Redis memory; without that memory and without the source transcript it must not know the answer.

### Milestone 2: Add Anthropic switching

Add the Anthropic adapter and provider selector using an Anthropic API key. Keep the same owner ID, Redis records, retrieval logic, and embeddings. Start a fresh Claude conversation and ask What's my name? without repeating the introduction or replaying the OpenAI transcript. The retrieved record must be the same existing name memory. Verify switching back to OpenAI still works. No biography migration or re-extraction is required merely to switch providers.

### Milestone 3: Add a locally running model

Install/configure Ollama or another local inference runtime and an appropriate downloaded model for the available hardware. Add its adapter to the same selector. Verify generation is actually local, then ask What's my name? in a fresh conversation with the same Redis context. Cloud memory remains cloud-hosted even though generation runs locally.

### Milestone 4: Expand into the full Redis capability demo

Use the document-led personal-context progression below instead of the fictional family-trip story. Implement source/edit/delete/category views, private mode, cross-provider corrections, Context Retriever entity paths, and managed LangCache through RedisVL for eligible non-personal examples. Extend the memory panel into a collapsible service inspector with measured timings and explicit hit/miss/bypass states. Include isolated anonymous test fixtures, safe reset, backup/export verification, and focused failure tests. Do not seed named fictional people into the presenter’s demo.

#### Document-led demo progression (updated 2026-09-23)

1. Start with the existing unknown-name → name introduction → fresh-chat recall proof, switching answering providers against the same saved context.
2. Upload the user's ChatGPT-produced personal-information document through the application. The upload is an explicit demo action, not hidden seeding. The document format will be established from the supplied file.
3. Preview the parsed source and proposed facts/relationships. Treat the document as data, never instructions. An assistant-authored document is not automatically verified truth: allow the user to confirm, correct, exclude, and resolve conflicts before facts become eligible for recall. Do not silently overwrite newer corrections.
4. Persist approved facts with document ID, content hash, source passage/section or page locator, confirmation status, categories, stable entity IDs, and revisions. Use supported managed-service ingestion and retain canonical import provenance in the application database. Re-importing the same document must not duplicate facts. Excluding or deleting an import must reconcile its derived records and retrieval projections.
5. Open fresh conversations with OpenAI, Anthropic, and the local model. Ask questions grounded in approved document content. Supply retrieved excerpts/facts rather than replaying the complete document or previous conversation. Show exactly which facts and sources each answer received.
6. Compare Context Retriever off (RedisVL memory recall) and on (additional governed entity/relationship retrieval). Build relationships only where the approved source supports them; no invented people or connections. Keep the answering model constant for this comparison, then show the same context with other models.
7. Correct one approved detail and prove revision-aware recall across providers. Demonstrate LangCache separately on eligible non-personal questions; personal imported content and private chat remain cache-ineligible.

Uploading in private mode is outside this import flow. Document parsing/ingestion errors must not produce partially approved recall records. The import UI must disclose configured external processors before submission. The text-document upload/review flow is implemented; see docs/document-import.md for its supported format and validation. Structured relationship extraction and the real-profile acceptance demo remain pending.

### Milestone 5: Personal-use hardening

Complete automated backup/export/restore, deletion reconciliation after restore, retention administration, guided onboarding, expanded fault tests, and all quality/acceptance scenarios before claiming readiness as a dependable personal-history application.

## 12. Confirmed decisions and remaining configuration

Confirmed:

- Delivery order is OpenAI-only name recall, then Anthropic switching, then local-model switching, followed by the expanded Redis demonstration.
- The primary objective is a Redis capability demo with a shared context layer that reduces answering-model lock-in.
- RedisVL is heavily favored for supported application-owned Redis AI operations, with documented SDK/primitive exceptions.
- Redis Cloud is the data and context platform; Agent Memory, LangCache, and Context Retriever are available for this project.
- Agent Memory handles managed conversational memory; Context Retriever supplies structured personal context; LangCache is used selectively.
- Planning remains separate from provisioning and implementation. No cloud resources or paid services are created by this document update.

Remaining configuration:

- Choose the Cloud region, service endpoints, and database topology based on supported co-location and latency.
- Confirm whether the initial UI/backend runs locally (proposed) or a separately scoped authenticated host. A local app with Redis Cloud still stores ordinary personal data in the cloud.
- Choose answering models and supported managed embedding/extraction settings; record every provider that processes personal information.
- Choose backup/export destination, supported schedules, retention, and encryption/key management.
- Confirm ordinary conversation retention: proposed default is until manually deleted, with storage visibility.
- Confirm private mode's strict default: no durable personal-context reads/writes and no LangCache use.
- Set a monthly operating budget and alerts for database storage, managed service usage, model calls, and backups after checking the selected account's pricing.

## 13. Source notes

Checked September 21, 2026. The architecture and policies above are application design decisions. These official sources establish the service roles, not automatic compatibility with every product requirement:

- [Redis Agent Memory overview](https://redis.io/docs/latest/develop/ai/context-engine/agent-memory/): session and long-term memory, automatic extraction, custom types, and provider-independent access.
- [Agent Memory on Redis Cloud](https://redis.io/docs/latest/operate/rc/context-engine/agent-memory/): managed service and configuration entry points.
- [Agent Memory model configuration](https://redis.io/docs/latest/operate/iris/agent-memory/model-configuration/): validate supported service-side model configuration during setup.
- [Context Retriever overview](https://redis.io/docs/latest/develop/ai/context-engine/context-retriever/): schema-defined entities/relationships and generated MCP retrieval tools over data in Redis.
- [Create a Context Retriever service](https://redis.io/docs/latest/operate/iris/context-retriever/create-service/): managed Cloud setup.
- [LangCache API and SDK](https://redis.io/docs/latest/develop/ai/context-engine/langcache/api-examples/): response search/storage, attribute filters, and deletion.

Backup guarantees, per-turn extraction completion, suppression of re-promotion, and complete mutation/provenance semantics remain explicit implementation verification items rather than assumed service capabilities.

Additional RedisVL references checked September 21, 2026:

- [RedisVL guides](https://docs.redisvl.com/en/latest/user_guide/index.html): schemas, index lifecycle, queries, and application patterns.
- [RedisVL extensions](https://redis.io/docs/latest/develop/ai/redisvl/concepts/extensions/): managed LangCacheSemanticCache versus Redis-backed SemanticCache, plus embedding caching.

Provider prerequisites:

- [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart): API key and server-side configuration for the first milestone.
- [Anthropic authentication](https://platform.claude.com/docs/en/manage-claude/authentication): direct API credentials for the second provider milestone.
- [Ollama quickstart](https://docs.ollama.com/quickstart): local runtime/model setup for the third provider milestone.

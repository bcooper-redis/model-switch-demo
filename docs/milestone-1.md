# Milestone 1 — durable chat and source-linked name recall

Implemented and validated September 21–22, 2026. Milestone 2 has not started.

## Delivered

- React/TypeScript chat UI served by FastAPI, with new conversations, durable
  history, explicit retries, processing status, and a memory evidence panel.
- One server-configured OpenAI model. Provider and model selection remain future
  work; secrets stay on the server.
- A separate worker delivers the durable outbox to managed Agent Memory,
  reconciles extracted memories, and projects verified records through RedisVL.
- Retrieval filters owner, generation, and active status before ranking, then
  checks canonical source records. Fresh chats use retrieved memory and their own
  history; no prior chat transcript or provider response chain is replayed.
- Reset changes the generation immediately, clears current chat and recall
  visibility, and schedules cleanup of only this application's retired sessions,
  memories, projections, and embedding caches.

## Storage and recovery

This small, single-user demo stores canonical conversations, jobs, and memories
in one Redis JSON string. Saving an answer and its outbox job is one atomic SET.
The user message is durable before provider generation starts. Stable request IDs
allow retries without duplicate application messages.

The API and worker serialize access with a local filesystem lock released by the
kernel on process exit. Run them on the same host and checkout with the provided
launcher. This is not a multi-host or large-history storage design.

The worker persists delivery intent before calling the managed service. If an
acknowledgment is lost, it checks application message IDs in managed event metadata
before retrying. An uncertain event that cannot be found is not blindly replayed.
Provider and recall failures remain visible; proceeding without recall requires
an explicit UI action.

Reset retains tombstones and periodically checks for late managed promotion.
Generation filtering protects current recall while remote cleanup is pending;
the UI reports cleanup status. This does not claim synchronous deletion across
all managed background work.

## Managed extraction and provenance limits

The configured service uses Redis-managed AI credentials, default extraction
cadence (approximately five minutes), a one-day short-term TTL, and a 365-day
long-term TTL. Automatic summarization starts at 20 messages and retains the most
recent 10 in full. The application database uses no eviction.

The current verifier accepts a simple managed name statement only when it matches
exactly one explicit user introduction in the same owner's source session. It
rejects assistant-only, hypothetical, compound, and ambiguous evidence. This is
an application verification step, not a replacement extractor. Names are not
hardcoded. Broader biography and preference extraction are outside this milestone.

Managed results expose source sessions, not native source-event attribution or
authoritative extraction completion. The UI labels attribution as verified by the
application. Empty polls remain pending; turns that produce no accepted name
memory may remain pending indefinitely rather than falsely claiming completion.

## Validation evidence

- 30 automated tests passed, covering contracts, evidence rejection, durable
  writes, idempotent retries, lost acknowledgments, failure recovery, explicit
  recall bypass, owner/generation isolation, reset, and API request protections.
- Production frontend build passed.
- Live isolated acceptance passed: unknown name → a synthetic test-name introduction → managed
  extraction → fresh-chat recall → duplicate request → scoped reset → unknown.
- Main demo passed: unknown name → Brian introduction → same-chat recall → fresh
  chat recall → API/worker restart → recall with one retrieved memory and only
  the current question in conversation history.
- On September 22, browser verification on port 8765 confirmed another new chat
  returned “Your name is Brian.” and source navigation opened the original
  “My name is Brian.” message. Port 8000 belongs to an unrelated Docker service;
  the launcher now defaults to 8765 and checks for conflicts.

Local evidence is in ignored `.artifacts/live-acceptance.json` and
`.artifacts/milestone1-main.json`. Run instructions are in the repository README.

No LangCache, additional providers, model picker, private mode, or production
deployment is included in this milestone.

# Milestone 3 — local generation with shared Redis memory

Implemented September 22, 2026. Milestone 4 has not started.

## Runtime and model

This Mac has Apple Silicon and 16 GB unified memory. The demo uses the official
Ollama 0.17.7 macOS CLI and Qwen3 4B Instruct (`qwen3:4b-instruct`, Q4_K_M,
approximately 2.5 GB download). Runtime and model files are in ignored
`.artifacts/`; Ollama also creates its standard local runtime files in `~/.ollama`.

Ollama 0.34.3's bundled inference process stalled during device discovery on this
machine. The verified 0.17.7 release runs with Metal acceleration. The generic
`qwen3:4b` tag currently selects a thinking model; the final default uses the
explicit instruction-tuned tag for concise demo answers. Both release downloads
were verified against the SHA256 digests published with their GitHub assets.

## Start and stop

In one terminal, from the repository root:

```sh
.venv/bin/python scripts/local_runtime.py serve
```

In another:

```sh
.venv/bin/python scripts/run.py
```

Open http://127.0.0.1:8765/ and select **Local · Ollama**. Start a new conversation
and ask “What's my name?” Existing Redis memory is shared with all three providers.
Ctrl-C in each terminal stops its corresponding service. The app launcher does
not start or stop Ollama. The loaded model expires after five idle minutes.

The runtime helper binds only `127.0.0.1:11434`, disables Ollama cloud features
with `OLLAMA_NO_CLOUD=1`, loads at most one model at a time, and uses an 8192-token
context. Logs from this installation are in `.artifacts/ollama-server.log`.

## Configuration

```dotenv
LOCAL_BASE_URL=http://127.0.0.1:11434
LOCAL_MODEL=qwen3:4b-instruct
LOCAL_MODELS=
```

No local API key is needed. Add comma-separated **downloaded** model tags to
`LOCAL_MODELS` for additional choices, then restart the application. Download a
model explicitly using `.venv/bin/python scripts/local_runtime.py pull MODEL`.
The application never downloads a model during chat. The model must support chat
and the adapter's non-thinking mode; the named default is the validated choice.

The provider selector exposes runtime reachability and whether the selected model
is downloaded. Generation errors preserve the saved turn and its exact selection;
retry after restarting Ollama or restoring the missing model. There is no cloud
fallback. Other provider choices remain usable in new conversations.

## Local execution evidence

A loopback URL alone does not prove local inference, since Ollama can proxy cloud
models. The adapter rejects remote endpoints, proxy environment settings,
redirects, cloud-tagged models, and model metadata describing a remote model.
It requires GGUF model metadata before generation and a matching loaded model
from `/api/ps` afterward. The persisted answer includes model digest, loaded
bytes, GPU bytes, generated tokens, and verification time. The UI shows
**Local execution verified** with the model digest available on hover.

The model receives the same source-linked memory fields and current-conversation
history as the cloud providers. Original source quotations are excluded from a
fresh chat. Reasoning blocks, when a model returns them inside answer content,
are removed before saving/displaying the answer. Incomplete responses are errors.

**Only answer generation is local.** Conversations and memories remain in Redis
Cloud; OpenAI still creates embeddings and Redis-managed AI extracts memories.
This milestone does not implement private mode or offline memory storage.

## Reinstall on macOS

The portable CLI is pinned to the validated release. Download and verify before
extracting into the directory expected by the helper:

```sh
curl -fL https://github.com/ollama/ollama/releases/download/v0.17.7/ollama-darwin.tgz -o .artifacts/ollama-stable.tgz
shasum -a 256 .artifacts/ollama-stable.tgz
```

Expected SHA256:
`a87a5d78825f91aee334020c868fba6c470da4e2bf21578d2ae1e36bb184ef35`.
After verifying it matches:

```sh
mkdir -p .artifacts/ollama-0.17.7
tar -xzf .artifacts/ollama-stable.tgz -C .artifacts/ollama-0.17.7
.venv/bin/python scripts/local_runtime.py serve
# In another terminal:
.venv/bin/python scripts/local_runtime.py pull qwen3:4b-instruct
```

## Validation

All 49 automated tests and the production frontend build pass. Live acceptance
with the final instruction-tuned model passed: unknown-name baseline, then
OpenAI → Claude → local → OpenAI, all reusing the same existing memory. The local
model reported 4,119,016,480 loaded bytes, all in GPU memory, and generated the
six-token answer “Your name is Brian.”

A live outage test stopped Ollama, confirmed a visible failure and exactly one
saved user turn, then restarted the runtime. The browser's retry completed that
same turn with local execution evidence and no duplicate user message. The UI
keeps the original provider/model selected for unfinished turns after reload.
The outage/recovery report is in `.artifacts/local-outage.json`.

The automated suite covers loopback enforcement, cloud-model rejection, local
execution evidence, incomplete answers, reasoning separation, runtime outages,
retry recovery, and no fallback, alongside the previous milestone checks.

Run the live proof with an existing Brian memory and both services running:

```sh
.venv/bin/python scripts/milestone3.py
```

It checks a local unknown-name baseline, then OpenAI → Claude → local → OpenAI in
fresh chats. All answers must use the same memory IDs with only one conversation
history message. Owner, generation, and canonical memories must be unchanged;
duplicate requests must return the same saved response. It adds test conversations
but does not reset data. Evidence is saved in ignored `.artifacts/milestone3.json`.

Broader personal memory support remains Milestone 4. Milestone 1's name-only
verification and pending-extraction limitations still apply.

References: [Ollama chat API](https://docs.ollama.com/api/chat),
[local/cloud configuration](https://docs.ollama.com/faq),
[loaded models API](https://docs.ollama.com/api/ps),
[Qwen model tags](https://ollama.com/library/qwen3/tags).

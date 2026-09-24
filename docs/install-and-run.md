# Install and run the Model Switch Demo

This guide is for Redis Solutions Architects (SAs). It takes you from a new checkout to a working demo, then shows how to present it.

The demo shows that a user's saved context can carry across answering models. Redis Cloud stores the data. Redis Agent Memory extracts facts from conversations. RedisVL retrieves approved facts before the selected model answers.

Start with OpenAI. Add Claude, local Ollama, and LangCache after the basic flow works. **Context Retriever is not yet integrated. Leave its settings blank.**

## 1. Before you start

| Item | What you need |
| --- | --- |
| Computer | macOS is the tested platform. Local inference was tested on Apple Silicon with 16 GB of memory. |
| Python | Python 3.12, installed through `uv` in the steps below. |
| JavaScript tools | Node.js 22.12 or later in the Node 22 release line, plus npm. |
| Other tools | Git, `uv`, a terminal, and a browser. |
| Network | Access to GitHub, package registries, your Redis database, Redis Agent Memory, and OpenAI. |
| Required services | A dedicated Redis Cloud application database, an Agent Memory service, and an OpenAI API key. |
| Optional services | Anthropic for Claude; Ollama for local answers; LangCache for the public-question cache demo. |

The app uses Unix file locking. Native Windows is not supported. Linux may work for the cloud-provider path, but it has not been validated here. The bundled Ollama setup below is for macOS only.

Use one app instance and one worker from the same checkout. The launcher starts both. Do not run two checkouts against the same demo namespace. Give each SA a separate database or namespace and separate service resources where possible.

This is a local, single-user demo without login controls. Keep it bound to localhost. It is not a shared customer service. Normal chats and uploaded facts can go to cloud services, even when Ollama generates the answer.

## 2. Install the tools and clone the project

Install Git, Node.js, and uv if they are missing. Use the [Git installers](https://git-scm.com/downloads), [Node.js downloads](https://nodejs.org/en/download), and [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/). Node's installer includes npm. The frontend uses Vite; see its [Node.js requirements](https://vite.dev/guide/).

Check your tools:

```sh
git --version
node --version
npm --version
uv --version
```

Clone the project into a folder where you keep demos:

```sh
git clone https://github.com/bcooper-redis/model-switch-demo.git
cd model-switch-demo
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.lock
```

Run the remaining commands from this `model-switch-demo` folder unless a step says otherwise. You do not need to activate the Python environment; the commands use its Python directly.

## 3. Set up Redis Cloud and Agent Memory

### Application database

Create a dedicated Redis Cloud database for the demo. It needs Redis Search with vector support, TLS, and the **noeviction** policy. The app creates its own search index. Do not create the index by hand.

Record the database hostname, port, username, and password. These are database credentials, not the Agent Memory service key. Your computer must be able to reach the database's TLS port.

Use a dedicated demo database rather than a production database. See [Create a Redis Cloud database](https://redis.io/docs/latest/operate/rc/databases/create-database/).

### Agent Memory service

In Redis Cloud, open **Agent Memory** and create a custom service. Select an eligible backing database and the default database user. Follow the console's eligibility checks; service support may differ from regular Redis database support.

Use these demo settings:

| Setting | Demo value |
| --- | --- |
| Extraction cadence | **60 seconds**, or **1 minute** if the console uses minutes |
| Short-term TTL | 1 day |
| Long-term TTL | 365 days |
| AI credentials | Redis-managed credentials |
| Automatic summarization | On |
| Summarize after | 20 messages |
| Keep most recent | 10 messages |
| Custom memory types | None required |

Copy the service's API base URL, store ID, and API key. Save the key when it is shown. Use these service values in the `AGENT_MEMORY_*` settings.

**Presenter timing:** the default extraction cadence is five minutes. Set it to 60 seconds for this demo. This controls how often extraction runs; it does not guarantee completion in exactly one minute. [Agent Memory setup and cadence](https://redis.io/docs/latest/operate/iris/agent-memory/create-service/)

## 4. Create your .env file

For a new checkout only:

```sh
cp .env.example .env
chmod 600 .env
```

Open `.env` in your text editor. Keep it in the project root, beside `README.md`. Do not repeat the copy command after adding credentials because it would overwrite them.

Fill in these required settings:

| Setting | Value to enter |
| --- | --- |
| `REDIS_HOST` | Database hostname only, with no scheme or port |
| `REDIS_PORT` | Database TLS port |
| `REDIS_USERNAME` | Database username, usually `default` for this demo |
| `REDIS_PASSWORD` | Database password |
| `REDIS_TLS` | `true` |
| `AGENT_MEMORY_BASE_URL` | HTTPS data-plane base URL from the service |
| `AGENT_MEMORY_STORE_ID` | Agent Memory store ID |
| `AGENT_MEMORY_API_KEY` | Agent Memory service key |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENAI_MODEL` | An answering model your account can use; this project has been tested with `gpt-5.4-mini` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `DEMO_NAMESPACE` | A stable, unique label, such as `model-switch-sa01` |

The namespace allows letters, numbers, and hyphens. Keep it unchanged between runs to keep using the same saved conversations. Changing it starts a separate set of app records; it does not delete the old data.

The search schema expects **1,536 dimensions**. Keep the embedding model above. Changing answering models is supported; changing embedding models on an existing index requires a separate migration.

Quote secrets with single quotes when needed. Never put credentials in frontend settings or variables beginning with `VITE_`. The app reads `.env` itself; you do not need to run `source .env`.

For the first run, leave Anthropic, LangCache, and Context Retriever credentials blank. Set `LOCAL_MODEL=` to leave Ollama disabled until you install it. Model names in the template are examples, not proof that your account has access. Remove any extra model IDs from the allowlists that you do not plan to use.

`.env`, runtime files, model downloads, and private upload/export folders are ignored by Git. Never commit keys or personal profiles.

## 5. Build and check the app

Build the browser UI:

```sh
cd frontend
npm ci
npm run build
cd ..
```

Run the automated tests:

```sh
.venv/bin/python -m pytest -q
```

The test suite requires the `.env` fields from step 4 to be present, even though the tests use test doubles for external services. Passing tests does not prove that your credentials work. At guide creation, all 67 tests passed.

Check the required live connections:

```sh
.venv/bin/python scripts/milestone0.py connect
```

This makes small OpenAI generation and embedding requests. It checks Redis connectivity, Agent Memory health, and OpenAI access. Look for Redis `ping: true`, `eviction_policy: noeviction`, a healthy memory service, and `dimensions: 1536`. Model calls may incur charges. Results are written to the ignored `.artifacts/connectivity.json` file.

This check does not test Claude, Ollama, LangCache, or background extraction. Test those through their demo steps below. You do not need to run the other Milestone 0 probe commands for installation.

## 6. Start, stop, and restart

Start the app and memory worker together:

```sh
.venv/bin/python scripts/run.py
```

Leave this terminal open. Look for `Memory worker started` and the Uvicorn startup message. Open **http://127.0.0.1:8765/**.

From a second terminal, you can check the page and API without printing conversation data:

```sh
curl -fsS -o /dev/null -w 'Page: %{http_code}\n' http://127.0.0.1:8765/
curl -fsS -o /dev/null -w 'API: %{http_code}\n' http://127.0.0.1:8765/api/state
```

Both should report `200`. A page response alone does not prove memory processing works; complete the name demo next.

Press **Ctrl+C** in the app terminal to stop both processes. Run the same start command to restart. Restart after editing `.env`. Refresh the browser after rebuilding the frontend. A normal restart keeps your saved Redis data.

If port 8765 is busy, stop your previous app instance first. To deliberately use another port:

```sh
DEMO_PORT=8766 .venv/bin/python scripts/run.py
```

Then open `http://127.0.0.1:8766/`. This port setting is passed in the shell, not read from `.env`.

## 7. Run the core memory demo

1. Start with an empty demo. If you have old data, use **Reset demo** only after exporting anything you need.
2. Select OpenAI. Ask **What's my name?** The model should say it does not know.
3. Send **My name is YOUR_FIRST_NAME**, replacing the placeholder with your name. State it once in a simple sentence.
4. Wait for the name fact under **Saved in Redis**. A successful chat reply does not mean extraction is done.
5. Select **New conversation**. Ask **What's my name?** again.
6. Inspect **Memories supplied**. The answer should show the saved name fact and its original source message.
7. Once Claude or Ollama is ready, start another new conversation, switch providers, and repeat the question.

Suggested narration: “Redis stores the conversation right away. Agent Memory extracts useful facts in the background. Once a fact is ready, another model can use it in a new conversation.”

A reply in the same conversation can use chat history. That is why it may know your name while showing **0 memories supplied**. The fresh conversation is the proof of saved-memory recall. Each answer keeps the memory count it had when generated; old answers do not update later.

Broader facts may appear under **Needs source review**. Confirm only facts supported by the original user message. Dismiss unrelated or incorrect candidates. A question with no useful fact may continue to show pending because the service does not expose a per-turn completion signal to this app.

## 8. Add Claude

Set these fields in `.env`:

```dotenv
ANTHROPIC_API_KEY='your-anthropic-key'
ANTHROPIC_MODEL=claude-sonnet-5
ANTHROPIC_WORKSPACE_ID=
ANTHROPIC_MODELS=claude-haiku-4-5-20251001
```

These model IDs were used during project validation. Use IDs available to your account. If your key requires a workspace ID, fill in `ANTHROPIC_WORKSPACE_ID` from your Anthropic setup. Do not use an OpenAI key here.

Restart the app, select Anthropic and a model, then run the fresh-conversation name test. OpenAI is still required for embeddings. The provider selector does not grant access to a model; it lists configured choices.

## 9. Add local Ollama on macOS

This path uses the project's tested Ollama 0.17.7 runtime. It downloads about 2.5 GB for the default model, plus runtime files. Allow extra disk space and time before presenting. Other platforms and runtime versions need separate validation.

First, make sure another Ollama server is not using port 11434. Quit the Ollama desktop app if it is serving that port.

Download the runtime from the project root:

```sh
mkdir -p .artifacts
curl -fL https://github.com/ollama/ollama/releases/download/v0.17.7/ollama-darwin.tgz -o .artifacts/ollama-stable.tgz
shasum -a 256 .artifacts/ollama-stable.tgz
```

The expected SHA256 for this pinned archive is:

```text
a87a5d78825f91aee334020c868fba6c470da4e2bf21578d2ae1e36bb184ef35
```

Stop if it differs. If it matches, extract and start the runtime:

```sh
mkdir -p .artifacts/ollama-0.17.7
tar -xzf .artifacts/ollama-stable.tgz -C .artifacts/ollama-0.17.7
.venv/bin/python scripts/local_runtime.py serve
```

Leave that terminal open. In a second terminal, change to the project root and download the model:

```sh
.venv/bin/python scripts/local_runtime.py pull qwen3:4b-instruct
.venv/bin/python scripts/local_runtime.py list
```

Set these fields in `.env`:

```dotenv
LOCAL_BASE_URL=http://127.0.0.1:11434
LOCAL_MODEL=qwen3:4b-instruct
LOCAL_MODELS=
```

Restart the app. Select **Local · Ollama** and run the fresh-conversation name test. The answer should show **Local execution verified**. Download the model before the demo; chat does not download missing models. The first answer may be slower while the model loads.

The app and Ollama run in separate terminals. Stop each with Ctrl+C. On later runs, start the Ollama server and app again; you do not need to download the model again.

Only answer generation is local. Redis Cloud still stores conversations and memories, OpenAI creates embeddings, and Redis-managed AI handles extraction. This is not an offline demo.

## 10. Add LangCache

Create a custom LangCache service for the public-question example. During creation, add these five attribute names exactly:

```text
task
prompt_version
provider
model
settings
```

**Add attributes before creating the service.** Existing services cannot add or change custom attributes. If they are missing, create a replacement service and update the credentials. [LangCache attribute limits](https://redis.io/docs/latest/operate/rc/context-engine/langcache/view-edit-cache/#attributes)

Fill in `.env` and restart:

```dotenv
LANGCACHE_BASE_URL='https://your-service-host'
LANGCACHE_CACHE_ID='your-cache-id'
LANGCACHE_API_KEY='your-service-key'
```

Copy the base URL from the service; do not append `/v1/caches/...`. See [LangCache creation instructions](https://redis.io/docs/latest/operate/rc/langcache/create-service/).

In the right panel, open **Non-personal cache example**:

1. Leave LangCache off and select **Run example**. Expect `bypassed` and a model call.
2. Turn it on and run the example. An empty cache should show `miss` and save the answer.
3. Keep the same provider and model, then run it again. Expect `hit` and zero generation time.
4. Try **Try paraphrase**. It may miss at the current strict match threshold. Do not promise a hit for every reworded question.

Existing entries may make the first enabled request a hit. Turning the switch off preserves entries. Entries written by this app have a one-hour TTL. The example uses a fixed question about the capital of France. Personal chats, private chats, and profile uploads bypass LangCache.

## 11. Demo a document upload

Prepare a UTF-8 `.txt` file with uppercase section headings and `- ` bullet lines. PDF and Word files are not supported. The maximum file size is 200 KB. This sample contains no named person:

```text
PROFESSIONAL INTERESTS
- You prefer practical examples when learning a technical topic.
WORK WITH AI
- You prefer short answers followed by a clear next step.
```

Choose **Upload context**. Review the proposed memories, edit wording if needed, and select individual facts, sections, or **Select all memories**. Check the review confirmation, then save.

Wait until the memories finish syncing before starting a fresh conversation with another model. Ask a question related to a saved fact and inspect its source passage.

Upload approval creates explicit memories; it does not wait for the chat extraction cycle. Sync and embedding work still take time. The preview alone does not save facts. No personal profile is bundled with this project.

## 12. Before and after a presentation

Before the demo, check the 60-second extraction setting, run a short provider test, and preload Ollama if needed. Choose whether to show an empty baseline or an existing profile. Do not reset a profile you plan to use later in the presentation.

Use **Export conversations & memories** to download data you want to keep. Export is not an automatic backup system, and the app has no full restore command. Store exports in the ignored `exports/` folder if you keep them in this checkout.

**Reset demo** clears this demo's app state and queues cleanup of its recorded managed memories and sessions. It does **not** run `FLUSHDB`. Keep the worker running while cleanup finishes. Reset does not flush the separate LangCache service.

## 13. Troubleshooting

| Symptom | What to check |
| --- | --- |
| `uv`, `node`, or `npm` not found | Install the tool and open a new terminal. Check the versions in step 2. |
| Python import or dependency error | Use `.venv/bin/python`, not system Python. Install from `requirements.lock` again. |
| `fcntl` error on Windows | Use the tested macOS path. Native Windows is unsupported. |
| Frontend build reports unsupported Node | Use Node 22.12 or later in the Node 22 release line. Run `npm ci` again. |
| App says to build the frontend | Run the build commands in step 5. |
| Missing setting | Fill the named field in the root `.env`; restart. Do not overwrite existing credentials with the template. |
| Redis connection or TLS error | Check hostname, port, password, TLS, network access, and database status. |
| Embedding dimensions do not match | Use `text-embedding-3-small`; do not change an existing index's embedding model casually. |
| Provider authentication or model error | Check the provider key, account access, exact model ID, and any required workspace ID. |
| Page works but memories stay pending | Check the worker terminal, Agent Memory credentials, and extraction cadence. Look for errors before retrying. Some turns produce no useful facts. |
| Fact is under Needs source review | Check its original user message and approve only if supported. It is not yet eligible for recall. |
| Answer knows a fact but shows zero memories | It may be using current chat history. Wait for Saved in Redis, then use a new conversation. |
| Port already in use | Stop your earlier instance. Do not start a second worker for the same namespace from another checkout. |
| Local runtime unavailable | Start Ollama separately. Confirm the configured model appears in `local_runtime.py list`. |
| Ollama fails to start under an automation sandbox | Run it in a normal macOS terminal so it can access the GPU. |
| LangCache reports an attribute error | Check all five names. A service created without them needs replacement. |
| LangCache paraphrase misses | Similarity must pass a strict threshold. Confirm an exact repeat hits first. |
| Upload file rejected | Use UTF-8 text, uppercase headings, and bullet lines. Keep it under 200 KB and each fact under 4,000 characters. |
| Profile import remains pending | Check the worker and cloud access. Failed syncs retry; pending facts are excluded from recall. |
| UI still shows the old version | Rebuild the frontend, then refresh the browser. |

When asking for help, include the step, error type, tool versions, and whether the problem affects one provider or all of them. Do not share `.env`, API keys, or unreviewed conversation exports.

## 14. Update an existing installation

Stop the app first. From the project root:

```sh
git pull --ff-only
uv pip install --python .venv/bin/python -r requirements.lock
cd frontend
npm ci
npm run build
cd ..
.venv/bin/python -m pytest -q
.venv/bin/python scripts/run.py
```

Compare `.env.example` with your settings for new fields, but keep your current `.env`. If Git reports local changes or a branch conflict, resolve that before updating; do not discard work to force the pull.

For normal daily use, you only need the start commands in step 6 and, if used, the Ollama server command in step 9. Rebuild only after frontend changes or an update.

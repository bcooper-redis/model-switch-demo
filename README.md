# Redis Model Switch Demo

Show how saved personal context carries across OpenAI, Claude, and a local Ollama model. Redis Cloud stores the conversations and memories. Redis Agent Memory extracts facts, and RedisVL retrieves approved facts for each answer.

**Start here: [Install and run guide for Redis SAs](docs/install-and-run.md).**

The guide covers required services, installation, `.env` settings, startup, the presenter flow, optional providers, document uploads, LangCache, and troubleshooting. macOS is the tested platform.

## What works today

- Switch answering providers and models while keeping the same saved context.
- Inspect the memories supplied to an answer and their source messages.
- Review, edit, and delete memories; export conversations and memories.
- Upload a text profile, select facts, and approve them before saving.
- Use private chat without app-side Redis storage or memory recall.
- Turn LangCache on or off for a fixed public-question example.

Context Retriever is not yet integrated. The app is a local, single-user demo, not a production service. Normal conversations and memories use cloud services even when Ollama generates the answer.

## Daily startup

After completing the install guide, run this from the project root:

```sh
.venv/bin/python scripts/run.py
```

Open **http://127.0.0.1:8765/**. This starts the API and memory worker. Press **Ctrl+C** to stop both. Restart after changing `.env`.

If using Ollama, also run this in a separate terminal from the project root:

```sh
.venv/bin/python scripts/local_runtime.py serve
```

Ollama must be installed and its model downloaded first. The app does not start Ollama for you.

## Presenter timing

Set Agent Memory's extraction cadence to **60 seconds** for demos. The default is five minutes. This is a processing interval, not a guaranteed completion time.

Wait for **Saved in Redis**, then open a **new conversation** and switch models to prove saved-memory recall. A model may know a fact from the current chat while showing **0 memories supplied**. See the [core demo steps](docs/install-and-run.md#7-run-the-core-memory-demo).

## Project references

- [Document import and source tracking](docs/document-import.md)
- [Current Milestone 4 implementation status](docs/milestone-4.md)
- [Product requirements](personal-memory-chatbot-prd.md)
- [Architecture and flow diagrams](redis-context-demo-diagrams.md)
- Historical validation reports: [Milestone 0](docs/milestone-0.md), [Milestone 1](docs/milestone-1.md), [Milestone 2](docs/milestone-2.md), [Milestone 3](docs/milestone-3.md)

Milestone reports describe the configuration and results at that point in development. Use the install guide for current setup steps. Keep `.env`, private profiles, and exports out of Git.

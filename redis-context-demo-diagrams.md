# Redis shared context demo — diagrams

Based on PRD v0.5. These diagrams describe the planned OpenAI-first implementation, not deployed infrastructure.

## 1. Architecture

Solid connections show the first milestone. Dashed connections show later additions. RedisVL is an application library; Agent Memory, Context Retriever, and LangCache are managed services.

```mermaid
flowchart TB
    user["Brian"] --> ui["Chat UI and memory evidence panel"]
    ui --> app["Python backend: shared context and provider adapters"]

    subgraph application["Application"]
        app --> retrieval["RedisVL: index and retrieve eligible memories"]
        app --> sync["Background delivery and memory reconciliation"]
    end

    subgraph redisCloud["Redis Cloud"]
        archive[("Conversation archive and durable delivery queue")]
        memory["Agent Memory: session events and fact extraction"]
        projection[("Source-linked memory projection")]
        contextRetriever["Later: Context Retriever"]
        langCache["Later: LangCache"]
    end

    app -->|"Save messages and delivery tasks"| archive
    archive -->|"Pending work"| sync
    sync -->|"Submit conversation events"| memory
    memory -->|"Extracted memories via supported API"| sync
    sync -->|"Validate sources and update through RedisVL"| projection
    retrieval <-->|"Filtered memory search"| projection
    retrieval -->|"Relevant facts and source IDs"| app

    app -->|"Question plus retrieved context"| openai["Stage 1: OpenAI API"]
    app -.-> claude["Stage 2: Anthropic API"]
    app -.-> localModel["Stage 3: local model runtime"]
    app -.->|"Structured entity retrieval"| contextRetriever
    contextRetriever -.->|"Read modeled application data"| projection
    app -.->|"RedisVL LangCache integration"| langCache
```

All answering providers return their generated answer to the backend, which saves it and displays it in the UI; response arrows are omitted for clarity. Provider keys remain server-side. Embedding configuration for the RedisVL projection is independent of the answering model; Agent Memory has its own managed processing configuration.

The name-recall demo bypasses LangCache. Context Retriever and LangCache are added after the three provider milestones. They are not prerequisites for the first working demonstration.

## 2. User flow

A fresh conversation retains the same opaque user identity but does not resend the original conversation or a provider-side conversation chain. This is what proves Redis-backed recall.

```mermaid
flowchart TB
    start["Select OpenAI; start with empty demo memory"]
    start --> baseline["Ask: What's my name?"]
    baseline --> unknown["Assistant: I don't know yet"]
    unknown --> introduce["Say: My name is Brian"]
    introduce --> save["Save source in Redis; Agent Memory extracts the fact"]
    save --> ready{"Source-linked memory ready?"}
    ready -->|"Pending or failed"| pending["Show status; wait or retry"]
    pending --> ready
    ready -->|"Yes"| same["Same model: What's my name?"]
    same --> sameRecall["RedisVL retrieves Brian; answer shows memory source"]
    sameRecall --> fresh["New conversation; same OpenAI model"]
    fresh --> question["Ask: What's my name?"]
    question --> redisRecall["Retrieve from Redis; do not replay original chat"]
    redisRecall --> answer["OpenAI: Your name is Brian"]
    answer --> restart["Restart app; repeat fresh-chat recall"]
    restart --> pass["Stage 1 complete: persisted memory proven"]
    pass -.-> claude["Stage 2: switch to Claude; new chat; ask the same question"]
    claude -.-> claudeAnswer["Claude retrieves the existing Redis memory: Brian"]
    claudeAnswer -.-> localModel["Stage 3: switch to local model; new chat; ask again"]
    localModel -.-> localAnswer["Local model retrieves the same Redis memory: Brian"]
```

The application must not seed Brian's name through account metadata, the user ID, or a hardcoded prompt. Before the memory exists, the baseline answer should not know the name. Every successful recall shows the actual retrieved memory and its source. Switching answering models does not require migrating memories or changing their embeddings.

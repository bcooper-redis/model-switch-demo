# Milestone 4 service setup

Credentials belong in the existing root `.env`, never in chat or frontend settings. Copy the new blank entries from `.env.example`; preserve your existing values. LangCache is wired only to the fixed example in the evidence panel; it becomes callable after credentials are added and the app is restarted. Context Retriever integration still needs implementation and live schema/access verification.

## LangCache

1. Open Redis Cloud → LangCache → create a service named `model-switch-demo-cache`. Use a dedicated cache for this demo.
2. Choose an eligible database and complete the embedding/provider settings offered by your account.
3. Add these five custom attributes, exactly: `task`, `prompt_version`, `provider`, `model`, `settings`.
4. Save the service API key when displayed. Copy the API base URL and cache ID from its configuration.
5. Populate:

```dotenv
LANGCACHE_BASE_URL='https://<service-host-from-console>'
LANGCACHE_CACHE_ID='<cache-id>'
LANGCACHE_API_KEY='<service-api-key>'
```

The intended cache demo uses only fixed, non-personal example tasks. Normal personal chats and private chats bypass it. Attribute scoping and a one-hour TTL will be validated before enabling cache reuse.

Official instructions: [Create a LangCache service](https://redis.io/docs/latest/operate/rc/langcache/create-service/), [API authentication and attributes](https://redis.io/docs/latest/develop/ai/context-engine/langcache/api-examples/).

## Context Retriever

1. Open Redis Cloud → Context Retriever → New service → Create custom service.
2. Name it `model-switch-demo-context` and select this demo's application database. Do not select the managed Agent Memory store. Flex and Active-Active databases are not currently supported by this preview.
3. Create a `Memory` entity with key template `model-switch-demo:app:memory:{id}` (replace `model-switch-demo` if your `DEMO_NAMESPACE` differs).
4. Manually define `id` as the string primary key; `text` as string/TEXT; `owner_id`, `generation`, `status`, and `category` as string/TAG; and `revision` as numeric. Do not expose the binary embedding field. This is the initial application projection; person relationships will be added with the integration.
5. Create the service. In Context Retriever → Admin keys, generate an admin key and save it immediately.
6. Copy the admin API URL, service/surface ID, and MCP URL supplied in the console's connection/get-started instructions:

```dotenv
CONTEXT_RETRIEVER_ADMIN_URL='https://<admin-api-base-url>'
CONTEXT_RETRIEVER_ADMIN_KEY='<admin-key>'
CONTEXT_RETRIEVER_SURFACE_ID='<surface-id>'
CONTEXT_RETRIEVER_MCP_URL='https://<mcp-url>'
CONTEXT_RETRIEVER_AGENT_KEY=
```

Leave the agent key blank initially. The app integration must first verify the live generated tool schemas and create/check an agent key with owner/generation access restrictions. Admin credentials must not be used for runtime retrieval. If console endpoint labels differ, share only the labels or non-secret instructions; do not guess a URL from the Redis endpoint.

Official instructions: [Create a Context Retriever service](https://redis.io/docs/latest/operate/iris/context-retriever/create-service/), [Admin keys](https://redis.io/docs/latest/operate/iris/context-retriever/view-admin-keys/), [official Python client](https://pypi.org/project/redis-context-retriever/).

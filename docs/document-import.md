# Document import

Use **Upload context** in the normal chat sidebar. Private chat has no upload control.

1. Choose a UTF-8 `.txt` profile (up to 200 KB). This version supports uppercase section headings and `- ` bullet passages, matching the supplied profile format. It does not parse PDF/Word or perform model-based extraction.
2. Expand sections to inspect the original source passages and line numbers. Professional sections and AI working preferences are selected initially; other sections are unchecked. Select or exclude sections or individual passages, or use **Select all memories** to include every proposed fact. Edit the memory wording and choose categories. Selecting all still requires the final review confirmation.
3. Compare with existing saved memories. Imports add records; they do not replace contradictory facts automatically. Exclude conflicting passages and correct existing memories first. Keep uncertainty and historical qualifiers unless explicitly correcting them.
4. Confirm review and select **Save approved memories**. The worker writes approved facts through the Agent Memory SDK and projects them through RedisVL. Failed operations retry automatically. Pending memories stay out of recall until managed sync is verified.
5. Start a fresh conversation with each answering provider. The memory panel's **View document passage** action shows filename, section, line, original passage, and document/section notes. Citations refer to the uploaded profile, not inaccessible earlier conversations named in that profile.

Preview performs no Redis, embedding, or model calls. The full text exists in the active page/local request during review. Approval saves only selected source passages, associated notes, file hash/name, and approved memory text. No personal file is bundled in this repository or imported automatically. Section/file notes retain date and uncertainty context.

The same normalized file content and passage produce stable IDs within the current demo generation. Retrying/re-uploading skips existing records, including edited/deleted ones; it does not overwrite corrections or resurrect deletions. Changed files have new hashes and require review; semantic deduplication across different documents is not implemented.

Import approval and its durable sync tasks are committed in one canonical state write. Source passage lineage is application-owned, explicitly confirmed by the user. No fake managed event ID or automatic extraction claim is created. This uses the supported explicit long-term memory creation API.

Export includes approved document passages and provenance. Deleting a memory retains its archived source passage, like deleting a memory retains its original conversation. Full demo reset removes local document sources and includes their managed session IDs in scoped cloud cleanup. Whole-document removal and entity/relationship extraction remain future work.

LangCache and Context Retriever are not called during import. Context Retriever relationships can later be modeled over approved context. Ordinary personal answers still bypass LangCache.

## Validation

- 67 automated tests and the frontend build passed.
- The supplied profile parsed locally as 11 sections / 106 passages / 27 initially selected. Its contents were not imported or sent to answering/embedding services during validation.
- Browser validation with a generic two-section file verified section defaults, original passage display, editable memory/category controls, and confirmation gating.
- `python -m scripts.document_acceptance` passed using an isolated generic fixture: explicit import → managed sync → RedisVL source-linked retrieval → fresh-chat recall with OpenAI, Anthropic, and local Ollama. The fixture and index were cleaned up. No original source transcript was replayed.

# Growth Memory as RAG — Research Findings

Branch: `research/growth-memory-rag` (pushed, not merged). Supersedes the earlier
plain-JSON `growthHistory[]`/`goals[]` growth-memory plan (see
`aio-df-2026-07-22-session-state` memory) — SwegOn asked specifically for a RAG-based
approach instead, researched and prototyped here.

## Why RAG instead of the additive-JSON approach

The original plan (`growthHistory[]`/`goals[]` appended to the existing memory.json,
injected via frequency-based pattern promotion) works but doesn't scale: every entry
gets loaded and reasoned about by the token-budget logic regardless of relevance to the
current conversation. A RAG approach only injects the entries semantically relevant to
what's being discussed right now, so the store can grow large (years of growth entries)
without blowing the prompt budget or making the agent re-read irrelevant history.

## What already existed in this repo

- `backend/packages/harness/pyproject.toml` already depends on `langchain>=1.2.15`,
  `langchain-openai>=1.2.1`, `langgraph>=1.1.9`, etc. — **no new dependency needed** for
  the core RAG building blocks (vector store, embeddings interface, document schema).
- No embeddings usage anywhere in the codebase before this branch (`grep -rn
  "embedding"` across `deerflow/` and `app/` was empty, and `config.example.yaml` has no
  embeddings section). This is genuinely new infra — see Open Questions.
- The existing `deerflow.agents.memory.storage.FileMemoryStorage` pattern (atomic
  temp-file+rename writes, per-user path via `Paths`, mtime-cached reads) was the model
  to mirror for the new storage, but simplified — this module skips the pluggable
  storage-class config and cache layer since it's a research prototype, not a
  replacement for the main memory system yet.

## What was prototyped

New module: `backend/packages/harness/deerflow/agents/growth_memory/`

- **`storage.py`** — append-only per-user entries (`id`, `text`, `kind`, `createdAt`,
  `metadata`), one JSON file per user (`Paths.user_growth_memory_file`, added alongside
  the existing `user_memory_file`), atomic write via temp-file+rename. `load_entries` /
  `append_entry`, no caching layer (kept simple — add if profiling ever shows it's
  needed).
- **`retrieval.py`** — `retrieve_relevant_entries(user_id, query, embeddings, k=5)`
  builds a fresh `langchain_core.vectorstores.InMemoryVectorStore` from that user's
  entries on every call and returns the top-k `Document`s by similarity.
  `render_growth_memory_block(entries)` formats retrieved entries into a
  prompt-injectable text block (mirrors the shape of other `<soul>`-adjacent prompt
  blocks in this codebase).
- `embeddings` is a **required parameter**, not defaulted — see Open Questions below.

Tests: `backend/tests/test_growth_memory_rag.py`, using
`langchain_core.embeddings.DeterministicFakeEmbedding` (ships with `langchain-core`,
already installed) so the whole round-trip (append → embed → retrieve → render) is
tested with zero network calls and zero new dependencies. 8 tests, all passing. Full
backend suite: 5252 passed, 18 skipped (pre-existing skips, unrelated to this change).
`ruff check` / `ruff format --check` both clean.

`InMemoryVectorStore` rebuilding the index from scratch on every retrieval call is
intentional for the prototype (no state to manage, correctness over throughput) and
fine at the scale a single user's growth entries will realistically reach (hundreds,
not millions) — a persistent/indexed store is a later optimization, not a blocker.

## Open questions (need SwegOn's decision before this becomes a full implementation plan)

1. **Embeddings provider.** Nothing in this repo currently calls an embeddings API. The
   two realistic options:
   - Use whichever chat-model provider is already configured (OpenAI/Anthropic-style
     key) via `langchain-openai`'s `OpenAIEmbeddings` or equivalent — reuses an existing
     API key, adds one network call per query/append.
   - A local/offline embeddings model (e.g. `sentence-transformers`) — no network
     dependency or per-call cost, but is a new dependency and needs a model download at
     setup time.
   This needs a decision because it changes `config.yaml` schema (a new `embeddings:`
   section, mirroring how `models:` is configured) and `backend/pyproject.toml`.
2. **Where entries come from.** This branch only proves storage + retrieval work; it
   does not wire anything into the agent's memory-update pipeline
   (`deerflow/agents/memory/updater.py`) or the `<soul>` prompt injection point
   (`get_agent_soul` in `lead_agent/prompt.py`). Growth-memory entries need a source:
   auto-extracted by the existing memory-update LLM pass (like `facts[]` today), or a
   dedicated tool/flow the agent calls explicitly when it notices a growth moment.
3. **Retrieval trigger + budget.** When does retrieval run (every turn vs. only when the
   agent decides growth context is relevant), and how many entries/tokens get injected —
   mirrors the existing memory system's token-budget question but wasn't scoped here.

## Next step if SwegOn wants to proceed

Once (1)-(3) above are decided, this becomes a normal TDD implementation plan: wire
`retrieve_relevant_entries` into the `<soul>` prompt block, add the chosen embeddings
provider to config, and give the agent (or the memory-updater) a way to call
`append_entry`. Not started here — this branch is research + a working, tested
prototype of the storage/retrieval core only.

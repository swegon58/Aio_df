# Configuration System

Split out of `backend/CLAUDE.md` (source of truth for agent runtime architecture).

## Main Configuration (`config.yaml`)

Setup: Copy `config.example.yaml` to `config.yaml` in the **project root** directory.

**Config Versioning**: `config.example.yaml` has a `config_version` field. On startup, `AppConfig.from_file()` compares user version vs example version and emits a warning if outdated. Missing `config_version` = version 0. Run `make config-upgrade` to auto-merge missing fields. When changing the config schema, bump `config_version` in `config.example.yaml`.

**Config Caching**: `get_app_config()` caches the parsed config, but automatically reloads it when the resolved config path or file content signature changes. The signature includes file metadata and a content digest, so Gateway and LangGraph reads stay aligned with `config.yaml` edits even on object-store or network mounts where mtime can remain stale.

**Config Hot-Reload Boundary**: Gateway dependencies route through `get_app_config()` on every request, so per-run fields like `models[*].max_tokens`, `summarization.*`, `title.*`, `memory.*`, `subagents.*`, `tools[*]`, and the agent system prompt pick up `config.yaml` edits on the next message. `AppConfig` is intentionally **not** cached on `app.state` — `lifespan()` keeps a local `startup_config` variable for one-shot bootstrap work and passes it to `langgraph_runtime(app, startup_config)`.

Infrastructure fields are **restart-required**. The authoritative list lives in `packages/harness/deerflow/config/reload_boundary.py::STARTUP_ONLY_FIELDS` and is mirrored by the standardised `"startup-only:"` prefix on the corresponding `Field(description=...)` in `AppConfig`, so IDE hover on those fields surfaces the reason inline (no need to context-switch into this table). Currently registered: `database`, `checkpointer`, `run_events`, `stream_bridge`, `sandbox`, `log_level`, `channels`, `channel_connections`. Adding a new restart-required field requires updating the registry; drift is pinned by `tests/test_reload_boundary.py`.

Configuration priority:
1. Explicit `config_path` argument
2. `DEER_FLOW_CONFIG_PATH` environment variable
3. `config.yaml` in current directory (backend/)
4. `config.yaml` in parent directory (project root - **recommended location**)

Config values starting with `$` are resolved as environment variables (e.g., `$OPENAI_API_KEY`).
`ModelConfig` also declares `use_responses_api` and `output_version` so OpenAI `/v1/responses` can be enabled explicitly while still using `langchain_openai:ChatOpenAI`.

## Extensions Configuration (`extensions_config.json`)

MCP servers and skills are configured together in `extensions_config.json` in project root:

Configuration priority:
1. Explicit `config_path` argument
2. `DEER_FLOW_EXTENSIONS_CONFIG_PATH` environment variable
3. `extensions_config.json` in current directory (backend/)
4. `extensions_config.json` in parent directory (project root - **recommended location**)

## Config Schema

**`config.yaml`** key sections:
- `models[]` - LLM configs with `use` class path, `supports_thinking`, `supports_vision`, provider-specific fields
- vLLM reasoning models should use `deerflow.models.vllm_provider:VllmChatModel`; for Qwen-style parsers prefer `when_thinking_enabled.extra_body.chat_template_kwargs.enable_thinking`, and DeerFlow will also normalize the older `thinking` alias
- `tools[]` - Tool configs with `use` variable path and `group`
- `tool_groups[]` - Logical groupings for tools
- `sandbox.use` - Sandbox provider class path
- `skills.path` / `skills.container_path` - Host and container paths to skills directory
- `title` - Auto-title generation (enabled, max_words, max_chars, prompt_template)
- `summarization` - Context summarization (enabled, trigger conditions, keep policy)
- `subagents.enabled` - Master switch for subagent delegation
- `memory` - Memory system (enabled, storage_path, debounce_seconds, model_name, max_facts, fact_confidence_threshold, injection_enabled, max_injection_tokens)
- `usage_limits` - Per-user Energy credits + run rate limiting (see below)

### `usage_limits` — per-user Energy credits + rate limiting

Admin-managed via `config.yaml` only (no admin API/UI); hot-reloadable. Two independent systems gated by `usage_limits.enabled`:

- **Energy credits** (`usage_limits.credits`) — a per-user balance that drains with real (weighted) token usage and regenerates continuously. Enforced at three layers: a pre-run gate (`app/gateway/services.py::start_run` → 429), an in-run `CreditBudgetMiddleware` (`deerflow/agents/middlewares/credit_budget_middleware.py`, hard-stops a run overrunning the balance by forcing a graceful final answer), and post-run settlement in the worker's `finally` (`deerflow/runtime/runs/worker.py`).
- **Rate limiting** (`usage_limits.rate_limit`) — per-user sliding-window run caps evaluated by a `COUNT` over the `runs` table (no extra infrastructure).

"Energy" is a **display unit only**: `energy = weighted_tokens / tokens_per_unit`. Internally the balance is stored in weighted token-equivalents (`user_credits` table), with an append-only `credit_events` ledger whose `UNIQUE(run_id)` partial index makes settlement idempotent. Regeneration is computed lazily (no cron): `balance = min(max, balance + rate × elapsed)`, materialized on each write and previewed on reads. Overrides per user are keyed by email; admins and unauthenticated/`default` users are exempt. Core logic: `deerflow/runtime/usage/` (`conversion.py`, `service.py`) + `deerflow/persistence/usage/`. Read-model: `GET /api/usage` (`app/gateway/routers/usage.py`). Config schema: `deerflow/config/usage_limits_config.py`. Schema/migration: `0003_usage_credits`.

**`extensions_config.json`**:
- `mcpServers` - Map of server name → config (enabled, type, command, args, env, url, headers, oauth, description)
- `skills` - Map of skill name → state (enabled)

Both can be modified at runtime via Gateway API endpoints or `DeerFlowClient` methods.

See also: [../CONFIGURATION.md](../CONFIGURATION.md) for the user-facing configuration guide.

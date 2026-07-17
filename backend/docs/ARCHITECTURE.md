# Architecture

**This document is stale** — it predates the current 26-item lead-agent middleware chain (it showed an old 8-step chain) and other subsystem changes since. Authoritative architecture docs now live under [architecture/](architecture/), split by subsystem and kept in sync with `backend/CLAUDE.md`:

| Doc | Covers |
|-----|--------|
| [architecture/agent-runtime.md](architecture/agent-runtime.md) | Harness/App split, Agent System, full middleware chain, Subagent System |
| [architecture/configuration.md](architecture/configuration.md) | Config System, hot-reload boundary, Config Schema |
| [architecture/gateway-api.md](architecture/gateway-api.md) | Gateway routers, RunManager/RunStore |
| [architecture/sandbox-tools-mcp-skills.md](architecture/sandbox-tools-mcp-skills.md) | Sandbox, Tool System, MCP, Skills |
| [architecture/models.md](architecture/models.md) | Model Factory, vLLM Provider |
| [architecture/memory-system.md](architecture/memory-system.md) | Memory System |
| [architecture/im-channels.md](architecture/im-channels.md) | IM Channels System |
| [architecture/infra.md](architecture/infra.md) | Reflection, Schema Migrations, TUI, Tracing |
| [architecture/embedded-client.md](architecture/embedded-client.md) | Embedded `DeerFlowClient` |

See `backend/CLAUDE.md` → `## Architecture` for the short index version of the same map.

---
name: aio-df-mode-model-override
description: Aio_df chat modes (flash/thinking/pro/ultra) have no built-in model binding — model_name is fully independent of mode unless mode_model_overrides is set
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ff4e9b63-a33f-439d-88ba-7fe0971ae21c
  modified: 2026-07-22T16:08:20.720Z
---

Chat "mode" (`flashMode`/`reasoningMode`/`proMode`/`ultraMode`, UI-labelled
e.g. "Aio Pro") only ever controlled `thinking_enabled` / `is_plan_mode` /
`subagent_enabled` / `reasoning_effort` — it never selected which model runs.
Model selection was purely `model_name` (explicit per-request/per-thread
override, from a separate model picker) → custom agent's configured model →
`config.yaml` `models[0]` (global default) — see
`_resolve_model_name`/`_make_lead_agent` in
`backend/packages/harness/deerflow/agents/lead_agent/agent.py`.

**Fixed 2026-07-22**: added `mode_model_overrides: dict[str,str]` to
`AppConfig` (`backend/packages/harness/deerflow/config/app_config.py`),
settable in `config.yaml` (e.g. `mode_model_overrides: {pro: glm-4.7}`).
Resolution order is now: explicit `model_name` → agent config model → mode
override → global default (`models[0]`). Only applies when nothing more
specific was already requested.

**Why this matters**: if a future request is "make mode X use model Y",
don't assume it's a one-line config change — check whether
`mode_model_overrides` already covers it (it should, post-2026-07-22) rather
than re-deriving the whole mode→model resolution chain from scratch. Also:
changing `config.yaml`'s `models[0]` entry changes the default for **every**
mode, not just one — don't reach for that when the ask is mode-scoped
(learned the hard way: first pass wrongly reordered `models[0]` to satisfy a
"just for Aio Pro" request, user corrected — "đã nói chỉ mỗi aio pro thôi
mà").

**How to apply**: for any "swap model for mode X" request, edit
`config.yaml`'s `mode_model_overrides` map (or add the field if a stale
memory says it doesn't exist yet — verify by grepping
`mode_model_overrides` in `app_config.py` first). Don't touch `models[0]`
default ordering for a mode-scoped ask.

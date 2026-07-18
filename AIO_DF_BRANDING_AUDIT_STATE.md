# DeerFlow-branding audit — session state (2026-07-17/18)

Scope: Discord item 1 only ("report → preview panel" verification lane).
Branch: `fix/skill-deerflow-branding` (off `feat/live-terminal-preview`, which
still carries pre-existing Phase-1 uncommitted changes). **Nothing committed
yet** — only commit when owner explicitly asks.

## Done

1. **Skill-file branding sweep — complete.** Fixed 5 hardcoded "deerflow"/
   "deer" strings:
   - Deleted `skills/public/claude-to-deerflow/` (self-referential, wrong in
     Aio's own deployment).
   - `podcast-generation/SKILL.md`: removed "Hello Deer!" forced greeting
     (5 spots) → generic welcome-back greeting.
   - `systematic-literature-review/SKILL.md`: "DeerFlow runtime" /
     "DeerFlow users" → "Aio runtime" / "Aio users".
   - `github-deep-research/assets/report_template.md` line 189: report
     footer "...by DeerFlow" → "...by Aio" (user-facing report leak).
   - `systematic-literature-review/scripts/arxiv_search.py` line 81:
     User-Agent string `deerflow-slr-skill/0.1` → `aio-slr-skill/0.1`.
   - Left `find-skills/scripts/install-skill.sh`'s `deer-flow.code-workspace`
     marker-file check untouched (real file still exists at repo root,
     functional, not user-output-facing).

2. **File-type preview verification — complete, no bugs.** Tested
   notes.txt/data.csv/config.json/script.py/page.html in the live
   workspace UI. script.py Code tab: pass. page.html Code tab: pass.
   page.html Preview tab: pass (renders real HTML, not raw markup).
   Non-bug note: asking for 2 files in one message only created the first;
   needed a follow-up turn for the second — flagged, not fixed, out of scope.

## Open — the real finding

While testing config.json (unrelated to research/deerflow), the LLM
**spontaneously invented** `"app_name": "Deerflow Analytics"` — a leak
deeper than any skill file, since config.json isn't skill-triggered content.

- Hypothesis 1 (citation example URL `bytedance/deer-flow` at
  `prompt.py:565`, injected into every system prompt): fixed, gateway
  restarted, **retested live — leak still present** (`"Deerflow Analytics"`
  again in a fresh chat). Hypothesis disproven / insufficient.
- Hypothesis 2 (`agent_name` template var defaulting wrong): ruled out —
  confirmed `agent_name=agent_name or "Aio"` at `prompt.py:846`, correctly
  defaults to "Aio".
- **RESOLVED.** Background subagent's exhaustive sweep found no further
  "deer" string reachable on the default-agent path (SOUL.md/USER.md don't
  exist → return None; skill descriptions clean; all `@tool` docstrings in
  `tools/builtins/` clean except one). Two fixes landed:
  - `setup_agent_tool.py:23` docstring `"Setup the custom DeerFlow agent."`
    → `"Setup the custom agent."` (real leak, but only on the bootstrap/
    custom-agent path, not the one that reproduced the bug — fixed anyway).
  - `prompt.py:366-368` `<role>` block: added explicit negative guardrail —
    "When inventing example or placeholder content ... never use
    'DeerFlow'/'Deerflow' or 'deer' branding — invent something generic and
    unrelated instead." Conclusion: the leak is the local model's own
    pretrained association (bytedance/deer-flow is public GitHub content),
    not literally copied from Aio's prompt — the model's own casing
    ("Deerflow", single cap) diverged from the codebase's casing, consistent
    with free invention. Not fixable by removing more prompt text; needed
    an explicit negative instruction instead.
  - Gateway was restarted by the subagent to pick up the fix.
- **Live-retested by coordinator after subagent reported back**: fresh chat,
  generic `billing-config.json` request (SaaS invoicing placeholder config,
  no research/deerflow context) → produced `"app_name": "InvoiceFlow"`,
  zero "deer" branding. **`[live-verified]` — leak fixed.**

## Status: audit + fix + file-type verification all done, [live-verified]

Nothing technical left open on item 1's branding side-quest. Remaining
steps are process only:

1. Report finding + fix status to Discord (chat_id `1519020450322317362`)
   — done same session this file was last edited.
2. Decide with owner whether/when to commit `fix/skill-deerflow-branding`
   (8 files changed: 6 branding fixes/deletion + setup_agent_tool.py +
   prompt.py guardrail, all uncommitted per git-safety norms — only commit
   when owner explicitly asks).
3. Item 1 (report render → preview panel, not live dashboard) is
   `[live-verified]` and complete, including this branding side-quest and
   the 5-file-type preview sweep (script.py/page.html preview confirmed
   working, no bugs). Owner's final approval on item 1 is still the gate
   before items 2-5 can start (see task list: items 2-5 explicitly BLOCKED).

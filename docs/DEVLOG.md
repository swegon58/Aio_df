# DEVLOG

Lean progress log — one line per completed unit of work, newest first. Format and
compression rule: [`docs/superpowers/specs/2026-07-23-devlog-process-design.md`](superpowers/specs/2026-07-23-devlog-process-design.md).

## Shipped

- 2026-07-23 — added DEVLOG process itself [spec](superpowers/specs/2026-07-23-devlog-process-design.md)
- 2026-07-22 — Personality settings page + first-run onboarding wizard [plan](superpowers/plans/2026-07-22-personality-identity-wizard.md)
- 2026-06-13 — DeerFlow TUI (`deerflow` terminal workbench) [spec](superpowers/specs/2026-06-13-deerflow-tui.md)

## Backlog (pending/deferred — do not compress the linked doc until actually shipped)

- Event-store-backed `/history` — designed but not adopted; `get_thread_history` still reads checkpoint state, live `FIXME` for limit=1000 duration gap. [plan](superpowers/plans/2026-04-10-event-store-history.md) / [eval](superpowers/specs/2026-04-11-runjournal-history-evaluation.md)
- Summarize marker in history UI — design approved, implementation deferred, never built. [spec](superpowers/specs/2026-04-11-summarize-marker-design.md)

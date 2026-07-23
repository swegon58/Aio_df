# DEVLOG Process — Lean Per-Commit Progress Log

**Date**: 2026-07-23
**Status**: Approved, implemented same session

## Problem

`docs/superpowers/plans/` and `docs/superpowers/specs/` accumulate full step-by-step
plan/spec docs forever, even after the work ships. Example found while designing this:
`2026-07-22-personality-identity-wizard.md` sat at 1711 lines / 60 unchecked checkboxes
after all 5 of its commits had already landed — nobody had gone back to close it out, so
it silently looked unfinished. There was no single place to see "what shipped recently"
without reading `git log`.

## Design

**Index file**: `docs/DEVLOG.md`, newest entry on top. One line per completed unit of
work:

```
- YYYY-MM-DD — what shipped, ≤15 words [link to plan/spec if one exists]
```

**Trigger**: written as part of the final commit of a unit of work (a feature or fix
that's actually done), not every raw commit — avoids noise from WIP/typo commits.

**Compression rule** (the "don't get heavy" requirement): when a plan/spec doc's
described work is confirmed fully shipped, the doc is compressed in place — the
step-by-step body is replaced with a short block:

```
**Status**: Shipped YYYY-MM-DD, commits <first>..<last>
**Outcome**: 2-3 sentence summary of what actually shipped.
```

Full history is not lost — it's still recoverable via `git log -p` on the file — this
only declutters the working-tree view of the doc.

**Non-done docs are never compressed.** A plan/spec whose work is still pending,
deferred, or blocked stays at full detail (a partial doc is exactly the thing someone
needs full context to finish or evaluate later). Instead it gets a one-line backlog
pointer added to `DEVLOG.md` so it can't silently rot forgotten the way the wizard plan
did. This session found two genuine backlog items this way:
[`2026-04-10-event-store-history.md`](../plans/2026-04-10-event-store-history.md)
(designed architecture not actually adopted in code — `get_thread_history` still reads
from checkpoint state, with a live `# FIXME` for the same limit=1000 gap called out in
[`2026-04-11-runjournal-history-evaluation.md`](../specs/2026-04-11-runjournal-history-evaluation.md))
and
[`2026-04-11-summarize-marker-design.md`](../specs/2026-04-11-summarize-marker-design.md)
(explicitly "deferred to a follow-up PR", never built).

## Why not alternatives

- **Reuse `CHANGELOG.md`'s `[Unreleased]` section** — rejected by user preference (option
  A over B): `CHANGELOG.md` is release-cadence and Keep-a-Changelog formatted, which is
  heavier than a one-line-per-shipped-thing log and would force every entry through
  release categorization it doesn't need yet.
- **Archive folder for finished plans/specs** — rejected as unnecessary; in-place
  compression is simpler and git history already serves as the archive.

## Out of scope

- No tooling/automation (git hook, CI check) enforcing the DEVLOG entry or the
  compression — this is a documentation convention, not an enforced process, matching
  the scope actually requested.

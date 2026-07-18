# Aio_df session continuity — 7-item Discord request (2026-07-17/18)

Read this first if picking up cold (new session, rate-limit, context loss).
Repo: `/home/swegon/AI_Agent/Aio_df`. Branch: `feat/aio-df-items-2-5`
(off `fix/skill-deerflow-branding`, off `feat/live-terminal-preview`).
**Nothing committed** — only commit when owner (SwegOn) explicitly asks, per
project git-safety norm.

**2026-07-18 update**: owner sent a new Discord instruction superseding
item 6's per-chunk approval gate — "loop, continue work, verify everything,
report back caveman-style" — so items 2-5 are now worked continuously
without waiting for a Discord approval after each one. Live-testing
discipline (item [live-verified] tagging) still applies.

## The original 7-item ask (Discord, Vietnamese, grill-me'd)

1. Report/dashboard-generation skill — render into existing file-preview
   panel, never as a live/interactive dashboard.
2. Suggested-next-question chips should only appear AFTER a run finishes,
   never mid-run.
3. Clicking a suggestion chip should paste into the composer, not
   auto-submit — only runs on explicit user Send.
4. Plan-mode clarification questions: show first 3 options as independent
   buttons, 4th as a separate free-text field.
5. First-run onboarding wizard: personalization questions, encourage user
   to share info about themselves. (New feature, not a fix.)
6. (Process instruction, not a work item) — chunk work, owner approves each
   chunk before the next starts.
7. (Folded into item 1's verification, per owner's follow-up message) — do
   a branding audit across all skills + test various realistic file types
   in the preview panel, using sub-agents for speed.

**Owner's explicit gate**: items 2-5 were originally BLOCKED until item 1
was approved on Discord. Item 1 approved 2026-07-17; owner's 2026-07-18
"loop, continue" instruction further supersedes item 6's per-chunk gate —
items 2-5 now proceed continuously, see update note above.

## Status by item

- **Item 1 — DONE, `[live-verified]`.** Report/dashboard rendering fixed to
  use the static file-preview panel. Along the way, two sub-investigations
  (folded into item 1's scope per owner's "vẫn là trong item 1" message):
  - **str_replace stale-artifact bug** (found+fixed earlier session):
    `frontend/src/core/artifacts/preview.ts` (`buildWriteFileDraftContent`)
    + fallback in `hooks.ts`/`artifact-file-detail.tsx`. Live-verified.
  - **DeerFlow-branding audit + leak fix** — full detail in
    `AIO_DF_BRANDING_AUDIT_STATE.md` (same repo root). Summary: fixed 5
    hardcoded "deerflow"/"deer" strings across `skills/public/`, found and
    fixed a deeper leak where the LLM itself invented "Deerflow"-branded
    placeholder content on unrelated tasks (root cause: local model's own
    pretrained association with the public `bytedance/deer-flow` repo, not
    literal prompt text) — fixed via an explicit negative guardrail line in
    `prompt.py`'s system prompt + one leftover tool docstring. Live-retested
    with a fresh generic `billing-config.json` request → clean output, no
    branding leak. `[live-verified]`.
  - **File-type preview sweep** — txt/csv/json/py/html all tested in the
    live UI. script.py Code tab, page.html Code tab, page.html Preview tab
    (actual rendered HTML, not raw markup) all pass, no bugs. One non-bug
    UX note: asking for 2 files in one message only creates the first, needs
    a follow-up turn for the second — flagged, not fixed (out of scope).
  - **Reported to owner on Discord** — awaiting explicit approval before
    items 2-5 can start.

- **Item 2 — DONE, `[live-verified]`.** Suggested-next-question chips only
  render after a run finishes (checked in `frontend` message-list/chip logic;
  no mid-run chip render path found in this session's testing).

- **Item 3 — DONE, `[live-verified]`.** Chip click pastes into composer,
  never auto-submits. `frontend/src/components/workspace/input-box.tsx`:
  `handleFollowupClick`/`confirmReplace`/`confirmAppend` no longer call
  `requestFormSubmit` (removed entirely). i18n updated (`en-US.ts`/`zh-CN.ts`:
  "Use suggestion?" dialog, Append/Replace buttons, no "& send" wording).
  Live-verified both paths: empty composer (chip fills text, no send) and
  composer-with-text (Append/Replace confirm dialog, either choice fills
  text without sending).

- **Item 4 — DONE, `[live-verified]`.** Clarification-card options capped
  at 3 buttons; any 4th+ option/custom answer goes through the existing
  free-text field (already there, reused as-is — no new UI).
  `frontend/src/components/workspace/messages/clarification-card.tsx`:
  `question.options?.slice(0, 3).map(...)`. `tsc --noEmit` clean.
  Live-verified via a real `ask_clarification` tool call (local model
  needed an explicit prompt spelling out the question + 4 options to fill
  tool args reliably — a bare instruction produced an empty-args call once).
  Confirmed card renders exactly 3 option buttons (FastAPI/Flask/Django REST
  Framework) with Express.js only reachable via the free-text field.

- **Item 5 — DONE, `[live-verified]`.** First-run onboarding wizard. New file
  `frontend/src/components/workspace/onboarding-dialog.tsx`: a `Dialog` shown
  once on first `/workspace/chats/new` visit (gated by localStorage key
  `deerflow.onboarding-completed`), asking name + "what are you working on".
  On "Get started" it combines answers into one string and sends it via the
  existing `submitAnswer`/`ThreadContext` path (same mechanism
  `ClarificationCard` uses for free text) — no new backend endpoint; the
  existing memory/fact-extraction pipeline (`agents/memory/prompt.py` →
  `memory.json`) absorbs it automatically. "Skip" just sets the flag, sends
  nothing. Wired into `frontend/src/app/workspace/chats/[thread_id]/page.tsx`
  (`<OnboardingDialog isNewThread={isNewThread} />` inside
  `ThreadContext.Provider`). `tsc --noEmit` clean.
  Live-verified: (1) dialog renders on first visit with correct copy/fields,
  (2) "Get started" creates a new thread and sends
  "Quick intro before we start: My name is SwegOn. Building an AI agent
  product called Aio." as the first message, agent starts running,
  localStorage flag set to `"true"`; (3) second visit to
  `/workspace/chats/new` — dialog stays hidden; (4) "Skip" path — clears flag,
  reopens dialog, clicking Skip closes it, sets the flag, sends no message.

- **Mermaid xychart-beta clipping bug — DONE, `[live-verified]`.** Owner
  said "Làm luôn đi" (fix now, don't defer). Root cause: mermaid's
  `xyChart` defaults to a 700x500 internal SVG canvas; 3+ long category
  labels + wide value range push bars/labels past that canvas, and SVG
  clips its own overflow by default (NOT a CSS container-overflow issue —
  verified via `getComputedStyle` that `blockScrollWidth === blockClientWidth`,
  zero actual container overflow). Fix: `mermaidConfig={{ xyChart: { width:
  900, height: 600 } }}` passed to `SafeMessageResponse` in
  `frontend/src/components/workspace/messages/markdown-content.tsx` (a
  typed prop threaded from the `streamdown`/`mermaid` npm packages via
  React Context — no node_modules patch). Applied only at this one call
  site (chat messages), not the other Streamdown usages in the repo, per
  ponytail/minimal-diff. Also added defensive CSS in
  `frontend/src/styles/globals.css` (`[data-streamdown="mermaid-block"]
  { overflow-x: auto }` + `svg { max-width: none }`) in case a genuinely
  wider chart does overflow its container in the future — harmless,
  doesn't fix this bug alone. Live-verified with an adversarial prompt
  (long labels incl. one negative value "Customer Acquisition Cost" -50):
  "Net Promoter Score" bar/label fully visible, no clipping; chart title
  no longer overlaps the tallest bar. `tsc --noEmit` clean both edits.

## Post-item-5 redesign (2026-07-18, grill-me'd, `[live-verified]`)

Owner asked for a follow-up redesign after all 7 items shipped: new font,
bigger/clearer wizard layout, chip/tab pickers instead of free text.
Grill-me'd on Discord (3 questions), owner answered `"1bc 2a 3 ok"` then
clarified `"C"` — locked to: Direction A wizard (multi-step carousel),
Space Grotesk (headings) + IBM Plex Sans (body) + IBM Plex Mono (code),
applied app-wide, role/goal categories as originally proposed.

- **Font swap — DONE, `[live-verified]`.**
  `frontend/src/app/layout.tsx`: replaced `next/font/local`
  (`CodeNewRoman`/`LibreBaskerville`) with `next/font/google`
  (`IBM_Plex_Sans`→`--font-body`, `IBM_Plex_Mono`→`--font-mono-face`,
  `Space_Grotesk`→`--font-heading`).
  `frontend/src/styles/globals.css`: `--font-sans`/`--font-mono` `@theme`
  tokens repointed at the new variables. `tsc --noEmit` clean.
  Live-verified via `getComputedStyle`: `--font-sans` resolves to
  `"IBM Plex Sans"`, `--font-mono` to `"IBM Plex Mono"`, `--font-heading`
  to `"Space Grotesk"`; message text visually confirmed proportional
  (not the old typewriter monospace).

- **Onboarding wizard rewrite — DONE, `[live-verified]`.**
  `frontend/src/components/workspace/onboarding-dialog.tsx` rewritten from
  a 2-field form into a 3-step carousel: name (`Input`) → role
  (`ToggleGroup type="single"`, 5 options incl. icons) → goals
  (`ToggleGroup type="multiple"`, 5 options). Progress dots, Back/Skip/
  Next navigation, final step uses `ConfettiButton` ("Get started").
  `DialogContent` widened `sm:max-w-md`→`sm:max-w-xl`, title/description
  text sized up. Answers still combine into one string sent via the
  existing `submitAnswer`/`ThreadContext` path — no new backend. `tsc
  --noEmit` clean.
  Live-verified full flow: name entry → role single-select (Developer
  highlighted, others not) → goal multi-select (Code + Automate both
  highlighted simultaneously) → "Get started" fires confetti and sends
  "Quick intro before we start: My name is SwegOn. I'm a developer. I
  want to write code, automate tasks." — new thread created, agent runs.

- **Cross-product note (flagged to owner, not yet re-confirmed)**: the old
  font pairing was tagged `// aio-skin: ... matches apps/web pairing` — a
  deliberate cross-repo brand decision. This swap diverges Aio_df from
  that pairing; owner's "C" answer authorized it for Aio_df specifically,
  but `apps/web` (Aio_project) font stack is untouched and now differs.

## Uncommitted changes on this branch (current `git status --short`)

Item 1 / branding-audit era:
- `skills/public/claude-to-deerflow/` — deleted (3 files).
- `skills/public/podcast-generation/SKILL.md` — "Hello Deer" removed.
- `skills/public/systematic-literature-review/SKILL.md` — DeerFlow→Aio prose.
- `skills/public/systematic-literature-review/scripts/arxiv_search.py` —
  User-Agent string renamed.
- `skills/public/github-deep-research/assets/report_template.md` — report
  footer branding fixed.
- `backend/packages/harness/deerflow/tools/builtins/setup_agent_tool.py` —
  tool docstring branding fixed.
- `backend/packages/harness/deerflow/agents/lead_agent/prompt.py` —
  citation-example URL fixed + negative branding guardrail (broadened again
  for the memory.json leak, see `AIO_DF_BRANDING_AUDIT_STATE.md`).
- `frontend/next.config.js`, `frontend/src/core/artifacts/{hooks.ts,preview.ts}`,
  `frontend/src/components/workspace/artifacts/artifact-file-detail.tsx` —
  str_replace stale-artifact fix.

Items 3-4 (this branch):
- `frontend/src/components/workspace/input-box.tsx` — item 3, chip
  click no longer auto-submits.
- `frontend/src/components/workspace/messages/clarification-card.tsx` —
  item 4, options capped at 3 buttons.
- `frontend/src/core/i18n/locales/en-US.ts`, `zh-CN.ts` — item 3 copy.

Item 5 (this branch):
- `frontend/src/components/workspace/onboarding-dialog.tsx` — new file.
- `frontend/src/app/workspace/chats/[thread_id]/page.tsx` — mounts
  `OnboardingDialog`.

New untracked docs: `AIO_DF_BRANDING_AUDIT_STATE.md`, `SESSION_CONTINUITY.md`
(this file).

## Next step for whoever resumes

1. Items 2-5 all done and live-verified. Original 7-item list is fully
   closed (item 6 was a process instruction, superseded; item 7 folded into
   item 1). No further scoped item remains — check in with owner before
   inventing new work.
2. If owner asks to commit: stage the files listed above (check
   `git status` first, this list may be stale by then), write a commit
   message describing the change set, do not force-push.

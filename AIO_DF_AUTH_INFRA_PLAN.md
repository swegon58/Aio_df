# Aio_df auth + multi-user infra — locked plan (2026-07-19, grilled on Discord)

Repo: `/home/swegon/AI_Agent/Aio_df`. Branch: `main` (feat/aio-df-items-2-5
FF-merged same session, local only, not pushed to `origin` — origin is
upstream `bytedance/deer-flow`, do not push there).

## Locked decisions (grill-me, 5 questions, owner answered `1B 2B 3A 4B 5A`)

1. **DB host: dedicated new Supabase project for Aio_df** — separate from
   Aio_project's apps/web Supabase project. No shared tables/schema between
   the two products.
2. **Login: email+password (already coded) + OIDC/SSO (Google etc)** —
   both enabled. OIDC needs an OAuth client registered in Google Cloud
   Console (owner-only action, external console).
3. **Scope: auth + per-user data isolation only.** No billing/spend-cap in
   this round (that's a separate future project, same pattern as
   Aio_project's Paddle integration if ever needed).
4. **Research: narrow agent research on Postgres RLS + multi-tenant
   hardening best practices**, specifically because current isolation is
   **app-level only** (`deerflow.runtime.user_context` contextvar + WHERE
   clause in repository methods) — not native Postgres RLS. Before real
   users touch this, want a second layer (DB-level RLS) so a missed
   `user_id` filter in one repository method can't leak cross-user data.
5. **Audience: private/known users only** (SwegOn + family), not public
   signup. Lighter requirements: can skip email-verification/anti-spam
   signup hardening for now; still want RLS-level isolation since it's
   cheap to add now vs. retrofit later.

## What already exists (don't rebuild)

- Full session-auth stack: `backend/app/gateway/auth_middleware.py`,
  `csrf_middleware.py`, login page + `AuthProvider.tsx`
  (`frontend/src/core/auth/`, `frontend/src/app/(auth)/login`).
- `DEER_FLOW_AUTH_DISABLED=1` env var is what's currently bypassing it
  (dev/E2E mode, synthetic admin user, `backend/app/gateway/auth_disabled.py`).
- DB backend already supports `postgres` via one config block
  (`config.yaml` → `database.backend: postgres` + `postgres_url:
  $DATABASE_URL`) — no new integration code needed, just point
  `DATABASE_URL` at the new Supabase project's connection string.
- OIDC/SSO hook already exists in `config.example.yaml` (`auth.oidc.*`) —
  needs real client id/secret, not new code.
- Per-user isolation: `deerflow.runtime.user_context.get_effective_user_id()`
  (contextvar, task-local under asyncio) — every repository method
  defaults to filtering by it.

## Next steps

1. **[in progress]** Supabase project created (`project_ref=ljxoskfglzcwqkmteofj`),
   connected via Supabase's own dashboard "Connect via MCP" flow —
   `.mcp.json` added (`claude mcp add --scope project --transport http
   supabase ...`). **Still pending:** owner needs to run `claude /mcp` in a
   real terminal to authenticate the MCP server (interactive OAuth, can't
   be automated), then retrieve the port-5432 direct/session-mode
   connection string (dashboard, or via the MCP once authenticated) and
   hand it back so `DATABASE_URL` can be wired. **Use the session-mode/
   direct connection (port 5432), not the transaction pooler (6543)** —
   see research below, the pooler breaks asyncpg prepared statements and
   unsafely scopes `SET LOCAL`.
2. **[done]** Google OAuth client registered by owner in Google Cloud
   Console; client id/secret handed back and wired 2026-07-22 —
   `GOOGLE_OAUTH_CLIENT_SECRET` in `.env` (gitignored), `auth.oidc.providers.google`
   block in `config.yaml` (gitignored), `redirect_uri:
   http://localhost:8001/api/v1/auth/callback/google`. Verified by loading
   the real config through `get_app_config()` — parses clean, `$GOOGLE_OAUTH_CLIENT_SECRET`
   resolves correctly. **Caveat:** `database.backend` is still `sqlite`
   (step 1 above not finished), so the Google login button will create/auth
   a user against SQLite, not the RLS-hardened Postgres project yet —
   multi-tenant isolation isn't live until step 1 + step 4 land.
3. **[done]** Research fork: Postgres RLS + multi-tenant hardening best
   practices for this exact stack — see checklist below.
4. Wire config: `database.backend: postgres`, `DATABASE_URL` from step 1
   (port 5432), `auth.oidc.*` from step 2, unset `DEER_FLOW_AUTH_DISABLED`.
5. Add DB-level RLS policies per the checklist below as defense-in-depth
   on top of the existing app-level contextvar filter.
6. Migration: existing single-default-user data (if any real data exists
   under `DEFAULT_USER_ID`) needs a decision — reassign to the real owner
   account or start fresh. Flag to owner before running.
7. Live-verify: two real accounts, confirm zero cross-user data bleed
   (threads, uploads, memory) before calling this done — DB-layer
   adversarial test (step 6 of the checklist below), not just UI clicking.

## RLS + hardening research findings (2026-07-19)

**Confirmed by reading the repo:** `runs`, `threads_meta`, `run_events`,
`feedback`, `channel_connections`, `channel_oauth_states`,
`channel_conversations` all have a direct `user_id`/`owner_user_id`
column, filtered app-side. `run/sql.py:139,184` uses a
fetch-then-compare-`row.user_id` pattern instead of a WHERE clause — real
leak risk if a future edit forgets the check; fix to a WHERE-clause
filter. `channel_credentials` table's owner column not yet verified —
check before writing its policy. LangGraph's own checkpoint tables
(`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, from
`langgraph-checkpoint-postgres`) are keyed by `thread_id` only, **no
`user_id` column** — RLS there needs a join to `threads_meta` or must be
explicitly documented as an accepted app-level-only gap.

**Pattern:** `SET LOCAL app.current_user_id = :uid` as the first
statement in each request's transaction (bound param, never
string-formatted), sourced from the same `get_effective_user_id()`
contextvar the app already uses — so app-level and DB-level checks can't
drift. Policies read it via
`current_setting('app.current_user_id', true)` (the `true` arg fails
closed: returns NULL instead of erroring when unset, and NULL matches no
user_id). Supabase's own `auth.uid()`/`auth.jwt()` RLS helpers **don't
apply** — those assume a Supabase-Auth-issued JWT, which this app never
issues. Use Supabase purely as hosted Postgres; write plain custom
policies against the session var.

**Confirmed pooler gotcha:** Supabase's transaction-mode pooler
(Supavisor, port 6543) breaks this: asyncpg's prepared-statement caching
errors under transaction pooling ([supabase/supabase#39227](https://github.com/supabase/supabase/issues/39227)),
and plain `SET`/`SET LOCAL` is unsafe since the pooler can swap the
underlying server connection between transactions. Fix: Aio_df already
runs its own connection pool (`create_async_engine(..., pool_size=...)`
in `engine.py`), so skip Supabase's pooler — connect via port 5432
(session-mode/direct), where `SET LOCAL` is reliable and no
`statement_cache_size=0` workaround is needed.

**Checklist (ranked, prevents-a-leak first):**
1. Connect via Supabase port 5432 (direct/session-mode), not 6543
   (transaction pooler) — do this regardless of RLS. **[owner, pending —
   needs the real Supabase project from step 1 above]**
2. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` (not just `ENABLE`) on every
   user table — otherwise the app's own DB role, as table owner, bypasses
   RLS by default. **[done, live-verified]** — migration
   `0004_rls_policies.py`, logic factored into
   `persistence/rls.py::apply_rls_policies` (single source of truth, also
   called directly by `bootstrap.py`'s empty-DB branch — see finding below).
3. Add `USING (...)` bypass-flag policies (own design, see below) to:
   `users`, `threads_meta`, `runs`, `run_events`, `feedback`,
   `channel_connections`, `channel_oauth_states`, `channel_conversations`,
   plus `user_credits`/`credit_events` (added since this doc was written,
   R18 usage-limits tables) and `channel_credentials` (no owner column of
   its own — join to `channel_connections.owner_user_id`). **[done,
   live-verified against Docker Postgres]**. Policy design deviates from
   this doc's plain `user_id = current_setting(...)`: uses a bypass flag
   (`app.rls_bypass`) so system/admin/scheduler paths that call
   `resolve_user_id()` with its explicit-`None` "no filter" state (e.g. the
   run scheduler's `list_pending`/`list_inflight`) aren't broken by RLS —
   mirrors the app-level three-state contract instead of being a blunt
   per-row filter.
4. Wire `set_config('app.current_user_id', :uid, true)` (not `SET LOCAL`
   directly — Postgres doesn't accept bind params there) as the first
   statement of every session that touches a user-scoped table. **[done for
   `run/sql.py` — reference implementation, live-verified. Remaining
   repos — `channel_connections/sql.py`, `feedback/sql.py`,
   `thread_meta/sql.py`, `usage/sql.py`,
   `runtime/events/store/db.py` — not yet wired, same pattern applies.]**
   This codebase opens a new session per repository call (no shared
   per-request session), so wiring is per-call via
   `persistence/rls.py::apply_rls_context(session, resolved_user_id)`, not a
   single FastAPI dependency as this doc originally assumed.
5. LangGraph checkpoint tables have no `user_id` — **accepted as a
   documented app-level-only gap** (see migration 0004's docstring); thread
   ownership is already checked before any checkpoint read.
6. DB-layer isolation test — **[done, live-verified]**:
   `backend/tests/test_rls_isolation.py`, gated on
   `AIO_DF_TEST_POSTGRES_URL` (skipped by default, no Postgres in normal
   dev/CI). Confirms a query with **no WHERE clause at all** still returns
   only the scoped user's row, and the bypass flag still sees both.
   **Caveat discovered while writing this test:** the connecting Postgres
   role must not be a superuser / have `BYPASSRLS`, or RLS silently does
   nothing — even `FORCE ROW LEVEL SECURITY` doesn't bind superusers. A
   default Docker `postgres` role IS a superuser, so testing against one
   gives a loud, safe test failure (not a false pass). Supabase's own
   default `postgres` role is documented as non-superuser/no-BYPASSRLS, but
   **this needs a one-time confirmation query once the real Supabase
   project exists**: `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE
   rolname = current_user` — if that ever comes back true, every policy in
   this migration is a no-op with no error to signal it.
7. Fix `run/sql.py:139,184`'s fetch-then-compare pattern to a WHERE-clause
   filter — **[done, already landed]**, see prior session.

**New finding (2026-07-22), not anticipated by this doc originally:** this
repo's bootstrap (`persistence/bootstrap.py`) has a hybrid
create_all/alembic strategy where a **fresh** database (`empty` branch —
exactly what step 1 of this plan will produce) does `create_all` + `alembic
stamp head` and **never runs `alembic upgrade`** — so a migration whose
entire body is imperative DDL with no `Base.metadata`/ORM representation
(RLS policies have none) would silently never execute on a brand-new
database. Fixed by having `_run_create_all_sync` call
`apply_rls_policies(sync_conn)` directly right after `create_all`, using the
same function `0004_rls_policies.upgrade()` calls — one source of truth, no
alembic branch-logic changes. Live-verified: dropped/recreated a fresh
Docker Postgres DB, ran `init_engine`, confirmed all 11 tables show
`relrowsecurity`/`relforcerowsecurity = true` and 11 policies exist in
`pg_policies` with zero manual intervention.

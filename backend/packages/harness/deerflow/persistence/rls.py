"""Postgres row-level-security session context.

Defense-in-depth on top of the app-level ``user_id`` WHERE-clause filtering
(``deerflow.runtime.user_context``): once migration ``0004_rls_policies``
lands, every user-scoped table has ``FORCE ROW LEVEL SECURITY`` plus a policy
of the form::

    USING (
        current_setting('app.rls_bypass', true) = 'on'
        OR user_id = current_setting('app.current_user_id', true)
    )

so a repository method that forgets its WHERE clause still can't leak
cross-user rows -- the DB refuses them. ``apply_rls_context`` sets the two
session variables that drive that policy and must be called as the first
statement of every session that touches a user-scoped table:

- ``resolved_user_id`` is a real id -> scope to that user, bypass off.
- ``resolved_user_id`` is ``None`` -> bypass on (mirrors the app-level
  ``user_id=None`` "no filter" contract used by migration/admin/system paths
  that are not user-scoped by design, e.g. background run schedulers).

No-ops on SQLite (``set_config`` is Postgres-only and RLS doesn't exist
there), so this is safe to call unconditionally in both dialects.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_BYPASS = "current_setting('app.rls_bypass', true) = 'on'"

# table -> USING clause (without the "<bypass> OR " prefix, added in apply_rls_policies).
# Single source of truth for migration 0004_rls_policies AND bootstrap.py's
# "empty" branch (a fresh DB does create_all + stamp head, which never runs
# alembic upgrade -- so DDL-only revisions like this one, which have no
# Base.metadata/ORM representation for create_all to pick up, must be applied
# directly there too). See both call sites for why.
RLS_POLICIES: dict[str, str] = {
    "users": "id = current_setting('app.current_user_id', true)",
    "threads_meta": "user_id = current_setting('app.current_user_id', true)",
    "runs": "user_id = current_setting('app.current_user_id', true)",
    "run_events": "user_id = current_setting('app.current_user_id', true)",
    "feedback": "user_id = current_setting('app.current_user_id', true)",
    "channel_connections": "owner_user_id = current_setting('app.current_user_id', true)",
    "channel_oauth_states": "owner_user_id = current_setting('app.current_user_id', true)",
    "channel_conversations": "owner_user_id = current_setting('app.current_user_id', true)",
    "user_credits": "user_id = current_setting('app.current_user_id', true)",
    "credit_events": "user_id = current_setting('app.current_user_id', true)",
    "channel_credentials": (
        "EXISTS (SELECT 1 FROM channel_connections cc "
        "WHERE cc.id = channel_credentials.connection_id "
        "AND cc.owner_user_id = current_setting('app.current_user_id', true))"
    ),
}

RLS_POLICY_NAME = "rls_user_isolation"


def apply_rls_policies(bind: Any) -> None:
    """Enable+force RLS and (re)create the isolation policy on every table in
    ``RLS_POLICIES``. Sync, dialect-guarded (no-op off Postgres), idempotent
    (``CREATE POLICY`` is dropped-then-created since Postgres has no
    ``CREATE POLICY IF NOT EXISTS``). Called from migration
    ``0004_rls_policies.upgrade()`` and from ``bootstrap.py``'s empty-DB
    branch -- see module docstring above.
    """
    if bind.dialect.name != "postgresql":
        return
    for table, clause in RLS_POLICIES.items():
        bind.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        bind.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        bind.execute(text(f"DROP POLICY IF EXISTS {RLS_POLICY_NAME} ON {table}"))
        bind.execute(text(f"CREATE POLICY {RLS_POLICY_NAME} ON {table} USING ({_BYPASS} OR {clause})"))


async def apply_rls_context(session: AsyncSession, resolved_user_id: str | None) -> None:
    """Set ``app.current_user_id`` / ``app.rls_bypass`` for this transaction.

    Uses ``set_config(..., true)`` (transaction-scoped, equivalent to
    ``SET LOCAL``) rather than ``SET LOCAL`` directly because ``SET`` does not
    accept bind parameters in Postgres -- ``set_config`` is a regular
    function call and does.
    """
    bind = getattr(session, "bind", None)
    if bind is None or bind.dialect.name != "postgresql":
        return
    await session.execute(
        text("SELECT set_config('app.current_user_id', :uid, true), set_config('app.rls_bypass', :bypass, true)"),
        {"uid": resolved_user_id or "", "bypass": "off" if resolved_user_id is not None else "on"},
    )

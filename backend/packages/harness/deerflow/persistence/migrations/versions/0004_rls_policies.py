"""Postgres row-level security -- defense-in-depth on user-scoped tables.

Revision ID: 0004_rls_policies
Revises: 0003_usage_credits
Create Date: 2026-07-22

See ``AIO_DF_AUTH_INFRA_PLAN.md`` (locked 2026-07-19) checklist items 2-3.
Current app-level isolation is a WHERE-clause filter in each repository
method (``deerflow.runtime.user_context``); this adds a DB-level backstop so
a repository method that forgets that filter still can't leak cross-user
rows.

Design
------

``FORCE ROW LEVEL SECURITY`` (not just ``ENABLE``) because the app's own DB
role owns these tables, and table owners bypass RLS under plain ``ENABLE``.

Every policy reads two session variables set by
``deerflow.persistence.rls.apply_rls_context`` as the first statement of each
session (transaction-scoped via ``set_config(..., true)``, equivalent to
``SET LOCAL``)::

    USING (
        current_setting('app.rls_bypass', true) = 'on'
        OR user_id = current_setting('app.current_user_id', true)
    )

``rls_bypass = 'on'`` mirrors the existing app-level ``user_id=None`` "no
filter" contract (``resolve_user_id``'s third state) used by
migration/admin/system paths that are not user-scoped by design -- e.g. the
run scheduler's ``list_pending``/``list_inflight``, which iterate runs across
all users. Both session vars default to unset (``current_setting(..., true)``
returns NULL on unset), which fails closed: an unset/forgotten
``apply_rls_context`` call blocks all rows rather than exposing them.

``channel_credentials`` has no owner column of its own (keyed by
``connection_id``, FK to ``channel_connections``), so its policy joins back
to ``channel_connections.owner_user_id``.

LangGraph's own checkpoint tables (``checkpoints``, ``checkpoint_writes``,
``checkpoint_blobs``) are excluded from this migration -- see
``migrations/env.py::include_object``, they aren't DeerFlow-owned tables and
have no ``user_id``/thread-ownership column to key a policy on. Cross-user
isolation for those relies on the app-level thread-ownership check already
performed before any checkpoint read; this is a documented, accepted gap
until either the LangGraph postgres checkpointer's schema changes or a join
through ``threads_meta`` is added separately.

Postgres-only: no-ops entirely on SQLite (used in tests and local dev),
since RLS doesn't exist there.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from deerflow.persistence.rls import RLS_POLICIES, RLS_POLICY_NAME, apply_rls_policies

# revision identifiers, used by Alembic.
revision: str = "0004_rls_policies"
down_revision: str | Sequence[str] | None = "0003_usage_credits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Idempotent: safe to re-run (bootstrap retry, crash mid-DDL) like the
    other revisions in this chain -- delegates to ``persistence.rls.apply_rls_policies``,
    the single source of truth also called directly by ``bootstrap.py``'s
    empty-DB branch (a fresh DB never runs this ``upgrade()`` at all; see that
    module for why).
    """
    apply_rls_policies(op.get_bind())


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in RLS_POLICIES:
        op.execute(f"DROP POLICY IF EXISTS {RLS_POLICY_NAME} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

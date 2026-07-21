"""Add per-user Energy credit tables + a run rate-limit index.

Revision ID: 0003_usage_credits
Revises: 0002_runs_token_usage
Create Date: 2026-07-20

Introduces the ``usage_limits`` subsystem's persistence:

- ``user_credits``  — one balance row per user (weighted token-equivalents,
  may be negative for overdraft) plus the lazy-regen anchor ``last_regen_at``.
- ``credit_events`` — append-only ledger. The partial-unique index on
  ``run_id`` makes run settlement idempotent under retries / crash recovery
  while leaving NULL-run_id rows (grants, clamps) unconstrained.

Also adds the composite index ``ix_runs_user_created`` on
``runs(user_id, created_at)`` that backs the per-user windowed run COUNT used
by the rate limiter.

Neither ``user_credits`` nor ``credit_events`` is a baseline table, so they are
NOT added to ``bootstrap._BASELINE_TABLE_NAMES``: fresh DBs get them from
``Base.metadata.create_all`` (empty branch), and legacy/versioned DBs get them
here via ``op.create_table``. See ``persistence/bootstrap.py`` for the branch
logic.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_usage_credits"
down_revision: str | Sequence[str] | None = "0002_runs_token_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_index(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    return any(ix["name"] == name for ix in sa.inspect(op.get_bind()).get_indexes(table))


def upgrade() -> None:
    """Upgrade schema.

    Idempotent (defence-in-depth, mirroring ``safe_add_column`` in 0002): the
    ``create_table`` / ``create_index`` calls are guarded so re-running against
    a DB that already has these objects — a manual create, a retry after SQLite
    lock contention, or a legacy DB whose schema was materialized from the full
    current ORM metadata — is a safe no-op rather than a hard "already exists".
    """
    if not _has_table("credit_events"):
        op.create_table(
            "credit_events",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("delta_tokens", sa.BigInteger(), nullable=False),
            sa.Column("reason", sa.String(length=32), nullable=False),
            sa.Column("run_id", sa.String(length=64), nullable=True),
            sa.Column("balance_after", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        with op.batch_alter_table("credit_events", schema=None) as batch_op:
            batch_op.create_index("idx_credit_events_run_settlement", ["run_id"], unique=True, sqlite_where=sa.text("run_id IS NOT NULL"), postgresql_where=sa.text("run_id IS NOT NULL"))
            batch_op.create_index(batch_op.f("ix_credit_events_user_id"), ["user_id"], unique=False)

    if not _has_table("user_credits"):
        op.create_table(
            "user_credits",
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("balance_tokens", sa.BigInteger(), nullable=False),
            sa.Column("last_regen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("user_id"),
        )

    if not _has_index("runs", "ix_runs_user_created"):
        with op.batch_alter_table("runs", schema=None) as batch_op:
            batch_op.create_index("ix_runs_user_created", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    if _has_index("runs", "ix_runs_user_created"):
        with op.batch_alter_table("runs", schema=None) as batch_op:
            batch_op.drop_index("ix_runs_user_created")

    if _has_table("user_credits"):
        op.drop_table("user_credits")
    if _has_table("credit_events"):
        with op.batch_alter_table("credit_events", schema=None) as batch_op:
            batch_op.drop_index(batch_op.f("ix_credit_events_user_id"))
            batch_op.drop_index("idx_credit_events_run_settlement", sqlite_where=sa.text("run_id IS NOT NULL"), postgresql_where=sa.text("run_id IS NOT NULL"))
        op.drop_table("credit_events")

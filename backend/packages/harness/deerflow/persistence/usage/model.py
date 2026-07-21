"""ORM models for per-user Energy credit accounting.

Two tables:

- ``user_credits`` — one balance row per user. The balance is stored in
  *weighted token-equivalents* (the internal accounting unit), not in the
  display "Energy" unit, so the display unit can be renamed/rescaled via
  ``tokens_per_unit`` without any migration. ``last_regen_at`` records the
  instant up to which continuous regeneration has already been folded into
  ``balance_tokens`` (lazy regen — see ``deerflow.runtime.usage.service``).

- ``credit_events`` — an append-only ledger for auditability *and* settlement
  idempotency. The partial-unique index on ``run_id`` guarantees a run is
  charged at most once even if settlement is retried (SQLite lock contention,
  crash-recovery reconciliation).

Both live in the shared harness ``Base.metadata`` so they are created alongside
``runs``/``users`` by the bootstrap ``create_all`` path (empty DBs) or by
migration ``0003_usage_credits`` (legacy/versioned DBs).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from deerflow.persistence.base import Base


class UserCreditRow(Base):
    __tablename__ = "user_credits"

    # Matches ``runs.user_id`` width (String(64)); one balance row per user.
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Weighted token-equivalents. MAY be negative (overdraft): a run is allowed
    # to overshoot slightly, and regeneration repays the deficit before new
    # runs are admitted again.
    balance_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Regeneration accrued up to this instant is already folded into
    # ``balance_tokens``. Reads compute additional accrual since this time
    # without writing; writes materialize it and advance the timestamp.
    last_regen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class CreditEventRow(Base):
    __tablename__ = "credit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Weighted token-equivalents. Negative = charge (run spend / config clamp),
    # positive = grant (initial grant, regen fold recorded at settlement).
    delta_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # "run_settlement" | "initial_grant" | "config_clamp" | "manual_adjustment"
    reason: Mapped[str] = mapped_column(String(32), nullable=False)

    # Set for run-settlement rows; the partial-unique index below makes
    # settlement idempotent. NULL for non-run events (grants, clamps).
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Balance snapshot after applying this event, for cheap audit reads.
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    __table_args__ = (
        # One settlement row per run. Leaves NULL/NULL rows (non-run events)
        # unconstrained so many grant/clamp rows can coexist. Mirrors the
        # ``idx_users_oauth_identity`` partial-unique pattern in user/model.py.
        Index(
            "idx_credit_events_run_settlement",
            "run_id",
            unique=True,
            sqlite_where=text("run_id IS NOT NULL"),
            postgresql_where=text("run_id IS NOT NULL"),
        ),
    )

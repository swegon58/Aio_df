"""SQLAlchemy-backed repository for per-user Energy credit accounting.

Stores and mutates the raw ``user_credits`` balance (in weighted
token-equivalents) and the ``credit_events`` ledger. Regeneration *math* lives
in :mod:`deerflow.runtime.usage.service`; this layer only persists, so the
repository stays a thin, testable DB boundary.

Concurrency & idempotency
-------------------------
``settle`` is the delicate operation. Two guarantees:

- **Idempotent** — the ledger row is inserted first inside the transaction;
  a duplicate ``run_id`` violates ``idx_credit_events_run_settlement`` and the
  whole transaction (including the balance change) rolls back, so a retried or
  crash-recovered settlement never double-charges.
- **No lost updates** — the balance row is read ``FOR UPDATE`` (a real row lock
  on Postgres; a no-op on SQLite, which already serialises writers), so two
  concurrent settlements apply sequentially.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deerflow.persistence.rls import apply_rls_context
from deerflow.persistence.run.model import RunRow
from deerflow.persistence.usage.model import CreditEventRow, UserCreditRow
from deerflow.runtime.usage.conversion import accrued_tokens


class CreditRepository:
    """Persistence for Energy credit balances + ledger, and rate-limit counts."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def read(self, user_id: str) -> tuple[int, datetime] | None:
        """Return ``(balance_tokens, last_regen_at)`` or ``None`` if no row."""
        async with self._sf() as session:
            await apply_rls_context(session, user_id)
            row = await session.get(UserCreditRow, user_id)
            if row is None:
                return None
            return row.balance_tokens, _as_utc(row.last_regen_at)

    async def ensure(self, user_id: str, *, initial_balance_tokens: int, now: datetime | None = None) -> tuple[int, datetime]:
        """Lazily create the balance row for a first-seen user.

        Returns the current ``(balance_tokens, last_regen_at)``. Concurrent
        first-inserts are resolved by catching the PK conflict and re-reading.
        """
        now = now or datetime.now(UTC)
        async with self._sf() as session:
            await apply_rls_context(session, user_id)
            row = await session.get(UserCreditRow, user_id)
            if row is not None:
                return row.balance_tokens, _as_utc(row.last_regen_at)
            session.add(UserCreditRow(user_id=user_id, balance_tokens=initial_balance_tokens, last_regen_at=now, updated_at=now))
            session.add(CreditEventRow(user_id=user_id, delta_tokens=initial_balance_tokens, reason="initial_grant", run_id=None, balance_after=initial_balance_tokens, created_at=now))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                row = await session.get(UserCreditRow, user_id)
                if row is not None:
                    return row.balance_tokens, _as_utc(row.last_regen_at)
                # Extremely unlikely: re-raise so the caller sees the failure.
                raise
            return initial_balance_tokens, now

    async def settle(
        self,
        user_id: str,
        run_id: str,
        *,
        charge_tokens: int,
        regen_tokens_per_hour: float,
        max_balance_tokens: int,
        initial_balance_tokens: int,
        now: datetime | None = None,
        reason: str = "run_settlement",
    ) -> bool:
        """Atomically fold in accrued regen and apply a run charge.

        Regeneration accrued since the row's ``last_regen_at`` is computed
        inside the transaction (via the shared :func:`accrued_tokens` helper)
        and capped so the post-regen balance never exceeds
        ``max_balance_tokens``. ``charge_tokens`` (>= 0) is then subtracted; the
        balance may go negative (overdraft).

        Returns ``True`` when the charge was applied, ``False`` when this
        ``run_id`` was already settled (idempotent no-op).
        """
        now = now or datetime.now(UTC)
        async with self._sf() as session:
            await apply_rls_context(session, user_id)
            # Ledger-insert-first: a duplicate run_id trips the unique index and
            # rolls the whole transaction back, so the charge cannot double-apply.
            ledger = CreditEventRow(user_id=user_id, delta_tokens=-int(charge_tokens), reason=reason, run_id=run_id, balance_after=0, created_at=now)
            session.add(ledger)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                return False

            row = await session.get(UserCreditRow, user_id, with_for_update=True)
            if row is None:
                row = UserCreditRow(user_id=user_id, balance_tokens=initial_balance_tokens, last_regen_at=now, updated_at=now)
                session.add(row)
                base_balance = initial_balance_tokens
                last_regen = now
            else:
                base_balance = row.balance_tokens
                last_regen = _as_utc(row.last_regen_at)

            accrued = accrued_tokens(regen_tokens_per_hour, last_regen, now)
            regened = min(max_balance_tokens, base_balance + accrued)
            new_balance = regened - int(charge_tokens)
            row.balance_tokens = new_balance
            row.last_regen_at = now
            row.updated_at = now
            ledger.balance_after = new_balance
            await session.commit()
            return True

    async def count_runs_in_window(self, user_id: str, window_start: datetime) -> tuple[int, datetime | None]:
        """Return ``(count, earliest_created_at)`` for a user's runs since ``window_start``.

        Counts every run created in the window regardless of status (a failed
        run still consumed an admission slot). ``earliest_created_at`` powers
        the ``Retry-After`` hint (when the oldest run ages out of the window).
        """
        stmt = select(func.count(), func.min(RunRow.created_at)).where(RunRow.user_id == user_id, RunRow.created_at >= window_start)
        async with self._sf() as session:
            await apply_rls_context(session, user_id)
            count, earliest = (await session.execute(stmt)).one()
        return int(count or 0), _as_utc(earliest) if isinstance(earliest, datetime) else None


def _as_utc(value: datetime) -> datetime:
    """Normalise a possibly-naive datetime (SQLite drops tzinfo) to aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

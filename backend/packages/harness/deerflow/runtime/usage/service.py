"""UsageService — admission gate, settlement, and read-model for Energy credits.

The Gateway constructs one :class:`UsageService` at startup (from the shared
session factory) and stores it on ``app.state``. Three responsibilities:

- :meth:`check_admission` — pre-run gate. Evaluates run rate limiting and the
  Energy balance; returns an :class:`AdmissionDecision` the router turns into a
  429 on denial.
- :meth:`settle_run` — post-run settlement. Charges the run's weighted-token
  cost against the user's balance, idempotently.
- :meth:`get_usage_state` — read-only snapshot for ``GET /api/usage``.

Config (``usage_limits``) is read fresh on every call via ``get_app_config()``,
so ``config.yaml`` edits take effect without a restart.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deerflow.config.app_config import get_app_config
from deerflow.config.usage_limits_config import CreditsConfig, RateLimitWindow, UsageLimitsConfig
from deerflow.persistence.usage.sql import CreditRepository
from deerflow.runtime.usage.conversion import (
    accrued_tokens,
    energy_to_tokens,
    run_charge_tokens_from_completion,
    tokens_to_energy,
)

logger = logging.getLogger(__name__)

# user_id values that represent "no real user" (auth-disabled single-user
# installs, legacy rows). Never enforced against, so those deployments are
# never bricked by the credit system.
_UNMETERED_USER_IDS = frozenset({"", "default"})


@dataclass(frozen=True)
class _ResolvedLimits:
    """Per-user effective limits after applying config + email overrides."""

    exempt: bool
    max_balance_tokens: int
    initial_balance_tokens: int
    regen_tokens_per_hour: float
    min_start_balance_tokens: int
    windows: tuple[RateLimitWindow, ...]
    credits: CreditsConfig


@dataclass(frozen=True)
class AdmissionDecision:
    """Outcome of the pre-run gate."""

    allowed: bool
    reason: str | None = None  # "insufficient_energy" | "rate_limited"
    detail: dict = field(default_factory=dict)
    retry_after_seconds: int | None = None

    @classmethod
    def allow(cls) -> AdmissionDecision:
        return cls(allowed=True)


@dataclass(frozen=True)
class UsageState:
    """Read-model returned by ``GET /api/usage``."""

    enabled: bool
    unit_name: str = "Energy"
    credits: dict | None = None
    rate_limit: dict | None = None

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "unit_name": self.unit_name,
            "credits": self.credits,
            "rate_limit": self.rate_limit,
        }


class UsageService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._repo = CreditRepository(session_factory)

    # -- config resolution ------------------------------------------------

    @staticmethod
    def _config() -> UsageLimitsConfig:
        return get_app_config().usage_limits

    def _is_exempt_user(self, cfg: UsageLimitsConfig, user_id: str | None, system_role: str, email: str | None) -> bool:
        if user_id is None or user_id in _UNMETERED_USER_IDS:
            return True
        if cfg.exempt_admins and system_role == "admin":
            return True
        override = cfg.user_overrides.get(email) if email else None
        if override is not None and override.exempt:
            return True
        return False

    def _resolve_limits(self, cfg: UsageLimitsConfig, email: str | None) -> _ResolvedLimits:
        credits = cfg.credits
        tpu = credits.tokens_per_unit
        override = cfg.user_overrides.get(email) if email else None

        max_balance = override.max_balance if override and override.max_balance is not None else credits.max_balance
        initial_balance = override.initial_balance if override and override.initial_balance is not None else credits.initial_balance
        regen_per_hour = override.regen_per_hour if override and override.regen_per_hour is not None else credits.regen_per_hour
        windows = override.rate_limit_windows if override and override.rate_limit_windows is not None else cfg.rate_limit.windows

        return _ResolvedLimits(
            exempt=bool(override.exempt) if override else False,
            max_balance_tokens=energy_to_tokens(max_balance, tpu),
            initial_balance_tokens=energy_to_tokens(initial_balance, tpu),
            regen_tokens_per_hour=regen_per_hour * tpu,
            min_start_balance_tokens=energy_to_tokens(credits.min_start_balance, tpu),
            windows=tuple(windows),
            credits=credits,
        )

    # -- admission gate ---------------------------------------------------

    async def check_admission(self, user_id: str | None, *, email: str | None = None, system_role: str = "user") -> AdmissionDecision:
        """Evaluate rate limiting + Energy balance before a run starts."""
        cfg = self._config()
        if not cfg.enabled or self._is_exempt_user(cfg, user_id, system_role, email):
            return AdmissionDecision.allow()
        assert user_id is not None  # narrowed by _is_exempt_user
        limits = self._resolve_limits(cfg, email)
        now = datetime.now(UTC)

        if cfg.rate_limit.enabled and limits.windows:
            decision = await self._check_rate_limit(user_id, limits.windows, now)
            if decision is not None:
                return decision

        if cfg.credits.enabled:
            decision = await self._check_credits(user_id, limits, now)
            if decision is not None:
                return decision
            # Admitted & metered: materialize the balance row now (with full
            # identity: overrides/exemption already resolved here). Row-existence
            # is the "this user is metered" flag that settlement and the in-run
            # middleware key off later, where email/role are unavailable.
            await self._repo.ensure(user_id, initial_balance_tokens=limits.initial_balance_tokens)

        return AdmissionDecision.allow()

    async def _check_rate_limit(self, user_id: str, windows: tuple[RateLimitWindow, ...], now: datetime) -> AdmissionDecision | None:
        for window in windows:
            window_start = now - timedelta(seconds=window.seconds)
            used, earliest = await self._repo.count_runs_in_window(user_id, window_start)
            if used >= window.max_runs:
                # The oldest run in the window ages out at earliest + window.
                retry_after = None
                if earliest is not None:
                    retry_after = max(1, int((earliest + timedelta(seconds=window.seconds) - now).total_seconds()))
                return AdmissionDecision(
                    allowed=False,
                    reason="rate_limited",
                    detail={"error": "rate_limited", "window_seconds": window.seconds, "limit": window.max_runs, "used": used, "retry_after_seconds": retry_after},
                    retry_after_seconds=retry_after,
                )
        return None

    async def _check_credits(self, user_id: str, limits: _ResolvedLimits, now: datetime) -> AdmissionDecision | None:
        stored = await self._repo.read(user_id)
        if stored is None:
            # First-seen user starts with a full grant; never blocked on run #1.
            return None
        balance_tokens, last_regen_at = stored
        effective = min(limits.max_balance_tokens, balance_tokens + accrued_tokens(limits.regen_tokens_per_hour, last_regen_at, now))
        if effective > limits.min_start_balance_tokens:
            return None

        # Time to regenerate just past the minimum-start threshold.
        retry_after = None
        if limits.regen_tokens_per_hour > 0:
            deficit = (limits.min_start_balance_tokens + 1) - effective
            retry_after = max(1, int(deficit / limits.regen_tokens_per_hour * 3600))
        tpu = limits.credits.tokens_per_unit
        return AdmissionDecision(
            allowed=False,
            reason="insufficient_energy",
            detail={
                "error": "insufficient_energy",
                "unit_name": limits.credits.unit_name,
                "balance": max(0.0, tokens_to_energy(effective, tpu)),
                "max": tokens_to_energy(limits.max_balance_tokens, tpu),
                "retry_after_seconds": retry_after,
            },
            retry_after_seconds=retry_after,
        )

    # -- settlement -------------------------------------------------------

    async def settle_run(self, user_id: str | None, run_id: str, completion: Mapping[str, object], *, email: str | None = None, system_role: str = "user") -> None:
        """Charge a completed run's weighted-token cost against the balance.

        Best-effort and idempotent: a duplicate ``run_id`` is a no-op. Exempt
        users and disabled subsystems settle as no-ops.
        """
        cfg = self._config()
        if not cfg.enabled or not cfg.credits.enabled or self._is_exempt_user(cfg, user_id, system_role, email):
            return
        assert user_id is not None
        # Only charge users the gate metered (a balance row exists). Users with
        # no row are exempt/unmetered — never conjure a row at settlement.
        if await self._repo.read(user_id) is None:
            return
        limits = self._resolve_limits(cfg, email)
        charge = run_charge_tokens_from_completion(completion, limits.credits)
        try:
            await self._repo.settle(
                user_id,
                run_id,
                charge_tokens=charge,
                regen_tokens_per_hour=limits.regen_tokens_per_hour,
                max_balance_tokens=limits.max_balance_tokens,
                initial_balance_tokens=limits.initial_balance_tokens,
            )
        except Exception:  # noqa: BLE001 — settlement must never break run completion
            logger.warning("usage: settle_run failed for user=%s run=%s", user_id, run_id, exc_info=True)

    # -- in-run budget ----------------------------------------------------

    async def remaining_run_budget_tokens(self, user_id: str | None) -> int | None:
        """Weighted-token budget a run may still spend before the in-run stop.

        Keyed by ``user_id`` alone (the in-run middleware has no email/role):
        returns ``None`` — meaning "do not enforce" — when the feature is off,
        the user is unmetered/exempt (no balance row, since the gate creates one
        only for metered users), or credits are disabled. Otherwise returns the
        effective remaining balance (after lazy regen) plus the configured
        overdraft allowance.
        """
        cfg = self._config()
        if not cfg.enabled or not cfg.credits.enabled:
            return None
        if user_id is None or user_id in _UNMETERED_USER_IDS:
            return None
        stored = await self._repo.read(user_id)
        if stored is None:
            return None
        limits = self._resolve_limits(cfg, None)
        balance_tokens, last_regen_at = stored
        effective = min(limits.max_balance_tokens, balance_tokens + accrued_tokens(limits.regen_tokens_per_hour, last_regen_at, datetime.now(UTC)))
        overdraft = energy_to_tokens(cfg.credits.overdraft_allowance, cfg.credits.tokens_per_unit)
        return max(0, effective + overdraft)

    # -- read model -------------------------------------------------------

    async def get_usage_state(self, user_id: str | None, *, email: str | None = None, system_role: str = "user") -> UsageState:
        """Compute the read-only usage snapshot for ``GET /api/usage``."""
        cfg = self._config()
        if not cfg.enabled or self._is_exempt_user(cfg, user_id, system_role, email):
            return UsageState(enabled=False, unit_name=cfg.credits.unit_name)
        assert user_id is not None
        limits = self._resolve_limits(cfg, email)
        now = datetime.now(UTC)
        tpu = limits.credits.tokens_per_unit

        credits_state = None
        if cfg.credits.enabled:
            stored = await self._repo.read(user_id)
            if stored is None:
                effective = limits.initial_balance_tokens
            else:
                balance_tokens, last_regen_at = stored
                effective = min(limits.max_balance_tokens, balance_tokens + accrued_tokens(limits.regen_tokens_per_hour, last_regen_at, now))
            balance_energy = tokens_to_energy(effective, tpu)
            max_energy = tokens_to_energy(limits.max_balance_tokens, tpu)
            next_full_at = None
            if limits.regen_tokens_per_hour > 0 and effective < limits.max_balance_tokens:
                remaining = limits.max_balance_tokens - effective
                seconds = remaining / limits.regen_tokens_per_hour * 3600
                next_full_at = (now + timedelta(seconds=seconds)).isoformat()
            credits_state = {
                "enabled": True,
                "balance": balance_energy,
                "balance_display": max(0, int(balance_energy)),
                "max": max_energy,
                "regen_per_hour": limits.regen_tokens_per_hour / tpu if tpu else 0.0,
                "next_full_at": next_full_at,
                "exhausted": effective <= limits.min_start_balance_tokens,
            }

        rate_state = None
        if cfg.rate_limit.enabled and limits.windows:
            windows_out = []
            for window in limits.windows:
                used, earliest = await self._repo.count_runs_in_window(user_id, now - timedelta(seconds=window.seconds))
                resets_at = None
                if earliest is not None:
                    resets_at = (earliest + timedelta(seconds=window.seconds)).isoformat()
                windows_out.append({"seconds": window.seconds, "limit": window.max_runs, "used": used, "resets_at": resets_at})
            rate_state = {"enabled": True, "windows": windows_out}

        return UsageState(enabled=True, unit_name=limits.credits.unit_name, credits=credits_state, rate_limit=rate_state)

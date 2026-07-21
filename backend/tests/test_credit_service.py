"""Tests for the Energy credit system: conversion math + UsageService.

Uses a temp SQLite DB (bootstrapped via init_engine) for the persistence-backed
paths, mirroring tests/test_run_repository.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from deerflow.config.app_config import AppConfig, reset_app_config, set_app_config
from deerflow.config.usage_limits_config import CreditsConfig
from deerflow.runtime.usage.conversion import (
    accrued_tokens,
    energy_to_tokens,
    run_charge_tokens_from_completion,
    tokens_to_energy,
    weighted_tokens,
)
from deerflow.runtime.usage.service import UsageService

# --------------------------------------------------------------------------- #
# Pure conversion math (no DB)
# --------------------------------------------------------------------------- #


def test_weighted_tokens_applies_weights_and_multiplier():
    credits = CreditsConfig(input_weight=1.0, output_weight=4.0, model_multipliers={"gpt-5": 3.0}, default_multiplier=1.0)
    # gpt-5: 3 * (100*1 + 10*4) = 3 * 140 = 420
    assert weighted_tokens(100, 10, credits=credits, model_name="gpt-5") == pytest.approx(420.0)
    # unknown model uses default multiplier 1.0: 100 + 40 = 140
    assert weighted_tokens(100, 10, credits=credits, model_name="other") == pytest.approx(140.0)


def test_run_charge_rounds_up_once_from_by_model():
    credits = CreditsConfig(input_weight=1.0, output_weight=1.0, default_multiplier=1.0)
    completion = {
        "token_usage_by_model": {
            "m1": {"input_tokens": 1, "output_tokens": 0, "total_tokens": 1},
            "m2": {"input_tokens": 0, "output_tokens": 1, "total_tokens": 1},
        }
    }
    # 1 + 1 = 2 weighted tokens
    assert run_charge_tokens_from_completion(completion, credits) == 2


def test_run_charge_falls_back_to_totals():
    credits = CreditsConfig(input_weight=1.0, output_weight=2.0, default_multiplier=1.0)
    completion = {"total_input_tokens": 10, "total_output_tokens": 5, "token_usage_by_model": {}}
    # 10*1 + 5*2 = 20
    assert run_charge_tokens_from_completion(completion, credits) == 20


def test_free_model_multiplier_zero():
    credits = CreditsConfig(model_multipliers={"local": 0.0})
    completion = {"token_usage_by_model": {"local": {"input_tokens": 1000, "output_tokens": 1000}}}
    assert run_charge_tokens_from_completion(completion, credits) == 0


def test_energy_token_roundtrip():
    assert energy_to_tokens(5, 1000) == 5000
    assert tokens_to_energy(5000, 1000) == pytest.approx(5.0)
    assert tokens_to_energy(100, 0) == 0.0


def test_accrued_tokens_clamps_and_scales():
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # 100 tokens/hour for 30 minutes => 50
    assert accrued_tokens(100.0, base, base + timedelta(minutes=30)) == 50
    # backwards clock => 0
    assert accrued_tokens(100.0, base, base - timedelta(minutes=30)) == 0
    # zero rate => 0
    assert accrued_tokens(0.0, base, base + timedelta(hours=10)) == 0


# --------------------------------------------------------------------------- #
# UsageService (DB-backed)
# --------------------------------------------------------------------------- #


def _config(**usage_limits) -> AppConfig:
    return AppConfig.model_validate(
        {
            "sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"},
            "usage_limits": usage_limits,
        }
    )


async def _make_service(tmp_path):
    from deerflow.persistence.engine import get_session_factory, init_engine

    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    await init_engine("sqlite", url=url, sqlite_dir=str(tmp_path))
    return UsageService(get_session_factory())


async def _cleanup():
    from deerflow.persistence.engine import close_engine

    await close_engine()
    reset_app_config()


@pytest.fixture
def enabled_config():
    """usage_limits enabled: 1 Energy = 100 tokens, cap 10 Energy, regen 60/hr."""
    cfg = _config(
        enabled=True,
        credits={"tokens_per_unit": 100, "max_balance": 10, "initial_balance": 10, "regen_per_hour": 60, "input_weight": 1.0, "output_weight": 1.0},
        rate_limit={"enabled": True, "windows": [{"seconds": 300, "max_runs": 3}]},
    )
    set_app_config(cfg)
    yield cfg
    reset_app_config()


@pytest.mark.anyio
async def test_disabled_admits_everything(tmp_path):
    set_app_config(_config(enabled=False))
    svc = await _make_service(tmp_path)
    try:
        decision = await svc.check_admission("u1", email="u1@x.com")
        assert decision.allowed is True
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_admin_exempt(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        decision = await svc.check_admission("admin1", email="a@x.com", system_role="admin")
        assert decision.allowed is True
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_default_user_exempt(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        assert (await svc.check_admission("default")).allowed is True
        assert (await svc.check_admission(None)).allowed is True
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_first_seen_user_admitted(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        # No balance row yet — should be admitted (full grant assumed).
        decision = await svc.check_admission("newuser", email="n@x.com")
        assert decision.allowed is True
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_settlement_charges_and_blocks_when_empty(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        # Gate admits the first run and materializes the balance row.
        assert (await svc.check_admission("u1", email="u1@x.com")).allowed is True
        # Charge 1000 tokens = 10 Energy = the whole balance.
        completion = {"token_usage_by_model": {"m": {"input_tokens": 1000, "output_tokens": 0}}}
        await svc.settle_run("u1", "run-1", completion, email="u1@x.com")
        # Balance now 0 -> next run rejected with insufficient_energy.
        decision = await svc.check_admission("u1", email="u1@x.com")
        assert decision.allowed is False
        assert decision.reason == "insufficient_energy"
        assert decision.detail["error"] == "insufficient_energy"
        assert decision.retry_after_seconds is not None  # regen > 0
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_settlement_is_idempotent(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        assert (await svc.check_admission("u1", email="u1@x.com")).allowed is True
        completion = {"token_usage_by_model": {"m": {"input_tokens": 300, "output_tokens": 0}}}
        await svc.settle_run("u1", "run-1", completion, email="u1@x.com")
        await svc.settle_run("u1", "run-1", completion, email="u1@x.com")  # duplicate
        state = await svc.get_usage_state("u1", email="u1@x.com")
        # 10 Energy - 3 Energy (300 tokens) = 7, charged once despite double settle.
        assert state.credits["balance"] == pytest.approx(7.0, abs=0.2)
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_rate_limit_blocks_after_max_runs(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        from deerflow.persistence.engine import get_session_factory
        from deerflow.persistence.run.model import RunRow

        now = datetime.now(UTC)
        sf = get_session_factory()
        async with sf() as session:
            for i in range(3):
                session.add(RunRow(run_id=f"r{i}", thread_id="t1", user_id="u1", status="success", created_at=now - timedelta(seconds=10)))
            await session.commit()
        decision = await svc.check_admission("u1", email="u1@x.com")
        assert decision.allowed is False
        assert decision.reason == "rate_limited"
        assert decision.detail["used"] == 3
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_regen_recovers_balance(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        from deerflow.persistence.engine import get_session_factory
        from deerflow.persistence.usage.model import UserCreditRow

        # Seed an empty balance whose last_regen_at is 1 hour ago; regen 60/hr
        # (tokens/hr = 60*100 = 6000) should more than refill the 10-Energy cap.
        sf = get_session_factory()
        async with sf() as session:
            session.add(UserCreditRow(user_id="u1", balance_tokens=0, last_regen_at=datetime.now(UTC) - timedelta(hours=1)))
            await session.commit()
        decision = await svc.check_admission("u1", email="u1@x.com")
        assert decision.allowed is True
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_get_usage_state_shape(tmp_path, enabled_config):
    svc = await _make_service(tmp_path)
    try:
        state = await svc.get_usage_state("u1", email="u1@x.com")
        d = state.to_dict()
        assert d["enabled"] is True
        assert d["unit_name"] == "Energy"
        assert d["credits"]["max"] == pytest.approx(10.0)
        assert d["credits"]["balance"] == pytest.approx(10.0)  # first-seen full grant
        assert d["rate_limit"]["windows"][0]["limit"] == 3
    finally:
        await _cleanup()


@pytest.mark.anyio
async def test_user_override_exempt(tmp_path):
    cfg = _config(
        enabled=True,
        credits={"tokens_per_unit": 100, "max_balance": 1, "initial_balance": 0, "regen_per_hour": 0},
        user_overrides={"vip@x.com": {"exempt": True}},
    )
    set_app_config(cfg)
    svc = await _make_service(tmp_path)
    try:
        # initial_balance 0 + regen 0 would normally block, but exempt overrides.
        decision = await svc.check_admission("vip", email="vip@x.com")
        assert decision.allowed is True
    finally:
        await _cleanup()

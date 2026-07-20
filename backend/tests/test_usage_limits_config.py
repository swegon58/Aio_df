"""Tests for the usage_limits config schema (Energy credits + rate limiting)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from deerflow.config.app_config import AppConfig
from deerflow.config.usage_limits_config import (
    CreditsConfig,
    RateLimitConfig,
    RateLimitWindow,
    UsageLimitsConfig,
    UsageUserOverride,
)


def test_defaults_disabled_master_switch():
    cfg = UsageLimitsConfig()
    assert cfg.enabled is False
    assert cfg.exempt_admins is True
    # Sub-systems default to enabled but are gated by the master switch.
    assert cfg.credits.enabled is True
    assert cfg.rate_limit.enabled is True


def test_credits_defaults():
    credits = CreditsConfig()
    assert credits.unit_name == "Energy"
    assert credits.tokens_per_unit == 1000
    assert credits.input_weight == 1.0
    assert credits.output_weight == 4.0
    assert credits.default_multiplier == 1.0
    assert credits.model_multipliers == {}
    assert credits.max_balance == 500
    assert credits.initial_balance == 500
    assert credits.regen_per_hour == 25.0
    assert credits.min_start_balance == 0
    assert credits.in_run_enforcement is True
    assert credits.overdraft_allowance == 20


def test_rate_limit_default_windows():
    rl = RateLimitConfig()
    assert rl.enabled is True
    assert [(w.seconds, w.max_runs) for w in rl.windows] == [(300, 10), (86400, 200)]


def test_initial_balance_cannot_exceed_max():
    with pytest.raises(ValidationError):
        CreditsConfig(max_balance=100, initial_balance=200)


def test_rate_limit_window_rejects_nonpositive():
    with pytest.raises(ValidationError):
        RateLimitWindow(seconds=0, max_runs=5)
    with pytest.raises(ValidationError):
        RateLimitWindow(seconds=60, max_runs=0)


def test_tokens_per_unit_must_be_positive():
    with pytest.raises(ValidationError):
        CreditsConfig(tokens_per_unit=0)


def test_user_override_partial_fields():
    override = UsageUserOverride(max_balance=2000, regen_per_hour=100)
    assert override.exempt is False
    assert override.max_balance == 2000
    assert override.initial_balance is None
    assert override.rate_limit_windows is None


def test_appconfig_exposes_usage_limits_default():
    """A minimal AppConfig gains a usage_limits section with safe defaults."""
    cfg = AppConfig.model_validate({"sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"}})
    assert isinstance(cfg.usage_limits, UsageLimitsConfig)
    assert cfg.usage_limits.enabled is False


def test_appconfig_parses_usage_limits_block():
    cfg = AppConfig.model_validate(
        {
            "sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"},
            "usage_limits": {
                "enabled": True,
                "credits": {"tokens_per_unit": 2000, "max_balance": 1000, "initial_balance": 1000, "model_multipliers": {"gpt-5": 3.0}},
                "rate_limit": {"windows": [{"seconds": 60, "max_runs": 5}]},
                "user_overrides": {"power@example.com": {"max_balance": 5000}},
            },
        }
    )
    assert cfg.usage_limits.enabled is True
    assert cfg.usage_limits.credits.tokens_per_unit == 2000
    assert cfg.usage_limits.credits.model_multipliers["gpt-5"] == 3.0
    assert [(w.seconds, w.max_runs) for w in cfg.usage_limits.rate_limit.windows] == [(60, 5)]
    assert cfg.usage_limits.user_overrides["power@example.com"].max_balance == 5000


def test_null_section_falls_back_to_default():
    """A present-but-null usage_limits (fully commented block) uses defaults."""
    cfg = AppConfig.model_validate(
        {
            "sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"},
            "usage_limits": None,
        }
    )
    assert cfg.usage_limits.enabled is False

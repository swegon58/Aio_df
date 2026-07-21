"""Tests for GET /api/usage (per-user Energy + rate-limit snapshot)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from _router_auth_helpers import make_authed_test_app
from fastapi.testclient import TestClient

from app.gateway.routers import usage
from deerflow.runtime.usage.service import UsageState


def _make_app(usage_service):
    app = make_authed_test_app()
    app.include_router(usage.router)
    app.state.usage_service = usage_service
    return app


def test_usage_disabled_when_service_missing():
    app = _make_app(None)
    with TestClient(app) as client:
        resp = client.get("/api/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["credits"] is None


def test_usage_returns_state_shape():
    svc = MagicMock()
    svc.get_usage_state = AsyncMock(
        return_value=UsageState(
            enabled=True,
            unit_name="Energy",
            credits={"enabled": True, "balance": 312.0, "balance_display": 312, "max": 500.0, "regen_per_hour": 25.0, "next_full_at": None, "exhausted": False},
            rate_limit={"enabled": True, "windows": [{"seconds": 300, "limit": 10, "used": 2, "resets_at": None}]},
        )
    )
    app = _make_app(svc)
    with TestClient(app) as client:
        resp = client.get("/api/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is True
    assert body["unit_name"] == "Energy"
    assert body["credits"]["balance_display"] == 312
    assert body["rate_limit"]["windows"][0]["limit"] == 10
    svc.get_usage_state.assert_awaited_once()

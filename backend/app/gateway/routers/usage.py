"""Per-user usage endpoint — read-only Energy balance + rate-limit state.

``GET /api/usage`` returns the current user's Energy snapshot for the workspace
sidebar. It is fully computed (lazy regen read path + windowed run COUNTs) and
performs no writes, so it is safe to poll. Enforcement lives in
``services.start_run`` (gate), the in-run middleware, and worker settlement;
this endpoint only reports.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.gateway.deps import get_usage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["usage"])


@router.get("/usage")
async def get_usage(request: Request) -> dict:
    """Return the authenticated user's Energy + rate-limit snapshot.

    When the subsystem is disabled, the DB is unavailable, or the user is
    exempt, ``enabled`` is ``false`` and the frontend hides the Energy UI.
    The user is read from ``request.state`` (stamped by AuthMiddleware), same
    as ``services.start_run``, so an unauthenticated request simply reports
    the feature as disabled rather than 401ing.
    """
    usage_service = get_usage_service(request)
    user = getattr(getattr(request, "state", None), "user", None)
    if usage_service is None or user is None:
        return {"enabled": False, "unit_name": "Energy", "credits": None, "rate_limit": None}

    state = await usage_service.get_usage_state(
        str(user.id),
        email=getattr(user, "email", None),
        system_role=getattr(user, "system_role", "user"),
    )
    return state.to_dict()

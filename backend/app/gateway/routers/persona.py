"""Persona API router: per-user personality/tone tuning for the default agent."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.gateway.internal_auth import get_trusted_internal_owner_user_id
from deerflow.agents.persona.schema import PRESETS
from deerflow.agents.persona.storage import get_persona, reset_persona, save_persona
from deerflow.config.paths import make_safe_user_id
from deerflow.runtime.user_context import get_effective_user_id

router = APIRouter(prefix="/api", tags=["persona"])


def _resolve_persona_user_id(request: Request) -> str:
    """Resolve the persona owner for this request (mirrors _resolve_memory_user_id)."""
    raw_owner = get_trusted_internal_owner_user_id(request)
    if raw_owner:
        return make_safe_user_id(raw_owner)
    return get_effective_user_id()


class PersonaTraits(BaseModel):
    """A user's tuned personality/tone traits for the default agent."""

    formality: int = Field(default=50, ge=0, le=100)
    playfulness: int = Field(default=50, ge=0, le=100)
    verbosity: int = Field(default=50, ge=0, le=100)
    emojiUsage: int = Field(default=20, ge=0, le=100)
    nicknameForUser: str | None = Field(default=None, max_length=40)
    customNotes: str = Field(default="", max_length=2000)
    preset: str | None = Field(default=None)
    onboardingCompleted: bool = Field(default=False)


class PersonaUpdateRequest(BaseModel):
    """Partial update — only fields present in the request body are changed."""

    formality: int | None = Field(default=None, ge=0, le=100)
    playfulness: int | None = Field(default=None, ge=0, le=100)
    verbosity: int | None = Field(default=None, ge=0, le=100)
    emojiUsage: int | None = Field(default=None, ge=0, le=100)
    nicknameForUser: str | None = Field(default=None, max_length=40)
    customNotes: str | None = Field(default=None, max_length=2000)
    preset: str | None = Field(default=None)
    onboardingCompleted: bool | None = Field(default=None)


class PersonaPreset(BaseModel):
    id: str
    label: str
    description: str
    traits: PersonaTraits


@router.get("/persona", response_model=PersonaTraits)
async def read_persona(request: Request) -> PersonaTraits:
    user_id = _resolve_persona_user_id(request)
    return PersonaTraits(**get_persona(user_id))


@router.put("/persona", response_model=PersonaTraits)
async def write_persona(request: Request, body: PersonaUpdateRequest) -> PersonaTraits:
    user_id = _resolve_persona_user_id(request)
    current = get_persona(user_id)
    updates = body.model_dump(exclude_unset=True)
    merged = {**current, **updates}
    save_persona(user_id, merged)
    return PersonaTraits(**merged)


@router.post("/persona/reset", response_model=PersonaTraits)
async def reset_persona_route(request: Request) -> PersonaTraits:
    user_id = _resolve_persona_user_id(request)
    return PersonaTraits(**reset_persona(user_id))


@router.get("/persona/presets", response_model=list[PersonaPreset])
async def list_persona_presets() -> list[PersonaPreset]:
    return [PersonaPreset(**preset) for preset in PRESETS.values()]

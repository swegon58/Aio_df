from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import persona
from deerflow.agents.persona.schema import DEFAULT_PERSONA


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(persona.router)
    return app


def test_get_persona_route_returns_current_traits() -> None:
    with (
        patch("app.gateway.routers.persona._resolve_persona_user_id", return_value="alice"),
        patch("app.gateway.routers.persona.get_persona", return_value=DEFAULT_PERSONA),
    ):
        with TestClient(_app()) as client:
            response = client.get("/api/persona")

    assert response.status_code == 200
    assert response.json()["formality"] == 50


def test_put_persona_route_merges_and_saves() -> None:
    saved = {}

    def fake_save(user_id: str, persona_dict: dict) -> None:
        saved["user_id"] = user_id
        saved["persona"] = persona_dict

    with (
        patch("app.gateway.routers.persona._resolve_persona_user_id", return_value="alice"),
        patch("app.gateway.routers.persona.get_persona", return_value=DEFAULT_PERSONA),
        patch("app.gateway.routers.persona.save_persona", side_effect=fake_save),
    ):
        with TestClient(_app()) as client:
            response = client.put("/api/persona", json={"formality": 90, "nicknameForUser": "Boss"})

    assert response.status_code == 200
    assert response.json()["formality"] == 90
    assert response.json()["nicknameForUser"] == "Boss"
    assert saved["user_id"] == "alice"
    assert saved["persona"]["formality"] == 90
    # Fields not sent in the PUT body are preserved from the current persona.
    assert saved["persona"]["verbosity"] == DEFAULT_PERSONA["verbosity"]


def test_reset_persona_route_returns_defaults() -> None:
    with (
        patch("app.gateway.routers.persona._resolve_persona_user_id", return_value="alice"),
        patch("app.gateway.routers.persona.reset_persona", return_value=DEFAULT_PERSONA),
    ):
        with TestClient(_app()) as client:
            response = client.post("/api/persona/reset")

    assert response.status_code == 200
    assert response.json() == DEFAULT_PERSONA


def test_presets_route_returns_all_preset_ids() -> None:
    with TestClient(_app()) as client:
        response = client.get("/api/persona/presets")

    assert response.status_code == 200
    ids = {preset["id"] for preset in response.json()}
    assert ids == {"default", "warm_companion", "efficient_assistant", "playful_buddy"}

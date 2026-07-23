from pathlib import Path
from unittest.mock import patch

from deerflow.agents.persona.schema import DEFAULT_PERSONA


def _patched_paths(tmp_path: Path):
    from deerflow.config.paths import Paths

    return patch("deerflow.agents.persona.storage.get_paths", return_value=Paths(tmp_path))


def test_get_persona_returns_defaults_when_no_file_exists(tmp_path) -> None:
    from deerflow.agents.persona.storage import get_persona

    with _patched_paths(tmp_path):
        persona = get_persona("brand_new_user")
    assert persona == DEFAULT_PERSONA


def test_save_then_get_persona_round_trips(tmp_path) -> None:
    from deerflow.agents.persona.storage import get_persona, save_persona
    from deerflow.config.paths import Paths

    with _patched_paths(tmp_path):
        save_persona("alice", {**DEFAULT_PERSONA, "formality": 80, "nicknameForUser": "Al"})

        persona = get_persona("alice")
        assert persona["formality"] == 80
        assert persona["nicknameForUser"] == "Al"

        persona_file = Paths(tmp_path).user_persona_file("alice")
        assert persona_file.exists()


def test_save_persona_is_isolated_per_user(tmp_path) -> None:
    from deerflow.agents.persona.storage import get_persona, save_persona

    with _patched_paths(tmp_path):
        save_persona("alice", {**DEFAULT_PERSONA, "formality": 90})
        save_persona("bob", {**DEFAULT_PERSONA, "formality": 10})

        assert get_persona("alice")["formality"] == 90
        assert get_persona("bob")["formality"] == 10


def test_reset_persona_restores_defaults(tmp_path) -> None:
    from deerflow.agents.persona.storage import get_persona, reset_persona, save_persona

    with _patched_paths(tmp_path):
        save_persona("alice", {**DEFAULT_PERSONA, "formality": 90, "customNotes": "loud"})

        reset = reset_persona("alice")

        assert reset == DEFAULT_PERSONA
        assert get_persona("alice") == DEFAULT_PERSONA

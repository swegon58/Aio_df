"""Test per-user persona injection into the default agent's soul block.

Tests verify that the default agent (agent_name=None) uses the per-user persona
instead of a static SOUL.md, while custom agents continue to read SOUL.md.
"""

from unittest.mock import patch

from deerflow.agents.lead_agent.prompt import get_agent_soul
from deerflow.agents.persona.schema import DEFAULT_PERSONA


def test_get_agent_soul_renders_persona_for_default_agent() -> None:
    """Verify get_agent_soul renders per-user persona when agent_name is None."""
    persona = {**DEFAULT_PERSONA, "nicknameForUser": "Chief"}
    with (
        patch("deerflow.agents.persona.storage.get_persona", return_value=persona),
        patch("deerflow.runtime.user_context.get_effective_user_id", return_value="alice"),
    ):
        soul = get_agent_soul(None)

    assert soul.startswith("<soul>\n")
    assert soul.endswith("</soul>\n")
    assert "You are Aio" in soul
    assert '"Chief"' in soul


def test_get_agent_soul_still_uses_soul_md_for_custom_agents(tmp_path, monkeypatch) -> None:
    """Verify custom agents still read SOUL.md, not the user persona."""
    from deerflow.config.agents_config import resolve_agent_dir

    agent_dir = resolve_agent_dir("researcher", user_id="alice")
    monkeypatch.setattr(
        "deerflow.config.agents_config.resolve_agent_dir",
        lambda name, *, user_id=None: tmp_path,
    )
    (tmp_path / "SOUL.md").write_text("A meticulous researcher persona.", encoding="utf-8")

    soul = get_agent_soul("researcher")

    assert "A meticulous researcher persona." in soul
    assert "You are Aio" not in soul
    del agent_dir  # unused, only imported to keep the patch target import path exercised

from deerflow.agents.persona.prompt import render_persona_block
from deerflow.agents.persona.schema import DEFAULT_PERSONA


def test_render_includes_fixed_identity_line() -> None:
    block = render_persona_block(DEFAULT_PERSONA)
    assert "You are Aio" in block


def test_render_reflects_low_and_high_trait_extremes() -> None:
    formal_terse = render_persona_block({**DEFAULT_PERSONA, "formality": 90, "playfulness": 5, "verbosity": 5, "emojiUsage": 0})
    assert "formal" in formal_terse.lower()
    assert "brief" in formal_terse.lower()
    assert "never use emoji" in formal_terse.lower()

    casual_playful = render_persona_block({**DEFAULT_PERSONA, "formality": 5, "playfulness": 95, "verbosity": 95, "emojiUsage": 90})
    assert "casual" in casual_playful.lower()
    assert "playful" in casual_playful.lower()


def test_render_includes_nickname_when_set() -> None:
    block = render_persona_block({**DEFAULT_PERSONA, "nicknameForUser": "Boss"})
    assert '"Boss"' in block


def test_render_omits_nickname_line_when_unset() -> None:
    block = render_persona_block(DEFAULT_PERSONA)
    assert "Address the user as" not in block


def test_render_appends_custom_notes_verbatim() -> None:
    block = render_persona_block({**DEFAULT_PERSONA, "customNotes": "Always end with a pun."})
    assert "Always end with a pun." in block

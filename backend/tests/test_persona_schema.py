from deerflow.agents.persona.schema import DEFAULT_PERSONA, PRESETS


def test_default_persona_has_expected_keys_and_values() -> None:
    assert DEFAULT_PERSONA == {
        "formality": 50,
        "playfulness": 50,
        "verbosity": 50,
        "emojiUsage": 20,
        "nicknameForUser": None,
        "customNotes": "",
        "preset": "default",
        "onboardingCompleted": False,
    }


def test_presets_cover_expected_ids_and_shape() -> None:
    assert set(PRESETS.keys()) == {
        "default",
        "warm_companion",
        "efficient_assistant",
        "playful_buddy",
    }
    for preset_id, preset in PRESETS.items():
        assert preset["id"] == preset_id
        assert isinstance(preset["label"], str) and preset["label"]
        assert isinstance(preset["description"], str) and preset["description"]
        assert preset["traits"]["preset"] == preset_id
        for key in ("formality", "playfulness", "verbosity", "emojiUsage"):
            assert 0 <= preset["traits"][key] <= 100

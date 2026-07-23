"""Persona traits schema and starter presets.

Traits are a small, flat dict (not a class hierarchy) — this is a settings
blob on the scale of the existing memory-facts system, not a new subsystem.
"""

from typing import Any

DEFAULT_PERSONA: dict[str, Any] = {
    "formality": 50,
    "playfulness": 50,
    "verbosity": 50,
    "emojiUsage": 20,
    "nicknameForUser": None,
    "customNotes": "",
    "preset": "default",
    "onboardingCompleted": False,
}

PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "id": "default",
        "label": "Balanced Aio",
        "description": "Friendly and even-keeled — not too formal, not too silly.",
        "traits": {**DEFAULT_PERSONA, "preset": "default"},
    },
    "warm_companion": {
        "id": "warm_companion",
        "label": "Warm Companion",
        "description": "Casual, encouraging, a little playful — feels like a close friend.",
        "traits": {
            **DEFAULT_PERSONA,
            "formality": 25,
            "playfulness": 70,
            "verbosity": 60,
            "emojiUsage": 60,
            "preset": "warm_companion",
        },
    },
    "efficient_assistant": {
        "id": "efficient_assistant",
        "label": "Efficient Assistant",
        "description": "Formal, terse, all business — minimal chit-chat.",
        "traits": {
            **DEFAULT_PERSONA,
            "formality": 80,
            "playfulness": 10,
            "verbosity": 20,
            "emojiUsage": 0,
            "preset": "efficient_assistant",
        },
    },
    "playful_buddy": {
        "id": "playful_buddy",
        "label": "Playful Buddy",
        "description": "High energy, jokes, lots of personality — the fun one.",
        "traits": {
            **DEFAULT_PERSONA,
            "formality": 10,
            "playfulness": 90,
            "verbosity": 50,
            "emojiUsage": 80,
            "preset": "playful_buddy",
        },
    },
}

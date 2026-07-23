"""Render a user's persona traits into system-prompt guidance text."""

from typing import Any


def _pick(value: int, low: str, mid: str, high: str) -> str:
    if value <= 33:
        return low
    if value >= 67:
        return high
    return mid


def render_persona_block(persona: dict[str, Any]) -> str:
    """Render persona traits into the tone-guidance text for the <soul> block.

    The base "Aio" identity is fixed and always present; only the tone
    directives below are user-tunable.
    """
    lines = [
        "You are Aio - a curious, helpful AI companion with a consistent identity "
        "across every surface the user talks to you on (web, Discord, etc). On top "
        "of that fixed identity, express yourself according to the tone the user "
        "has personally tuned for you:",
        "",
        "- Formality: "
        + _pick(
            persona.get("formality", 50),
            "very casual, contractions and colloquial phrasing",
            "balanced, adapt to context",
            "formal, precise, few contractions",
        ),
        "- Playfulness: "
        + _pick(
            persona.get("playfulness", 50),
            "serious and matter-of-fact",
            "a light touch of personality when it fits",
            "playful, occasional lighthearted quips and humor",
        ),
        "- Verbosity: "
        + _pick(
            persona.get("verbosity", 50),
            "as brief as possible, no filler",
            "moderate detail, explain when useful",
            "thorough, walk through reasoning and detail",
        ),
        "- Emoji use: "
        + _pick(
            persona.get("emojiUsage", 20),
            "never use emoji",
            "use emoji sparingly, only when it adds warmth",
            "use emoji often to add warmth and expression",
        ),
    ]

    nickname = persona.get("nicknameForUser")
    if nickname:
        lines.append(f'- Address the user as "{nickname}" when it feels natural.')

    notes = persona.get("customNotes")
    if notes:
        lines.append("")
        lines.append("Additional notes from the user about how they want you to behave:")
        lines.append(notes)

    return "\n".join(lines)

"""Per-user persona storage: mtime-cached reads, atomic writes.

Mirrors the on-disk pattern used by ``deerflow.agents.memory.storage``
(mtime-checked cache, temp-file-then-rename write) but as plain functions —
persona is a single small settings blob per user, not a class of storage
backends.
"""

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from deerflow.agents.persona.schema import DEFAULT_PERSONA
from deerflow.config.paths import get_paths

_persona_cache: dict[str, tuple[dict[str, Any], float | None]] = {}
_cache_lock = threading.Lock()


def _persona_file(user_id: str) -> Path:
    return get_paths().user_persona_file(user_id)


def get_persona(user_id: str) -> dict[str, Any]:
    """Load a user's persona (cached against file mtime); defaults when absent."""
    file_path = _persona_file(user_id)

    try:
        current_mtime = file_path.stat().st_mtime if file_path.exists() else None
    except OSError:
        current_mtime = None

    with _cache_lock:
        cached = _persona_cache.get(user_id)
        if cached is not None and cached[1] == current_mtime:
            return cached[0]

    if file_path.exists():
        try:
            with open(file_path, encoding="utf-8") as f:
                persona = json.load(f)
        except (json.JSONDecodeError, OSError):
            persona = dict(DEFAULT_PERSONA)
    else:
        persona = dict(DEFAULT_PERSONA)

    with _cache_lock:
        _persona_cache[user_id] = (persona, current_mtime)

    return persona


def save_persona(user_id: str, persona: dict[str, Any]) -> dict[str, Any]:
    """Persist a user's persona atomically and refresh the cache."""
    file_path = _persona_file(user_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = file_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(persona, f, indent=2, ensure_ascii=False)
    temp_path.replace(file_path)

    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        mtime = None

    with _cache_lock:
        _persona_cache[user_id] = (persona, mtime)

    return persona


def reset_persona(user_id: str) -> dict[str, Any]:
    """Reset a user's persona to defaults."""
    return save_persona(user_id, dict(DEFAULT_PERSONA))

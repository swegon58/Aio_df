"""File-backed storage for growth-memory entries (append-only, per user).

Deliberately simpler than deerflow.agents.memory.storage.FileMemoryStorage: no pluggable
storage-class config, no in-process cache. Prototype scope — see the RAG research plan doc.
"""

import json
import logging
import uuid
from typing import Any, TypedDict

from deerflow.agents.memory.storage import utc_now_iso_z
from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)


class GrowthMemoryEntry(TypedDict):
    id: str
    text: str
    kind: str
    createdAt: str
    metadata: dict[str, Any]


def _load_raw(user_id: str) -> dict[str, Any]:
    file_path = get_paths().user_growth_memory_file(user_id)
    if not file_path.exists():
        return {"version": "1.0", "entries": []}
    try:
        with open(file_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load growth memory file: %s", e)
        return {"version": "1.0", "entries": []}


def load_entries(user_id: str) -> list[GrowthMemoryEntry]:
    """Load all growth-memory entries for a user, oldest first."""
    return _load_raw(user_id).get("entries", [])


def append_entry(user_id: str, text: str, *, kind: str = "observation", metadata: dict[str, Any] | None = None) -> GrowthMemoryEntry:
    """Append a new growth-memory entry for a user and persist it atomically."""
    entry: GrowthMemoryEntry = {
        "id": uuid.uuid4().hex,
        "text": text,
        "kind": kind,
        "createdAt": utc_now_iso_z(),
        "metadata": metadata or {},
    }

    data = _load_raw(user_id)
    data["entries"] = [*data.get("entries", []), entry]

    file_path = get_paths().user_growth_memory_file(user_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_path.replace(file_path)

    return entry

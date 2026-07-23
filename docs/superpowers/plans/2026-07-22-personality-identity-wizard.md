# Personality/Identity Layer + Settings Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every web-UI user a per-user, tunable "personality" for the default Aio agent (tone/formality/playfulness/verbosity/emoji use + nickname + free-text notes), injected into the system prompt on every turn, with a highly visual settings page plus a first-run wizard so users can discover and adjust it easily.

**Architecture:** Reuses the existing `<soul>` system-prompt injection point (`get_agent_soul` in `lead_agent/prompt.py`, already wired into `apply_prompt_template` for every lead-agent turn) — today it only serves custom agents' raw `SOUL.md` files. This plan adds a second, per-user data source for the **default agent** (`agent_name is None`): a small structured JSON blob (`persona.json`, one per user, same per-user file-storage pattern as `memory.json`) rendered into prompt text by a pure function. No new middleware, no new agent-loop wiring, no vector store. A new `/api/persona*` router (mirroring `/api/memory*`'s per-user resolution) exposes it to the frontend, which gets a new Settings page (sliders + preset cards) and a first-run wizard modal reusing the same page's controls.

**Tech Stack:** FastAPI + Pydantic (backend router), plain-dict JSON storage (backend, mirrors `deerflow/agents/memory/storage.py`), Next.js/React 19 + TanStack Query + shadcn `Dialog`/`Slider`/`Textarea` (frontend).

## Global Constraints

- Backend: Python 3.12+, `ruff` line length 240, double quotes — run `cd backend && make format && make lint` before committing backend changes.
- Backend TDD is mandatory (`backend/CLAUDE.md`): every task below writes its test before/alongside its implementation and the full suite (`cd backend && make test`) must stay green.
- Harness (`packages/harness/deerflow/*`) must never import from `app.*` (enforced by `tests/test_harness_boundary.py`) — the persona storage/prompt modules live in the harness; only the router lives in `app/gateway/routers/`.
- Frontend: run `pnpm check` (lint + typecheck) before committing frontend changes; new locale keys must exist in **both** `en-US.ts` and `zh-CN.ts` plus `locales/types.ts`, or the typecheck fails.
- JSON field names throughout (Pydantic models, stored JSON, TypeScript types) use **camelCase**, matching the existing `memory.json`/`MemoryResponse` convention (`workContext`, `createdAt`, etc.) — do not switch to snake_case anywhere in this feature.
- No new datastore, no vector search, no generic "plugin" abstraction for presets — a plain `dict[str, dict]` constant is enough (YAGNI; this mirrors the scale of the existing memory-facts system, not a new subsystem).
- The base "Aio" identity (name, being an AI companion with a consistent voice) is **fixed** and not user-editable — only tone/expression is tunable. Do not let `customNotes` or presets override the fixed identity line in `render_persona_block`.

---

### Task 1: `Paths.user_persona_file` helper

**Files:**
- Modify: `backend/packages/harness/deerflow/config/paths.py:210-212` (right after `user_memory_file`)
- Test: `backend/tests/test_paths_persona_file.py`

**Interfaces:**
- Produces: `Paths.user_persona_file(user_id: str) -> Path`, used by Task 3's storage module.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_paths_persona_file.py
from deerflow.config.paths import get_paths


def test_user_persona_file_is_under_user_dir() -> None:
    paths = get_paths()
    persona_path = paths.user_persona_file("alice")
    assert persona_path == paths.user_dir("alice") / "persona.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_paths_persona_file.py -v`
Expected: FAIL with `AttributeError: 'Paths' object has no attribute 'user_persona_file'`

- [ ] **Step 3: Add the method**

In `backend/packages/harness/deerflow/config/paths.py`, immediately after the existing `user_memory_file` method (around line 212):

```python
    def user_persona_file(self, user_id: str) -> Path:
        """Path to a user's persona (tone/personality tuning) JSON file."""
        return self.user_dir(user_id) / "persona.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_paths_persona_file.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/config/paths.py backend/tests/test_paths_persona_file.py
git commit -m "feat(persona): add per-user persona.json path helper"
```

---

### Task 2: Persona schema (default traits + presets)

**Files:**
- Create: `backend/packages/harness/deerflow/agents/persona/__init__.py`
- Create: `backend/packages/harness/deerflow/agents/persona/schema.py`
- Test: `backend/tests/test_persona_schema.py`

**Interfaces:**
- Produces: `DEFAULT_PERSONA: dict[str, Any]` (keys: `formality`, `playfulness`, `verbosity`, `emojiUsage` — all `int` 0-100 — plus `nicknameForUser: str | None`, `customNotes: str`, `preset: str | None`, `onboardingCompleted: bool`), `PRESETS: dict[str, dict[str, Any]]` (each value has `id`, `label`, `description`, `traits`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_persona_schema.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deerflow.agents.persona'`

- [ ] **Step 3: Create the package and schema module**

`backend/packages/harness/deerflow/agents/persona/__init__.py`:

```python
"""Per-user personality/tone tuning for the default Aio agent."""
```

`backend/packages/harness/deerflow/agents/persona/schema.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/agents/persona/__init__.py backend/packages/harness/deerflow/agents/persona/schema.py backend/tests/test_persona_schema.py
git commit -m "feat(persona): add persona traits schema and starter presets"
```

---

### Task 3: Persona storage (per-user JSON, cached, atomic writes)

**Files:**
- Create: `backend/packages/harness/deerflow/agents/persona/storage.py`
- Test: `backend/tests/test_persona_storage.py`

**Interfaces:**
- Consumes: `DEFAULT_PERSONA` from Task 2 (`deerflow.agents.persona.schema`), `Paths.user_persona_file` from Task 1.
- Produces: `get_persona(user_id: str) -> dict[str, Any]`, `save_persona(user_id: str, persona: dict[str, Any]) -> None`, `reset_persona(user_id: str) -> dict[str, Any]` — used by Task 5 (prompt rendering) and Task 6 (router).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_persona_storage.py
from deerflow.agents.persona.schema import DEFAULT_PERSONA
from deerflow.agents.persona.storage import get_persona, reset_persona, save_persona
from deerflow.config.paths import get_paths


def test_get_persona_returns_defaults_when_no_file_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_paths(), "base_dir", tmp_path, raising=False)
    persona = get_persona("brand_new_user")
    assert persona == DEFAULT_PERSONA


def test_save_then_get_persona_round_trips(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_paths(), "base_dir", tmp_path, raising=False)
    save_persona("alice", {**DEFAULT_PERSONA, "formality": 80, "nicknameForUser": "Al"})

    persona = get_persona("alice")
    assert persona["formality"] == 80
    assert persona["nicknameForUser"] == "Al"

    persona_file = get_paths().user_persona_file("alice")
    assert persona_file.exists()


def test_save_persona_is_isolated_per_user(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_paths(), "base_dir", tmp_path, raising=False)
    save_persona("alice", {**DEFAULT_PERSONA, "formality": 90})
    save_persona("bob", {**DEFAULT_PERSONA, "formality": 10})

    assert get_persona("alice")["formality"] == 90
    assert get_persona("bob")["formality"] == 10


def test_reset_persona_restores_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(get_paths(), "base_dir", tmp_path, raising=False)
    save_persona("alice", {**DEFAULT_PERSONA, "formality": 90, "customNotes": "loud"})

    reset = reset_persona("alice")

    assert reset == DEFAULT_PERSONA
    assert get_persona("alice") == DEFAULT_PERSONA
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deerflow.agents.persona.storage'`

- [ ] **Step 3: Write the storage module**

```python
# backend/packages/harness/deerflow/agents/persona/storage.py
"""Persona storage: per-user persona.json, mirrors deerflow.agents.memory.storage's
mtime-cached, atomic-write pattern at the smaller scale this settings blob needs."""

import json
import logging
import threading
import uuid
from pathlib import Path
from typing import Any

from deerflow.agents.persona.schema import DEFAULT_PERSONA
from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[dict[str, Any], float | None]] = {}
_cache_lock = threading.Lock()


def _persona_file(user_id: str) -> Path:
    return get_paths().user_persona_file(user_id)


def get_persona(user_id: str) -> dict[str, Any]:
    """Load persona traits for a user (cached, invalidated on file mtime change)."""
    file_path = _persona_file(user_id)

    try:
        current_mtime = file_path.stat().st_mtime if file_path.exists() else None
    except OSError:
        current_mtime = None

    with _cache_lock:
        cached = _cache.get(user_id)
        if cached is not None and cached[1] == current_mtime:
            return cached[0]

    if not file_path.exists():
        persona = dict(DEFAULT_PERSONA)
    else:
        try:
            with open(file_path, encoding="utf-8") as f:
                persona = {**DEFAULT_PERSONA, **json.load(f)}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load persona file for user %s: %s", user_id, e)
            persona = dict(DEFAULT_PERSONA)

    with _cache_lock:
        _cache[user_id] = (persona, current_mtime)
    return persona


def save_persona(user_id: str, persona: dict[str, Any]) -> None:
    """Persist persona traits for a user (atomic temp-file + rename, cache update)."""
    file_path = _persona_file(user_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    merged = {**DEFAULT_PERSONA, **persona}
    temp_path = file_path.with_suffix(f".{uuid.uuid4().hex}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    temp_path.replace(file_path)

    try:
        mtime = file_path.stat().st_mtime
    except OSError:
        mtime = None

    with _cache_lock:
        _cache[user_id] = (merged, mtime)


def reset_persona(user_id: str) -> dict[str, Any]:
    """Reset a user's persona back to defaults."""
    persona = dict(DEFAULT_PERSONA)
    save_persona(user_id, persona)
    return persona
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_storage.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/agents/persona/storage.py backend/tests/test_persona_storage.py
git commit -m "feat(persona): add per-user persona storage with atomic writes"
```

---

### Task 4: Render persona traits into prompt text

**Files:**
- Create: `backend/packages/harness/deerflow/agents/persona/prompt.py`
- Test: `backend/tests/test_persona_prompt.py`

**Interfaces:**
- Consumes: a persona `dict[str, Any]` shaped like `DEFAULT_PERSONA` (Task 2/3).
- Produces: `render_persona_block(persona: dict[str, Any]) -> str` — consumed by Task 5's `get_agent_soul` change.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_persona_prompt.py
from deerflow.agents.persona.prompt import render_persona_block
from deerflow.agents.persona.schema import DEFAULT_PERSONA


def test_render_includes_fixed_identity_line() -> None:
    block = render_persona_block(DEFAULT_PERSONA)
    assert "You are Aio" in block


def test_render_reflects_low_and_high_trait_extremes() -> None:
    formal_terse = render_persona_block(
        {**DEFAULT_PERSONA, "formality": 90, "playfulness": 5, "verbosity": 5, "emojiUsage": 0}
    )
    assert "formal" in formal_terse.lower()
    assert "brief" in formal_terse.lower()
    assert "never use emoji" in formal_terse.lower()

    casual_playful = render_persona_block(
        {**DEFAULT_PERSONA, "formality": 5, "playfulness": 95, "verbosity": 95, "emojiUsage": 90}
    )
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_prompt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'deerflow.agents.persona.prompt'`

- [ ] **Step 3: Write the render function**

```python
# backend/packages/harness/deerflow/agents/persona/prompt.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_prompt.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/packages/harness/deerflow/agents/persona/prompt.py backend/tests/test_persona_prompt.py
git commit -m "feat(persona): render persona traits into system-prompt tone guidance"
```

---

### Task 5: Wire persona into the default agent's `<soul>` block

**Files:**
- Modify: `backend/packages/harness/deerflow/agents/lead_agent/prompt.py:725-730` (`get_agent_soul`)
- Test: `backend/tests/test_lead_agent_soul_persona.py`

**Interfaces:**
- Consumes: `get_persona` (Task 3), `render_persona_block` (Task 4), `get_effective_user_id` from `deerflow.runtime.user_context` (existing).
- Produces: `get_agent_soul(agent_name: str | None) -> str` now returns the rendered persona block (wrapped in `<soul>...</soul>`) when `agent_name is None`; unchanged for a real `agent_name` (custom agents keep reading `SOUL.md` exactly as before). This is the only call site (`apply_prompt_template`, `lead_agent/prompt.py:853`) — no other file needs to change.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_lead_agent_soul_persona.py
from unittest.mock import patch

from deerflow.agents.lead_agent.prompt import get_agent_soul
from deerflow.agents.persona.schema import DEFAULT_PERSONA


def test_get_agent_soul_renders_persona_for_default_agent() -> None:
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_lead_agent_soul_persona.py -v`
Expected: FAIL — first test fails because `get_agent_soul(None)` currently always returns `""` (no `SOUL.md` at the global `base_dir` in a clean test env), so `soul.startswith("<soul>\n")` is False.

- [ ] **Step 3: Update `get_agent_soul`**

In `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`, replace the existing function (around line 725):

```python
def get_agent_soul(agent_name: str | None) -> str:
    if agent_name is None:
        # Default agent: per-user tunable persona, not a static SOUL.md.
        from deerflow.agents.persona.prompt import render_persona_block
        from deerflow.agents.persona.storage import get_persona
        from deerflow.runtime.user_context import get_effective_user_id

        persona = get_persona(get_effective_user_id())
        block = render_persona_block(persona)
        return f"<soul>\n{block}\n</soul>\n" if block else ""

    # Custom agent: append its persisted SOUL.md (personality), if present.
    soul = load_agent_soul(agent_name)
    if soul:
        return f"<soul>\n{soul}\n</soul>\n" if soul else ""
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_lead_agent_soul_persona.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full backend suite to check for regressions**

Run: `cd backend && make test`
Expected: all tests pass, no regressions in `test_memory_updater.py` or any custom-agent test that exercises `get_agent_soul`/`apply_prompt_template`.

- [ ] **Step 6: Commit**

```bash
git add backend/packages/harness/deerflow/agents/lead_agent/prompt.py backend/tests/test_lead_agent_soul_persona.py
git commit -m "feat(persona): inject per-user persona into the default agent's soul block"
```

---

### Task 6: `/api/persona*` router

**Files:**
- Create: `backend/app/gateway/routers/persona.py`
- Modify: `backend/app/gateway/app.py` (register the router next to `memory.router`, around line 374)
- Test: `backend/tests/test_persona_router.py`

**Interfaces:**
- Consumes: `get_persona`, `save_persona`, `reset_persona` (Task 3), `PRESETS` (Task 2), `get_trusted_internal_owner_user_id` (existing, `app.gateway.internal_auth`), `get_effective_user_id` (existing), `make_safe_user_id` (existing, `deerflow.config.paths`).
- Produces: `GET /api/persona`, `PUT /api/persona`, `POST /api/persona/reset`, `GET /api/persona/presets` — consumed by Task 7's frontend `api.ts`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_persona_router.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.gateway.routers.persona'`

- [ ] **Step 3: Write the router**

```python
# backend/app/gateway/routers/persona.py
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
```

- [ ] **Step 4: Register the router in the gateway app**

In `backend/app/gateway/app.py`, add the import next to the `memory` import and the registration next to line 374 (`app.include_router(memory.router)`):

```python
    app.include_router(persona.router)
```

(Add `from app.gateway.routers import persona` alongside the existing `from app.gateway.routers import memory` import at the top of the file.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. uv run pytest tests/test_persona_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && make test && make lint`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/gateway/routers/persona.py backend/app/gateway/app.py backend/tests/test_persona_router.py
git commit -m "feat(persona): add /api/persona router (get/update/reset/presets)"
```

---

### Task 7: Frontend `core/persona` module (types, api, hooks)

**Files:**
- Create: `frontend/src/core/persona/types.ts`
- Create: `frontend/src/core/persona/api.ts`
- Create: `frontend/src/core/persona/hooks.ts`
- Create: `frontend/src/core/persona/index.ts`
- Test: `frontend/tests/unit/core/persona/api.test.ts`

**Interfaces:**
- Produces: `PersonaTraits`, `PersonaUpdateInput`, `PersonaPreset` types; `loadPersona`, `updatePersona`, `resetPersona`, `loadPersonaPresets` functions; `usePersona`, `useUpdatePersona`, `useResetPersona`, `usePersonaPresets` hooks — consumed by Task 8 (settings page) and Task 9 (wizard).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/tests/unit/core/persona/api.test.ts
import { describe, expect, it, vi, beforeEach } from "vitest";

import { loadPersona, updatePersona, resetPersona, loadPersonaPresets } from "@/core/persona/api";
import type { PersonaTraits } from "@/core/persona/types";

const samplePersona: PersonaTraits = {
  formality: 50,
  playfulness: 50,
  verbosity: 50,
  emojiUsage: 20,
  nicknameForUser: null,
  customNotes: "",
  preset: "default",
  onboardingCompleted: false,
};

describe("persona api", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(samplePersona), { status: 200 })),
    );
  });

  it("loadPersona fetches /api/persona", async () => {
    const result = await loadPersona();
    expect(result).toEqual(samplePersona);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/persona"));
  });

  it("updatePersona PUTs the partial update", async () => {
    await updatePersona({ formality: 90 });
    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({ formality: 90 });
  });

  it("resetPersona POSTs to /api/persona/reset", async () => {
    await resetPersona();
    const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/persona/reset");
    expect(init.method).toBe("POST");
  });

  it("loadPersonaPresets fetches /api/persona/presets", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify([]), { status: 200 })),
    );
    const presets = await loadPersonaPresets();
    expect(presets).toEqual([]);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/persona/presets"));
  });
});
```

Note: check `frontend/tests/unit/core/memory/` (if present) or any existing `tests/unit/core/*/api.test.ts` for the project's actual test runner import (Rstest per `frontend/CLAUDE.md`) before running — use whatever mocking API (`vi` or the Rstest equivalent) that file already uses, keeping the assertions above unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test tests/unit/core/persona/api.test.ts`
Expected: FAIL — `Cannot find module '@/core/persona/api'`

- [ ] **Step 3: Write `types.ts`**

```typescript
// frontend/src/core/persona/types.ts
export interface PersonaTraits {
  formality: number;
  playfulness: number;
  verbosity: number;
  emojiUsage: number;
  nicknameForUser: string | null;
  customNotes: string;
  preset: string | null;
  onboardingCompleted: boolean;
}

export interface PersonaUpdateInput {
  formality?: number;
  playfulness?: number;
  verbosity?: number;
  emojiUsage?: number;
  nicknameForUser?: string | null;
  customNotes?: string;
  preset?: string | null;
  onboardingCompleted?: boolean;
}

export interface PersonaPreset {
  id: string;
  label: string;
  description: string;
  traits: PersonaTraits;
}
```

- [ ] **Step 4: Write `api.ts`**

```typescript
// frontend/src/core/persona/api.ts
import { fetch } from "../api/fetcher";
import { getBackendBaseURL } from "../config";

import type { PersonaPreset, PersonaTraits, PersonaUpdateInput } from "./types";

async function readPersonaResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as {
      detail?: unknown;
    };
    const detailMessage =
      typeof errorData.detail === "string" ? errorData.detail : null;
    throw new Error(detailMessage ?? `${fallbackMessage}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function loadPersona(): Promise<PersonaTraits> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona`);
  return readPersonaResponse<PersonaTraits>(response, "Failed to fetch persona");
}

export async function updatePersona(
  input: PersonaUpdateInput,
): Promise<PersonaTraits> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return readPersonaResponse<PersonaTraits>(response, "Failed to update persona");
}

export async function resetPersona(): Promise<PersonaTraits> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona/reset`, {
    method: "POST",
  });
  return readPersonaResponse<PersonaTraits>(response, "Failed to reset persona");
}

export async function loadPersonaPresets(): Promise<PersonaPreset[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/persona/presets`);
  return readPersonaResponse<PersonaPreset[]>(response, "Failed to fetch persona presets");
}
```

- [ ] **Step 5: Write `hooks.ts`**

```typescript
// frontend/src/core/persona/hooks.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  loadPersona,
  loadPersonaPresets,
  resetPersona,
  updatePersona,
} from "./api";
import type { PersonaTraits, PersonaUpdateInput } from "./types";

export function usePersona() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["persona"],
    queryFn: () => loadPersona(),
  });
  return { persona: data ?? null, isLoading, error };
}

export function useUpdatePersona() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: PersonaUpdateInput) => updatePersona(input),
    onSuccess: (persona) => {
      queryClient.setQueryData<PersonaTraits>(["persona"], persona);
    },
  });
}

export function useResetPersona() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => resetPersona(),
    onSuccess: (persona) => {
      queryClient.setQueryData<PersonaTraits>(["persona"], persona);
    },
  });
}

export function usePersonaPresets() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["persona-presets"],
    queryFn: () => loadPersonaPresets(),
  });
  return { presets: data ?? [], isLoading, error };
}
```

- [ ] **Step 6: Write `index.ts`**

```typescript
// frontend/src/core/persona/index.ts
export * from "./api";
export * from "./hooks";
export * from "./types";
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd frontend && pnpm test tests/unit/core/persona/api.test.ts`
Expected: PASS (4 passed)

- [ ] **Step 8: Typecheck and commit**

```bash
cd frontend && pnpm typecheck
git add frontend/src/core/persona frontend/tests/unit/core/persona
git commit -m "feat(persona): add core/persona API client, hooks, and types"
```

---

### Task 8: Personality settings page + settings-dialog registration + i18n

**Files:**
- Create: `frontend/src/components/workspace/settings/personality-settings-page.tsx`
- Modify: `frontend/src/components/workspace/settings/settings-dialog.tsx`
- Modify: `frontend/src/core/i18n/locales/types.ts`
- Modify: `frontend/src/core/i18n/locales/en-US.ts`
- Modify: `frontend/src/core/i18n/locales/zh-CN.ts`
- Test: `frontend/tests/unit/components/workspace/settings/personality-settings-page.test.tsx`

**Interfaces:**
- Consumes: `usePersona`, `useUpdatePersona`, `useResetPersona`, `usePersonaPresets` (Task 7).
- Produces: `PersonalitySettingsPage` component, reused by Task 9's wizard for its slider/preset controls.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/tests/unit/components/workspace/settings/personality-settings-page.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/core/persona/hooks", () => ({
  usePersona: () => ({
    persona: {
      formality: 50,
      playfulness: 50,
      verbosity: 50,
      emojiUsage: 20,
      nicknameForUser: null,
      customNotes: "",
      preset: "default",
      onboardingCompleted: true,
    },
    isLoading: false,
    error: null,
  }),
  useUpdatePersona: () => ({ mutate: vi.fn(), isPending: false }),
  useResetPersona: () => ({ mutate: vi.fn(), isPending: false }),
  usePersonaPresets: () => ({
    presets: [
      { id: "default", label: "Balanced Aio", description: "...", traits: {} },
      { id: "warm_companion", label: "Warm Companion", description: "...", traits: {} },
    ],
    isLoading: false,
    error: null,
  }),
}));

import { PersonalitySettingsPage } from "@/components/workspace/settings/personality-settings-page";

describe("PersonalitySettingsPage", () => {
  it("renders every preset card and all four tone sliders", () => {
    render(<PersonalitySettingsPage />);
    expect(screen.getByText("Balanced Aio")).toBeInTheDocument();
    expect(screen.getByText("Warm Companion")).toBeInTheDocument();
    expect(screen.getByLabelText(/formality/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/playfulness/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/verbosity/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/emoji/i)).toBeInTheDocument();
  });
});
```

Note: mirror whatever render/import setup `memory-settings-page` unit tests already use for `@/core/*` hook mocking and shadcn component rendering in this repo (check for an existing `tests/unit/components/workspace/settings/*.test.tsx` file first) — keep the assertions above unchanged if the setup boilerplate differs.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test tests/unit/components/workspace/settings/personality-settings-page.test.tsx`
Expected: FAIL — `Cannot find module '@/components/workspace/settings/personality-settings-page'`

- [ ] **Step 3: Write the settings page**

```tsx
// frontend/src/components/workspace/settings/personality-settings-page.tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import {
  usePersona,
  usePersonaPresets,
  useResetPersona,
  useUpdatePersona,
} from "@/core/persona/hooks";
import type { PersonaTraits } from "@/core/persona/types";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

const SLIDER_FIELDS: Array<{
  key: keyof Pick<PersonaTraits, "formality" | "playfulness" | "verbosity" | "emojiUsage">;
  labelKey: "formality" | "playfulness" | "verbosity" | "emojiUsage";
}> = [
  { key: "formality", labelKey: "formality" },
  { key: "playfulness", labelKey: "playfulness" },
  { key: "verbosity", labelKey: "verbosity" },
  { key: "emojiUsage", labelKey: "emojiUsage" },
];

export function PersonalitySettingsPage() {
  const { t } = useI18n();
  const { persona } = usePersona();
  const { presets } = usePersonaPresets();
  const updatePersona = useUpdatePersona();
  const resetPersona = useResetPersona();
  const [nickname, setNickname] = useState(persona?.nicknameForUser ?? "");
  const [notes, setNotes] = useState(persona?.customNotes ?? "");

  if (!persona) {
    return null;
  }

  function handleSliderChange(
    field: (typeof SLIDER_FIELDS)[number]["key"],
    value: number[],
  ) {
    updatePersona.mutate(
      { [field]: value[0] },
      {
        onError: () => toast.error(t.settings.personality.saveFailed),
      },
    );
  }

  function handlePresetSelect(presetId: string) {
    const preset = presets.find((p) => p.id === presetId);
    if (!preset) return;
    updatePersona.mutate(
      { ...preset.traits, preset: presetId },
      {
        onSuccess: () => toast.success(t.settings.personality.presetApplied),
        onError: () => toast.error(t.settings.personality.saveFailed),
      },
    );
  }

  function handleSaveTextFields() {
    updatePersona.mutate(
      { nicknameForUser: nickname || null, customNotes: notes },
      {
        onSuccess: () => toast.success(t.settings.personality.saved),
        onError: () => toast.error(t.settings.personality.saveFailed),
      },
    );
  }

  function handleReset() {
    resetPersona.mutate(undefined, {
      onSuccess: () => toast.success(t.settings.personality.resetDone),
      onError: () => toast.error(t.settings.personality.saveFailed),
    });
  }

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold">{t.settings.personality.title}</h3>
        <p className="text-muted-foreground text-sm">
          {t.settings.personality.description}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {presets.map((preset) => (
          <button
            key={preset.id}
            type="button"
            onClick={() => handlePresetSelect(preset.id)}
            className={cn(
              "rounded-lg border p-4 text-left transition-colors hover:bg-muted",
              persona.preset === preset.id && "border-primary bg-muted",
            )}
          >
            <div className="font-medium">{preset.label}</div>
            <div className="text-muted-foreground text-sm">{preset.description}</div>
          </button>
        ))}
      </div>

      <div className="space-y-6">
        {SLIDER_FIELDS.map(({ key, labelKey }) => (
          <div key={key} className="space-y-2">
            <label htmlFor={`persona-${key}`} className="text-sm font-medium">
              {t.settings.personality[labelKey]}
            </label>
            <Slider
              id={`persona-${key}`}
              aria-label={t.settings.personality[labelKey]}
              min={0}
              max={100}
              step={5}
              value={[persona[key]]}
              onValueChange={(value) => handleSliderChange(key, value)}
            />
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <label htmlFor="persona-nickname" className="text-sm font-medium">
          {t.settings.personality.nicknameLabel}
        </label>
        <Input
          id="persona-nickname"
          value={nickname}
          placeholder={t.settings.personality.nicknamePlaceholder}
          onChange={(e) => setNickname(e.target.value)}
          onBlur={handleSaveTextFields}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="persona-notes" className="text-sm font-medium">
          {t.settings.personality.notesLabel}
        </label>
        <Textarea
          id="persona-notes"
          value={notes}
          placeholder={t.settings.personality.notesPlaceholder}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleSaveTextFields}
          rows={4}
        />
      </div>

      <Button variant="outline" onClick={handleReset} disabled={resetPersona.isPending}>
        {t.settings.personality.resetButton}
      </Button>
    </div>
  );
}
```

(If `Slider` or `Textarea` are not yet present under `frontend/src/components/ui/`, add them via the project's shadcn registry command — check `frontend/CLAUDE.md`'s Code Style section, `ui/` is "auto-generated from registries" — rather than hand-writing them.)

- [ ] **Step 4: Register the section in `settings-dialog.tsx`**

In `frontend/src/components/workspace/settings/settings-dialog.tsx`:

Add the import:

```typescript
import { PersonalitySettingsPage } from "@/components/workspace/settings/personality-settings-page";
```

Add `DramaIcon` to the `lucide-react` import list (alongside `BellIcon`, `CableIcon`, etc.).

Add `"personality"` to the `SettingsSection` union type:

```typescript
type SettingsSection =
  | "account"
  | "appearance"
  | "channels"
  | "memory"
  | "personality"
  | "tools"
  | "skills"
  | "notification"
  | "plan"
  | "about";
```

Add an entry to the `sections` array (right after the `memory` entry) and its dependency:

```typescript
      {
        id: "personality",
        label: t.settings.sections.personality,
        icon: DramaIcon,
      },
```

```typescript
      t.settings.sections.personality,
```

(added to the `useMemo` dependency array alongside the other `t.settings.sections.*` entries)

Add the render branch (right after the `memory` branch):

```typescript
              {activeSection === "personality" && <PersonalitySettingsPage />}
```

- [ ] **Step 5: Add i18n keys — `locales/types.ts`**

Add `personality: string;` to the `sections` interface, and a new `personality` block to the top-level settings translation interface (mirroring the shape of the existing `memory` block):

```typescript
    personality: {
      title: string;
      description: string;
      formality: string;
      playfulness: string;
      verbosity: string;
      emojiUsage: string;
      nicknameLabel: string;
      nicknamePlaceholder: string;
      notesLabel: string;
      notesPlaceholder: string;
      resetButton: string;
      saved: string;
      saveFailed: string;
      resetDone: string;
      presetApplied: string;
    };
```

- [ ] **Step 6: Add i18n keys — `locales/en-US.ts`**

Add `personality: "Personality",` to the `sections` object (after `memory: "Memory",`), and the full block after the existing `memory` block:

```typescript
    personality: {
      title: "Personality",
      description:
        "Tune how Aio talks to you — tone, playfulness, and how much detail it gives.",
      formality: "Formality",
      playfulness: "Playfulness",
      verbosity: "Verbosity",
      emojiUsage: "Emoji use",
      nicknameLabel: "What should Aio call you?",
      nicknamePlaceholder: "e.g. Boss, Alex, Captain",
      notesLabel: "Anything else Aio should know about how to talk to you?",
      notesPlaceholder: "e.g. Always suggest a next step at the end.",
      resetButton: "Reset to default",
      saved: "Personality updated.",
      saveFailed: "Couldn't save your personality settings — try again.",
      resetDone: "Personality reset to default.",
      presetApplied: "Preset applied.",
    },
```

- [ ] **Step 7: Add i18n keys — `locales/zh-CN.ts`**

Add `personality: "个性",` to the `sections` object, and the full block (translated) after the existing `memory` block:

```typescript
    personality: {
      title: "个性",
      description: "调整 Aio 与你交流的方式——语气、俏皮程度，以及回答的详细程度。",
      formality: "正式程度",
      playfulness: "俏皮程度",
      verbosity: "详细程度",
      emojiUsage: "表情符号使用",
      nicknameLabel: "Aio 应该怎么称呼你？",
      nicknamePlaceholder: "例如：老板、Alex、队长",
      notesLabel: "还有什么 Aio 应该知道的交流方式吗？",
      notesPlaceholder: "例如：每次回答结尾都建议下一步行动。",
      resetButton: "恢复默认",
      saved: "个性设置已更新。",
      saveFailed: "保存个性设置失败，请重试。",
      resetDone: "个性已恢复默认。",
      presetApplied: "已应用预设。",
    },
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd frontend && pnpm test tests/unit/components/workspace/settings/personality-settings-page.test.tsx`
Expected: PASS

- [ ] **Step 9: Typecheck and lint**

Run: `cd frontend && pnpm check`
Expected: no errors (this is what catches a missing key in either locale file).

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/workspace/settings/personality-settings-page.tsx \
        frontend/src/components/workspace/settings/settings-dialog.tsx \
        frontend/src/core/i18n/locales/types.ts \
        frontend/src/core/i18n/locales/en-US.ts \
        frontend/src/core/i18n/locales/zh-CN.ts \
        frontend/tests/unit/components/workspace/settings/personality-settings-page.test.tsx
git commit -m "feat(persona): add Personality settings page with presets and tone sliders"
```

---

### Task 9: First-run onboarding wizard

**Files:**
- Create: `frontend/src/components/workspace/onboarding/personality-wizard.tsx`
- Modify: `frontend/src/app/workspace/workspace-content.tsx`
- Test: `frontend/tests/unit/components/workspace/onboarding/personality-wizard.test.tsx`

**Interfaces:**
- Consumes: `usePersona`, `usePersonaPresets`, `useUpdatePersona` (Task 7), reuses the same preset-card and slider markup pattern as `PersonalitySettingsPage` (Task 8) — kept as separate, smaller components here since the wizard is a 3-step flow (preset → sliders → nickname), not a full settings page.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/tests/unit/components/workspace/onboarding/personality-wizard.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const updateMutate = vi.fn();

vi.mock("@/core/persona/hooks", () => ({
  usePersona: () => ({
    persona: {
      formality: 50,
      playfulness: 50,
      verbosity: 50,
      emojiUsage: 20,
      nicknameForUser: null,
      customNotes: "",
      preset: "default",
      onboardingCompleted: false,
    },
    isLoading: false,
    error: null,
  }),
  usePersonaPresets: () => ({
    presets: [
      {
        id: "default",
        label: "Balanced Aio",
        description: "...",
        traits: { formality: 50, playfulness: 50, verbosity: 50, emojiUsage: 20 },
      },
    ],
    isLoading: false,
    error: null,
  }),
  useUpdatePersona: () => ({ mutate: updateMutate, isPending: false }),
}));

import { PersonalityWizard } from "@/components/workspace/onboarding/personality-wizard";

describe("PersonalityWizard", () => {
  it("shows the wizard when onboarding is not yet completed", () => {
    render(<PersonalityWizard />);
    expect(screen.getByText("Balanced Aio")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test tests/unit/components/workspace/onboarding/personality-wizard.test.tsx`
Expected: FAIL — `Cannot find module '@/components/workspace/onboarding/personality-wizard'`

- [ ] **Step 3: Write the wizard**

```tsx
// frontend/src/components/workspace/onboarding/personality-wizard.tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useI18n } from "@/core/i18n/hooks";
import { usePersona, usePersonaPresets, useUpdatePersona } from "@/core/persona/hooks";
import { cn } from "@/lib/utils";

type Step = "preset" | "nickname";

export function PersonalityWizard() {
  const { t } = useI18n();
  const { persona } = usePersona();
  const { presets } = usePersonaPresets();
  const updatePersona = useUpdatePersona();
  const [step, setStep] = useState<Step>("preset");
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [nickname, setNickname] = useState("");

  if (!persona || persona.onboardingCompleted) {
    return null;
  }

  function handleFinish() {
    updatePersona.mutate({
      nicknameForUser: nickname || null,
      onboardingCompleted: true,
    });
  }

  return (
    <Dialog open onOpenChange={() => {}}>
      <DialogContent aria-describedby={undefined} className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t.settings.personality.wizardTitle}</DialogTitle>
        </DialogHeader>

        {step === "preset" && (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              {t.settings.personality.wizardPresetPrompt}
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => {
                    setSelectedPreset(preset.id);
                    updatePersona.mutate({ ...preset.traits, preset: preset.id });
                  }}
                  className={cn(
                    "rounded-lg border p-4 text-left transition-colors hover:bg-muted",
                    selectedPreset === preset.id && "border-primary bg-muted",
                  )}
                >
                  <div className="font-medium">{preset.label}</div>
                  <div className="text-muted-foreground text-sm">{preset.description}</div>
                </button>
              ))}
            </div>
            <div className="flex justify-end">
              <Button onClick={() => setStep("nickname")} disabled={!selectedPreset}>
                {t.settings.personality.wizardNext}
              </Button>
            </div>
          </div>
        )}

        {step === "nickname" && (
          <div className="space-y-4">
            <p className="text-muted-foreground text-sm">
              {t.settings.personality.wizardNicknamePrompt}
            </p>
            <Input
              value={nickname}
              placeholder={t.settings.personality.nicknamePlaceholder}
              onChange={(e) => setNickname(e.target.value)}
            />
            <p className="text-muted-foreground text-xs">
              {t.settings.personality.wizardSettingsHint}
            </p>
            <div className="flex justify-end">
              <Button onClick={handleFinish}>{t.settings.personality.wizardFinish}</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Add the three new wizard i18n keys**

Add to `locales/types.ts`'s `personality` block, and both `en-US.ts`/`zh-CN.ts`'s `personality` blocks:

```typescript
      wizardTitle: string;
      wizardPresetPrompt: string;
      wizardNext: string;
      wizardNicknamePrompt: string;
      wizardSettingsHint: string;
      wizardFinish: string;
```

`en-US.ts` values:

```typescript
      wizardTitle: "Let's set up how Aio talks to you",
      wizardPresetPrompt: "Pick a starting point — you can fine-tune everything later in Settings.",
      wizardNext: "Next",
      wizardNicknamePrompt: "What should Aio call you? (optional)",
      wizardSettingsHint: "You can change this anytime in Settings → Personality.",
      wizardFinish: "Done",
```

`zh-CN.ts` values:

```typescript
      wizardTitle: "设置一下 Aio 跟你说话的方式",
      wizardPresetPrompt: "选一个起点——之后可以在设置里随时微调。",
      wizardNext: "下一步",
      wizardNicknamePrompt: "Aio 应该怎么称呼你？（可选）",
      wizardSettingsHint: "之后随时可以在 设置 → 个性 里修改。",
      wizardFinish: "完成",
```

- [ ] **Step 5: Mount the wizard in `workspace-content.tsx`**

In `frontend/src/app/workspace/workspace-content.tsx`, add the import:

```typescript
import { PersonalityWizard } from "@/components/workspace/onboarding/personality-wizard";
```

And render it as a sibling of `<CommandPalette />` (it renders `null` once `persona.onboardingCompleted` is `true`, so it is safe to always mount):

```tsx
      <CommandPalette />
      <PersonalityWizard />
      <Toaster position="top-center" />
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && pnpm test tests/unit/components/workspace/onboarding/personality-wizard.test.tsx`
Expected: PASS

- [ ] **Step 7: Typecheck, lint, and full unit suite**

Run: `cd frontend && pnpm check && pnpm test`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/workspace/onboarding/personality-wizard.tsx \
        frontend/src/app/workspace/workspace-content.tsx \
        frontend/src/core/i18n/locales/types.ts \
        frontend/src/core/i18n/locales/en-US.ts \
        frontend/src/core/i18n/locales/zh-CN.ts \
        frontend/tests/unit/components/workspace/onboarding/personality-wizard.test.tsx
git commit -m "feat(persona): add first-run personality wizard"
```

---

## Self-Review

**1. Spec coverage:**
- Universal web-UI personality layer (not just Discord) → Tasks 2-6 (backend persona schema/storage/render/wiring/router).
- Settings page to customize tone/personality → Task 8.
- Highly visual/discoverable wizard → Task 9, mounted globally in `workspace-content.tsx` so every authenticated page shows it until completed.
- Per-user isolation consistent with the rest of the app → Task 3 (`user_persona_file`, mirrors `user_memory_file`) and Task 6 (`_resolve_persona_user_id` mirrors `_resolve_memory_user_id` exactly, including the trusted-internal-owner-header path for IM channels).
- "Companion, not Swiss-army-knife" scope constraint (grill point 1) → untouched; no tool/agent surface changed.

**2. Placeholder scan:** No TBD/TODO/"add error handling" placeholders — every step has complete code. One deliberate exception: Task 7 Step 1 and Task 8 Step 1 note to check for an existing sibling test file's mocking boilerplate before running, since the plan author could not directly confirm whether this repo's frontend uses `vi` (Vitest-style, via Rstest's compatible API) or another mocking surface — this is a one-line environment check, not a design gap, and the assertions to keep are given in full either way.

**3. Type consistency:** `PersonaTraits` fields (`formality`, `playfulness`, `verbosity`, `emojiUsage`, `nicknameForUser`, `customNotes`, `preset`, `onboardingCompleted`) are identical across `DEFAULT_PERSONA` (Task 2), `storage.py` (Task 3), the Pydantic `PersonaTraits`/`PersonaUpdateRequest` models (Task 6), and the TypeScript `PersonaTraits`/`PersonaUpdateInput` interfaces (Task 7) — verified name-by-name while writing this plan.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-22-personality-identity-wizard.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints.

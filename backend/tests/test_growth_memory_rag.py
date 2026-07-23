"""Tests for growth-memory storage + RAG retrieval (research prototype)."""

import json
from unittest.mock import MagicMock, patch

from langchain_core.embeddings import DeterministicFakeEmbedding

from deerflow.agents.growth_memory.retrieval import render_growth_memory_block, retrieve_relevant_entries
from deerflow.agents.growth_memory.storage import append_entry, load_entries


def _patch_paths(tmp_path):
    def mock_get_paths():
        mock_paths = MagicMock()
        mock_paths.user_growth_memory_file.return_value = tmp_path / "growth_memory.json"
        return mock_paths

    return mock_get_paths


class TestGrowthMemoryStorage:
    def test_load_entries_missing_file_returns_empty(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            assert load_entries("user-1") == []

    def test_append_entry_persists_and_round_trips(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            entry = append_entry("user-1", "Learned to set boundaries at work", kind="milestone", metadata={"source": "reflection"})

            assert entry["text"] == "Learned to set boundaries at work"
            assert entry["kind"] == "milestone"
            assert entry["metadata"] == {"source": "reflection"}
            assert entry["id"]
            assert entry["createdAt"]

            entries = load_entries("user-1")
            assert entries == [entry]

    def test_append_entry_is_append_only(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            append_entry("user-1", "first entry")
            append_entry("user-1", "second entry")

            entries = load_entries("user-1")
            assert [e["text"] for e in entries] == ["first entry", "second entry"]

    def test_growth_memory_file_is_valid_json_on_disk(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            append_entry("user-1", "an entry")

        raw = json.loads((tmp_path / "growth_memory.json").read_text(encoding="utf-8"))
        assert raw["version"] == "1.0"
        assert len(raw["entries"]) == 1


class TestGrowthMemoryRetrieval:
    def test_retrieve_relevant_entries_empty_when_no_entries(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            results = retrieve_relevant_entries("user-1", "career growth", DeterministicFakeEmbedding(size=8))
            assert results == []

    def test_retrieve_relevant_entries_returns_stored_text(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            append_entry("user-1", "Wants to become a better public speaker", kind="goal")
            append_entry("user-1", "Prefers terse, direct feedback", kind="preference")

            results = retrieve_relevant_entries("user-1", "public speaking goals", DeterministicFakeEmbedding(size=8), k=1)

            assert len(results) == 1
            assert results[0].page_content in {"Wants to become a better public speaker", "Prefers terse, direct feedback"}
            assert results[0].metadata["kind"] in {"goal", "preference"}

    def test_render_growth_memory_block_empty(self):
        assert render_growth_memory_block([]) == ""

    def test_render_growth_memory_block_formats_entries(self, tmp_path):
        with patch("deerflow.agents.growth_memory.storage.get_paths", side_effect=_patch_paths(tmp_path)):
            append_entry("user-1", "Started running weekly", kind="observation")
            results = retrieve_relevant_entries("user-1", "exercise habits", DeterministicFakeEmbedding(size=8))

        block = render_growth_memory_block(results)
        assert block.startswith("Relevant growth memory:")
        assert "Started running weekly" in block

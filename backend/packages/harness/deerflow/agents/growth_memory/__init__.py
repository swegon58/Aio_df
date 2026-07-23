"""Growth memory: RAG-retrieved long-term entries about a user's growth (goals, patterns, milestones).

Research/prototype module. See docs/superpowers/plans/2026-07-23-growth-memory-rag-research.md.
"""

from deerflow.agents.growth_memory.retrieval import retrieve_relevant_entries
from deerflow.agents.growth_memory.storage import GrowthMemoryEntry, append_entry, load_entries

__all__ = ["GrowthMemoryEntry", "append_entry", "load_entries", "retrieve_relevant_entries"]

"""RAG retrieval over a user's growth-memory entries.

Builds an in-process vector index per call from `storage.load_entries` and returns the
top-k entries relevant to a query. `embeddings` is caller-supplied on purpose: this repo
has no configured embeddings provider yet (open question in the research plan doc), so
production callers must pick and pass one explicitly rather than this module defaulting
to a fake.
"""

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

from deerflow.agents.growth_memory.storage import load_entries


def _entries_to_documents(user_id: str) -> list[Document]:
    return [Document(page_content=entry["text"], metadata={"id": entry["id"], "kind": entry["kind"], "createdAt": entry["createdAt"], **entry["metadata"]}) for entry in load_entries(user_id)]


def retrieve_relevant_entries(user_id: str, query: str, embeddings: Embeddings, *, k: int = 5) -> list[Document]:
    """Return up to `k` growth-memory entries most relevant to `query`, empty if the user has none."""
    documents = _entries_to_documents(user_id)
    if not documents:
        return []

    store = InMemoryVectorStore(embeddings)
    store.add_documents(documents)
    return store.similarity_search(query, k=k)


def render_growth_memory_block(entries: list[Document]) -> str:
    """Render retrieved entries as a prompt-injectable text block, empty string if none."""
    if not entries:
        return ""
    lines = [f"- ({doc.metadata.get('createdAt', '?')}) {doc.page_content}" for doc in entries]
    return "Relevant growth memory:\n" + "\n".join(lines)

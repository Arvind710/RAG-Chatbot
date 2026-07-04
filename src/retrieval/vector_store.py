"""
ChromaDB Vector Store Wrapper.

Provides a thin abstraction over ChromaDB's PersistentClient for the
mutual_funds collection. Handles initialization, querying with optional
metadata filters, and error reporting when the collection doesn't exist.
"""

import chromadb
from src.utils.config import config


class VectorStore:
    """Wrapper around ChromaDB PersistentClient for the mutual_funds collection."""

    def __init__(self, persist_dir: str = None):
        """
        Initialize the ChromaDB client and load the mutual_funds collection.

        Args:
            persist_dir: Path to the ChromaDB persistence directory.
                         Defaults to config.VECTORSTORE_DIR.

        Raises:
            ValueError: If the mutual_funds collection does not exist.
        """
        self._persist_dir = persist_dir or config.VECTORSTORE_DIR
        self._client = chromadb.PersistentClient(path=self._persist_dir)

        try:
            self._collection = self._client.get_collection(
                name="mutual_funds"
            )
        except Exception as e:
            raise ValueError(
                f"ChromaDB collection 'mutual_funds' not found at "
                f"'{self._persist_dir}'. Run the ingestion pipeline first "
                f"(python -m src.ingestion.run_ingestion). Original error: {e}"
            )

    @property
    def collection(self):
        """Return the underlying ChromaDB collection."""
        return self._collection

    @property
    def count(self) -> int:
        """Return the number of chunks in the collection."""
        return self._collection.count()

    def query(
        self,
        query_embedding: list,
        top_k: int = 5,
        where_filter: dict = None,
    ) -> dict:
        """
        Perform a similarity search against the mutual_funds collection.

        Args:
            query_embedding: The 384-dimensional embedding vector for the query.
            top_k: Number of results to return. Defaults to 5.
            where_filter: Optional ChromaDB metadata filter dict.
                          Example: {"scheme_name": "HDFC Small Cap Fund Direct Growth"}

        Returns:
            A dict with keys: 'ids', 'documents', 'metadatas', 'distances'.
            Each value is a list-of-lists (one list per query — we always
            send a single query, so index [0] to unpack).
        """
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }

        if where_filter:
            query_params["where"] = where_filter

        return self._collection.query(**query_params)

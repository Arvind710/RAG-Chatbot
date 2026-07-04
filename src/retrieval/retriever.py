"""
Retriever Module.

Implements the full retrieval pipeline:
  1. Extract scheme_name from user query (substring match against 5 known schemes)
  2. Embed the query using BGE instruction prefix
  3. Query ChromaDB with top_k=5 and optional scheme_name filter
  4. Post-filter: remove noise chunks, deduplicate, cap at final K=3
  5. Return ranked RetrievedChunk dicts
"""

import logging
from typing import List, Dict, Any, Optional

from src.embeddings.embedder import Embedder
from src.retrieval.vector_store import VectorStore
from src.utils.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# The 5 known scheme names — ordered longest-first so that
# "HDFC Gold ETF Fund of Fund" doesn't false-match before
# a more specific substring.
KNOWN_SCHEMES = [
    "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "HDFC Silver ETF FoF Direct Growth",
    "HDFC Large Cap Fund Direct Growth",
    "HDFC Small Cap Fund Direct Growth",
    "HDFC Mid Cap Fund Direct Growth",
]

# Aliases that users might type → canonical scheme_name in metadata.
# Keys are lowercase for case-insensitive matching.
SCHEME_ALIASES = {
    # Full names (lowercase)
    "hdfc gold etf fund of fund direct plan growth": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "hdfc silver etf fof direct growth": "HDFC Silver ETF FoF Direct Growth",
    "hdfc large cap fund direct growth": "HDFC Large Cap Fund Direct Growth",
    "hdfc small cap fund direct growth": "HDFC Small Cap Fund Direct Growth",
    "hdfc mid cap fund direct growth": "HDFC Mid Cap Fund Direct Growth",
    # Short names users are more likely to type
    "hdfc gold etf": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "hdfc gold fund": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "hdfc gold": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "gold etf": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "hdfc silver etf": "HDFC Silver ETF FoF Direct Growth",
    "hdfc silver fund": "HDFC Silver ETF FoF Direct Growth",
    "hdfc silver": "HDFC Silver ETF FoF Direct Growth",
    "silver etf": "HDFC Silver ETF FoF Direct Growth",
    "hdfc large cap": "HDFC Large Cap Fund Direct Growth",
    "large cap": "HDFC Large Cap Fund Direct Growth",
    "hdfc small cap": "HDFC Small Cap Fund Direct Growth",
    "small cap": "HDFC Small Cap Fund Direct Growth",
    "hdfc mid cap": "HDFC Mid Cap Fund Direct Growth",
    "mid cap": "HDFC Mid Cap Fund Direct Growth",
    "hdfc midcap": "HDFC Mid Cap Fund Direct Growth",
    "hdfc smallcap": "HDFC Small Cap Fund Direct Growth",
    "hdfc largecap": "HDFC Large Cap Fund Direct Growth",
}

# Minimum content length for a chunk to be considered useful.
# Chunks shorter than this are noise (section headers like "See All",
# "Holdings (\n3\n)", "Compare similar funds").
MIN_CHUNK_LENGTH = 20


def extract_scheme_name(query: str) -> Optional[str]:
    """
    Extract a scheme name from the user's query by substring matching.

    Tries longest aliases first to avoid partial false matches
    (e.g., "hdfc gold etf fund of fund" before "hdfc gold").

    Args:
        query: The raw user query string.

    Returns:
        The canonical scheme_name string, or None if no scheme is detected.
    """
    query_lower = query.lower()

    # Sort aliases by length (longest first) to prefer specific matches.
    sorted_aliases = sorted(SCHEME_ALIASES.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        if alias in query_lower:
            return SCHEME_ALIASES[alias]

    return None


def _filter_noise_chunks(
    documents: List[str],
    metadatas: List[dict],
    distances: List[float],
    ids: List[str],
) -> tuple:
    """Remove chunks that are too short to be useful (section headers, etc.)."""
    filtered = []
    for doc, meta, dist, id_ in zip(documents, metadatas, distances, ids):
        # Ignore the injected context prefix when checking length
        lines = doc.strip().split("\n")
        if len(lines) >= 2 and lines[0].startswith("Scheme:") and lines[1].startswith("Section:"):
            actual_content = "\n".join(lines[2:]).strip()
        else:
            actual_content = doc.strip()
            
        if len(actual_content) >= MIN_CHUNK_LENGTH:
            filtered.append((doc, meta, dist, id_))
    if not filtered:
        return [], [], [], []
    docs, metas, dists, id_list = zip(*filtered)
    return list(docs), list(metas), list(dists), list(id_list)


def _deduplicate_chunks(
    documents: List[str],
    metadatas: List[dict],
    distances: List[float],
    ids: List[str],
) -> tuple:
    """
    Deduplicate chunks by content, keeping the one with the latest scrape_date.

    This handles the case where the same content was embedded from two
    different scrape timestamps.
    """
    seen = {}  # content -> index of best entry
    best_docs = []
    best_metas = []
    best_dists = []
    best_ids = []

    for i, (doc, meta, dist, id_) in enumerate(
        zip(documents, metadatas, distances, ids)
    ):
        content_key = doc.strip()
        if content_key in seen:
            # Keep the entry with the later scrape_date
            existing_idx = seen[content_key]
            existing_scrape = best_metas[existing_idx].get("scrape_date", "0")
            current_scrape = meta.get("scrape_date", "0")
            if current_scrape > existing_scrape:
                # Replace with newer version
                best_docs[existing_idx] = doc
                best_metas[existing_idx] = meta
                best_dists[existing_idx] = dist
                best_ids[existing_idx] = id_
        else:
            seen[content_key] = len(best_docs)
            best_docs.append(doc)
            best_metas.append(meta)
            best_dists.append(dist)
            best_ids.append(id_)

    return best_docs, best_metas, best_dists, best_ids


class Retriever:
    """
    Retrieves the most relevant chunks for a user query.

    Pipeline:
        1. Extract scheme_name from query (substring matching)
        2. Embed query with BGE instruction prefix
        3. ChromaDB similarity search (top_k=5, cosine)
        4. Post-filter: noise removal, deduplication, cap at final_k=3
    """

    def __init__(self, embedder: Embedder = None, vector_store: VectorStore = None):
        """
        Args:
            embedder: An Embedder instance (loads BGE model). Created if not provided.
            vector_store: A VectorStore instance (connects to ChromaDB). Created if not provided.
        """
        self._embedder = embedder or Embedder()
        self._vector_store = vector_store or VectorStore()

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        final_k: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant chunks for a user query.

        Args:
            query: The user's natural language question.
            top_k: Number of raw results to fetch from ChromaDB (default: 10).
                   Over-fetching allows room for post-filtering.
            final_k: Maximum number of results to return after filtering
                     (default: config.TOP_K, which is 3).

        Returns:
            A list of dicts, each with keys:
                - 'content': The chunk text
                - 'metadata': Dict with source_url, scheme_name, section_type,
                              scrape_date, has_table
                - 'distance': Cosine distance (lower = more similar)
        """
        top_k = top_k or 40
        final_k = final_k or config.TOP_K

        # Step 1: Extract scheme name for metadata filtering
        scheme_name = extract_scheme_name(query)
        where_filter = None
        if scheme_name:
            where_filter = {"scheme_name": scheme_name}
            logger.info(f"Detected scheme: '{scheme_name}' — applying metadata filter")
        else:
            logger.info("No specific scheme detected — searching across all schemes")

        # Step 2: Embed the query with BGE instruction prefix
        query_embedding = self._embedder.embed_query(query)

        # Step 3: Query ChromaDB
        try:
            results = self._vector_store.query(
                query_embedding=query_embedding,
                top_k=top_k,
                where_filter=where_filter,
            )
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return []

        # Unpack results (ChromaDB returns list-of-lists; we sent 1 query)
        if not results or not results.get("documents") or not results["documents"][0]:
            logger.warning("No results returned from ChromaDB")
            return []

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]

        logger.info(f"ChromaDB returned {len(documents)} raw results")

        # Step 4a: Remove noise chunks
        documents, metadatas, distances, ids = _filter_noise_chunks(
            documents, metadatas, distances, ids
        )
        logger.info(f"After noise filtering: {len(documents)} results")

        # Step 4b: Deduplicate by content
        documents, metadatas, distances, ids = _deduplicate_chunks(
            documents, metadatas, distances, ids
        )
        logger.info(f"After deduplication: {len(documents)} results")

        # Step 4c: Cap at final_k
        documents = documents[:final_k]
        metadatas = metadatas[:final_k]
        distances = distances[:final_k]
        ids = ids[:final_k]

        # Build response
        retrieved_chunks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            retrieved_chunks.append(
                {
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                }
            )

        logger.info(
            f"Returning {len(retrieved_chunks)} chunks "
            f"(distances: {[round(d, 4) for d in distances]})"
        )

        return retrieved_chunks


if __name__ == "__main__":
    # Quick manual test
    retriever = Retriever()

    test_queries = [
        "What is the expense ratio of HDFC Small Cap Fund?",
        "What are the top holdings of HDFC Mid Cap Fund?",
        "What is the minimum SIP amount for HDFC Large Cap Fund?",
        "What are the returns of HDFC Gold ETF?",
        "Tell me about HDFC Silver ETF fund manager",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print(f"{'='*60}")
        results = retriever.retrieve(q)
        for i, chunk in enumerate(results):
            print(f"\n--- Result {i+1} (distance: {chunk['distance']:.4f}) ---")
            print(f"Section: {chunk['metadata']['section_type']}")
            print(f"Scheme:  {chunk['metadata']['scheme_name']}")
            content_preview = chunk["content"][:200]
            print(f"Content: {content_preview}...")

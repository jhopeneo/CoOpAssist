"""
Document retriever for QmanAssist.
Retrieves relevant documents from ChromaDB based on query similarity.
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from config.settings import get_settings
from src.core.vector_store import VectorStore, get_vector_store


class DocumentRetriever:
    """Retrieves relevant documents from the vector store."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        top_k: int = None,
        similarity_threshold: float = None,
    ):
        """Initialize document retriever.

        Args:
            vector_store: VectorStore instance. If None, uses global instance.
            top_k: Number of documents to retrieve. If None, uses setting.
            similarity_threshold: Minimum similarity score. If None, uses setting.
        """
        self.settings = get_settings()
        self.vector_store = vector_store or get_vector_store()
        self.top_k = top_k or self.settings.top_k
        self.similarity_threshold = (
            similarity_threshold or self.settings.similarity_threshold
        )

        logger.info(
            f"DocumentRetriever initialized: top_k={self.top_k}, "
            f"threshold={self.similarity_threshold}"
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for a query.

        Args:
            query: Query text.
            top_k: Number of results to return. If None, uses configured value.
            filters: Metadata filters (e.g., {"doc_type": "pdf"}).

        Returns:
            List of retrieved documents with content, metadata, and scores.
        """
        top_k = top_k or self.top_k

        logger.info(f"Retrieving documents for query: '{query[:50]}...'")

        # Query vector store
        results = self.vector_store.query(
            query_text=query, n_results=top_k, where=filters
        )

        # Filter by similarity threshold
        filtered_results = []
        for doc in results:
            # ChromaDB returns L2 distance (lower is better)
            # Convert to similarity score (higher is better)
            distance = doc["distance"]
            similarity = 1 / (1 + distance)  # Convert L2 distance to similarity

            if similarity >= self.similarity_threshold:
                doc["similarity_score"] = similarity
                filtered_results.append(doc)

        logger.info(
            f"Retrieved {len(filtered_results)} documents "
            f"(filtered from {len(results)} by threshold)"
        )

        return filtered_results

    def retrieve_with_context(
        self, query: str, top_k: Optional[int] = None, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retrieve documents with additional context.

        Args:
            query: Query text.
            top_k: Number of results to return.
            filters: Metadata filters.

        Returns:
            Dictionary with documents and metadata about the retrieval.
        """
        documents = self.retrieve(query=query, top_k=top_k, filters=filters)

        # Extract unique sources
        sources = set()
        doc_types = {}
        for doc in documents:
            if "source" in doc["metadata"]:
                sources.add(doc["metadata"]["source"])

            doc_type = doc["metadata"].get("doc_type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        return {
            "query": query,
            "documents": documents,
            "num_results": len(documents),
            "unique_sources": list(sources),
            "doc_types": doc_types,
        }

    def retrieve_by_source(
        self, source_path: str, top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all documents from a specific source file.

        Args:
            source_path: Path to the source file.
            top_k: Maximum number of results. If None, retrieves all.

        Returns:
            List of documents from the source.
        """
        # Use a generic query to get all documents from this source
        filters = {"source": str(source_path)}

        # Get documents without similarity filtering
        results = self.vector_store.query(
            query_text="",  # Empty query
            n_results=top_k or 100,
            where=filters,
        )

        logger.info(f"Retrieved {len(results)} documents from source: {source_path}")
        return results

    def get_similar_chunks(
        self, document_id: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar chunks to a given document.

        Args:
            document_id: ID of the document to find similar chunks for.
            top_k: Number of similar chunks to return.

        Returns:
            List of similar documents.
        """
        # Get the document content
        result = self.vector_store.collection.get(ids=[document_id])

        if not result["documents"]:
            logger.warning(f"Document not found: {document_id}")
            return []

        # Use the document content as query
        content = result["documents"][0]
        similar_docs = self.retrieve(query=content, top_k=top_k + 1)

        # Filter out the original document
        similar_docs = [doc for doc in similar_docs if doc["id"] != document_id]

        return similar_docs[:top_k]

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about the retrieval system.

        Returns:
            Dictionary with retrieval statistics.
        """
        vector_stats = self.vector_store.get_collection_stats()

        stats = {
            "vector_store": vector_stats,
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold,
        }

        return stats


# Convenience function
def retrieve_documents(query: str, top_k: int = None) -> List[Dict[str, Any]]:
    """Convenience function to retrieve documents.

    Args:
        query: Query text.
        top_k: Number of results to return.

    Returns:
        List of retrieved documents.
    """
    retriever = DocumentRetriever()
    return retriever.retrieve(query=query, top_k=top_k)

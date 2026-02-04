"""
Document retriever for QmanAssist.
Retrieves relevant documents from ChromaDB based on query similarity.
"""

from typing import List, Dict, Any, Optional
import re
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

    def _extract_codes(self, query: str) -> List[str]:
        """Extract potential material codes or part numbers from query.

        Args:
            query: Query text.

        Returns:
            List of extracted codes (material numbers, part numbers, etc.).
        """
        codes = []

        # Pattern 1: Number-number+letter (e.g., "312-80A", "1-80B")
        pattern1 = re.findall(r'\b\d+[-/]\d+[A-Za-z]+\b', query)
        codes.extend(pattern1)

        # Pattern 2: Word/brand followed by number (e.g., "primeco 585", "PrimeCo 585")
        pattern2 = re.findall(r'\b[A-Za-z]+\s+\d+\b', query, re.IGNORECASE)
        codes.extend(pattern2)

        # Pattern 3: Alphanumeric codes (e.g., "ABC123", "XYZ-456")
        pattern3 = re.findall(r'\b[A-Z]{2,}\d+\b', query)
        codes.extend(pattern3)

        return list(set(codes))  # Remove duplicates

    def _exact_search(self, query: str, codes: List[str], top_k: int) -> List[Dict[str, Any]]:
        """Perform exact text matching for material codes.

        Args:
            query: Original query text.
            codes: Extracted codes to search for.
            top_k: Number of results to return.

        Returns:
            List of documents containing exact matches.
        """
        if not codes:
            return []

        logger.info(f"Exact search for codes: {codes}")

        # Get all documents from vector store (ChromaDB doesn't support text search directly)
        # We'll use get() with limit to retrieve many documents and filter in memory
        try:
            # Get a large batch of documents to search through
            all_docs = self.vector_store.collection.get(
                limit=10000,  # Adjust based on your collection size
                include=["documents", "metadatas"]
            )

            matches = []
            for i, content in enumerate(all_docs["documents"]):
                # Check if any code appears in the content
                content_lower = content.lower()
                for code in codes:
                    if code.lower() in content_lower:
                        # Calculate a simple match score based on occurrences
                        occurrences = content_lower.count(code.lower())
                        matches.append({
                            "id": all_docs["ids"][i],
                            "content": content,
                            "metadata": all_docs["metadatas"][i],
                            "distance": 0.0,  # Exact match gets best score
                            "similarity_score": 1.0,  # Perfect score for exact match
                            "match_type": "exact",
                            "match_count": occurrences
                        })
                        break  # Only add once per document

            # Sort by number of occurrences (more mentions = more relevant)
            matches.sort(key=lambda x: x["match_count"], reverse=True)

            logger.info(f"Found {len(matches)} exact matches")
            return matches[:top_k]

        except Exception as e:
            logger.warning(f"Exact search failed: {e}")
            return []

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant documents using hybrid search (exact + semantic).

        Args:
            query: Query text.
            top_k: Number of results to return. If None, uses configured value.
            filters: Metadata filters (e.g., {"doc_type": "pdf"}).

        Returns:
            List of retrieved documents with content, metadata, and scores.
        """
        top_k = top_k or self.top_k

        logger.info(f"Retrieving documents for query: '{query[:50]}...'")

        # Step 1: Extract potential codes/part numbers
        codes = self._extract_codes(query)

        # Step 2: Perform exact search for codes
        exact_results = []
        if codes:
            exact_results = self._exact_search(query, codes, top_k)
            logger.info(f"Hybrid search: Found {len(exact_results)} exact matches for codes: {codes}")

        # Step 3: Perform semantic search
        semantic_results = self.vector_store.query(
            query_text=query, n_results=top_k, where=filters
        )

        # Filter semantic results by similarity threshold
        filtered_semantic = []
        for doc in semantic_results:
            distance = doc["distance"]
            similarity = 1 / (1 + distance)

            if similarity >= self.similarity_threshold:
                doc["similarity_score"] = similarity
                doc["match_type"] = "semantic"
                filtered_semantic.append(doc)

        # Step 4: Combine and de-duplicate results
        combined = []
        seen_ids = set()

        # Prioritize exact matches
        for doc in exact_results:
            if doc["id"] not in seen_ids:
                combined.append(doc)
                seen_ids.add(doc["id"])

        # Add semantic matches
        for doc in filtered_semantic:
            if doc["id"] not in seen_ids:
                combined.append(doc)
                seen_ids.add(doc["id"])

        # Limit to top_k results
        final_results = combined[:top_k]

        logger.info(
            f"Retrieved {len(final_results)} documents "
            f"({len([d for d in final_results if d.get('match_type') == 'exact'])} exact, "
            f"{len([d for d in final_results if d.get('match_type') == 'semantic'])} semantic)"
        )

        return final_results

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

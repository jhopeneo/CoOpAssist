"""
Simple RAG workflow for QmanAssist.
Basic query → retrieve → generate workflow.
"""

from typing import Dict, Any, Optional
from loguru import logger

from src.rag.query_processor import QueryProcessor
from src.rag.retriever import DocumentRetriever
from src.rag.response_generator import ResponseGenerator


class SimpleRAGWorkflow:
    """Simple RAG workflow: Query → Retrieve → Generate."""

    def __init__(
        self,
        use_query_expansion: bool = False,
        top_k: int = None,
        include_sources: bool = True,
    ):
        """Initialize simple RAG workflow.

        Args:
            use_query_expansion: Whether to expand queries with LLM.
            top_k: Number of documents to retrieve.
            include_sources: Whether to include source citations.
        """
        self.query_processor = QueryProcessor(use_llm_expansion=use_query_expansion)
        self.retriever = DocumentRetriever(top_k=top_k)
        self.response_generator = ResponseGenerator(include_sources=include_sources)

        logger.info("SimpleRAGWorkflow initialized")

    def run(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the RAG workflow.

        Args:
            query: User query.
            filters: Optional metadata filters.

        Returns:
            Dictionary with answer, sources, and metadata.
        """
        logger.info(f"Running RAG workflow for query: '{query[:50]}...'")

        # Step 1: Process query
        processed_query = self.query_processor.process_query(query)
        query_type = self.query_processor.classify_query_type(query)

        logger.debug(f"Query type: {query_type}")

        # Step 2: Retrieve documents
        retrieval_result = self.retriever.retrieve_with_context(
            query=processed_query, filters=filters
        )

        documents = retrieval_result["documents"]
        logger.info(f"Retrieved {len(documents)} relevant documents")

        # Step 3: Generate response
        response = self.response_generator.generate_response(
            query=query, documents=documents
        )

        # Add workflow metadata
        response["workflow"] = {
            "type": "simple_rag",
            "query_type": query_type,
            "processed_query": processed_query,
            "retrieval_stats": {
                "num_results": retrieval_result["num_results"],
                "unique_sources": len(retrieval_result["unique_sources"]),
                "doc_types": retrieval_result["doc_types"],
            },
        }

        return response

    def run_with_multiple_queries(
        self, query: str, num_variants: int = 3
    ) -> Dict[str, Any]:
        """Run RAG workflow with multiple query variants for better recall.

        Args:
            query: Original user query.
            num_variants: Number of query variants to generate.

        Returns:
            Dictionary with answer, sources, and metadata.
        """
        logger.info(f"Running multi-query RAG for: '{query[:50]}...'")

        # Generate query variants
        queries = self.query_processor.generate_search_queries(query, num_variants)

        # Retrieve documents for each variant
        all_documents = []
        seen_ids = set()

        for variant in queries:
            docs = self.retriever.retrieve(query=variant)

            # Deduplicate by document ID
            for doc in docs:
                doc_id = doc["id"]
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_documents.append(doc)

        logger.info(
            f"Retrieved {len(all_documents)} unique documents from {len(queries)} queries"
        )

        # Generate response from all documents
        response = self.response_generator.generate_response(
            query=query, documents=all_documents
        )

        # Add workflow metadata
        response["workflow"] = {
            "type": "multi_query_rag",
            "num_query_variants": len(queries),
            "query_variants": queries,
            "total_documents": len(all_documents),
        }

        return response


# Convenience function
def ask_question(query: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to ask a question.

    Args:
        query: User question.
        **kwargs: Additional arguments for the workflow.

    Returns:
        Dictionary with answer and sources.
    """
    workflow = SimpleRAGWorkflow(**kwargs)
    return workflow.run(query)

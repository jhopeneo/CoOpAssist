"""
Semantic search tool for RAG-based question answering.
Handles queries like "What is", "How to", "Explain", etc.
"""

from typing import Dict, Any
from loguru import logger

from src.rag.retriever import DocumentRetriever
from src.rag.response_generator import ResponseGenerator


class SemanticSearchTool:
    """Tool for semantic search and RAG-based question answering."""

    def __init__(self, top_k: int = 10):
        """Initialize semantic search tool.

        Args:
            top_k: Number of chunks to retrieve.
        """
        self.retriever = DocumentRetriever(top_k=top_k)
        self.response_generator = ResponseGenerator(include_sources=True)
        logger.info(f"SemanticSearchTool initialized with top_k={top_k}")

    @property
    def name(self) -> str:
        """Tool name."""
        return "semantic_search"

    @property
    def description(self) -> str:
        """Tool description for the agent."""
        return """Search for and answer questions using semantic similarity.

Use this tool when the user asks:
- "What is X?"
- "How do I do X?"
- "Explain X"
- "What are the requirements for X?"
- "Tell me about X"

Input should be a dictionary with:
- query: the question or search term
- top_k: number of relevant chunks to retrieve (default 10)
- category: filter by document category (optional)

Returns a natural language answer based on the most relevant document chunks."""

    def run(self, query_params: Dict[str, Any]) -> str:
        """Execute semantic search and generate answer.

        Args:
            query_params: Dictionary with query, top_k, filters.

        Returns:
            Natural language answer with sources.
        """
        query = query_params.get("query", "")
        top_k = query_params.get("top_k", 10)
        category = query_params.get("category", None)

        if not query:
            return "Error: No query provided."

        logger.info(f"SemanticSearchTool: query='{query[:50]}...', top_k={top_k}")

        try:
            # Build filters
            filters = {}
            if category:
                filters["category"] = category

            # Retrieve relevant documents
            documents = self.retriever.retrieve(
                query=query,
                top_k=top_k,
                filters=filters if filters else None
            )

            if not documents:
                return f"I couldn't find any relevant information to answer: '{query}'\n\nTry rephrasing or asking about a different topic."

            # Generate response
            response = self.response_generator.generate_response(
                query=query,
                documents=documents
            )

            return response["answer"]

        except Exception as e:
            logger.error(f"Error in SemanticSearchTool: {e}")
            return f"Error performing semantic search: {str(e)}"

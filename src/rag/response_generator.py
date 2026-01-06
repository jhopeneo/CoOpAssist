"""
Response generator for QmanAssist.
Generates answers from retrieved documents with source citations.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from src.core.llm_factory import create_llm
from config.settings import get_settings


class ResponseGenerator:
    """Generates responses from retrieved documents."""

    def __init__(self, include_sources: bool = True, streaming: bool = False):
        """Initialize response generator.

        Args:
            include_sources: Whether to include source citations.
            streaming: Whether to use streaming responses.
        """
        self.settings = get_settings()
        self.include_sources = include_sources
        self.streaming = streaming
        self.llm = create_llm()

        logger.info(
            f"ResponseGenerator initialized: sources={include_sources}, "
            f"streaming={streaming}"
        )

    def generate_response(
        self, query: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a response from retrieved documents.

        Args:
            query: User query.
            documents: List of retrieved documents with content and metadata.

        Returns:
            Dictionary with response and metadata.
        """
        if not documents:
            return self._generate_no_results_response(query)

        # Build context from documents
        context = self._build_context(documents)

        # Generate response
        prompt = self._build_prompt(query, context)

        try:
            if self.streaming:
                # For streaming, return generator
                response_stream = self.llm.stream(prompt)
                return {
                    "answer": response_stream,
                    "sources": self._extract_sources(documents),
                    "num_sources": len(documents),
                    "streaming": True,
                }
            else:
                # Regular response
                response = self.llm.invoke(prompt)
                answer = (
                    response.content if hasattr(response, "content") else str(response)
                )

                # Add citations
                if self.include_sources:
                    answer = self._add_citations(answer, documents)

                return {
                    "answer": answer,
                    "sources": self._extract_sources(documents),
                    "num_sources": len(documents),
                    "streaming": False,
                }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": "I apologize, but I encountered an error generating a response. Please try rephrasing your question.",
                "sources": [],
                "num_sources": 0,
                "error": str(e),
            }

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents.

        Args:
            documents: List of retrieved documents.

        Returns:
            Formatted context string.
        """
        context_parts = []

        for i, doc in enumerate(documents, start=1):
            content = doc["content"]
            metadata = doc["metadata"]

            # Format source info
            source = Path(metadata.get("source", "Unknown")).name
            page = metadata.get("page_number", "")
            page_info = f", Page {page}" if page else ""

            # Add document to context
            context_parts.append(
                f"[Source {i}: {source}{page_info}]\n{content}\n"
            )

        return "\n\n".join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """Build the prompt for the LLM.

        Args:
            query: User query.
            context: Context from retrieved documents.

        Returns:
            Formatted prompt.
        """
        prompt = f"""You are QmanAssist, an AI assistant helping employees at Neocon International answer questions about quality documentation and procedures.

Use the following context from our quality manuals to answer the question. If the answer is not in the context, say so clearly. Always be specific and cite which document or section your answer comes from.

Context from quality manuals:
{context}

Question: {query}

Answer (be specific and reference the source documents):"""

        return prompt

    def _add_citations(
        self, answer: str, documents: List[Dict[str, Any]]
    ) -> str:
        """Add source citations to the answer.

        Args:
            answer: Generated answer.
            documents: Source documents.

        Returns:
            Answer with citations appended.
        """
        if not documents:
            return answer

        # Extract unique sources
        sources = self._extract_sources(documents)

        # Format citations
        citations = ["\n\n**Sources:**"]
        for i, source_info in enumerate(sources, start=1):
            source_name = Path(source_info["file"]).name
            page = source_info.get("page", "")
            page_info = f" (Page {page})" if page else ""

            citations.append(f"{i}. {source_name}{page_info}")

        return answer + "\n".join(citations)

    def _extract_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract unique source information from documents.

        Args:
            documents: List of documents.

        Returns:
            List of unique source information.
        """
        seen_sources = set()
        sources = []

        for doc in documents:
            metadata = doc["metadata"]
            source = metadata.get("source", "Unknown")
            page = metadata.get("page_number", "")

            # Create unique identifier
            source_id = f"{source}:{page}"

            if source_id not in seen_sources:
                seen_sources.add(source_id)
                sources.append({
                    "file": source,
                    "page": page,
                    "doc_type": metadata.get("doc_type", "unknown"),
                })

        return sources

    def _generate_no_results_response(self, query: str) -> Dict[str, Any]:
        """Generate response when no documents are found.

        Args:
            query: User query.

        Returns:
            Response dictionary.
        """
        answer = (
            f"I couldn't find any relevant information in the quality documentation "
            f"to answer your question: '{query}'\n\n"
            f"This could mean:\n"
            f"- The information hasn't been indexed yet\n"
            f"- The topic isn't covered in the current documentation\n"
            f"- Try rephrasing your question with different terms\n\n"
            f"Please contact your quality manager if you need assistance."
        )

        return {
            "answer": answer,
            "sources": [],
            "num_sources": 0,
            "no_results": True,
        }

    def generate_summary(self, documents: List[Dict[str, Any]]) -> str:
        """Generate a summary of multiple documents.

        Args:
            documents: List of documents to summarize.

        Returns:
            Summary text.
        """
        if not documents:
            return "No documents to summarize."

        context = self._build_context(documents)

        prompt = f"""Summarize the key information from these quality documentation excerpts. Focus on the main points and procedures.

Context:
{context}

Summary:"""

        try:
            response = self.llm.invoke(prompt)
            summary = (
                response.content if hasattr(response, "content") else str(response)
            )
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Error generating summary."

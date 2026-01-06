"""
Query processor for QmanAssist.
Enhances user queries for better retrieval through expansion and rephrasing.
"""

from typing import List, Optional
from loguru import logger

from src.core.llm_factory import create_llm
from config.settings import get_settings


class QueryProcessor:
    """Processes and enhances user queries."""

    def __init__(self, use_llm_expansion: bool = False):
        """Initialize query processor.

        Args:
            use_llm_expansion: Whether to use LLM for query expansion.
        """
        self.use_llm_expansion = use_llm_expansion
        self.settings = get_settings()

        if use_llm_expansion:
            self.llm = create_llm(temperature=0.3)  # Lower temp for focused expansion

        logger.info(f"QueryProcessor initialized: llm_expansion={use_llm_expansion}")

    def process_query(self, query: str) -> str:
        """Process a user query.

        Args:
            query: Original user query.

        Returns:
            Processed query.
        """
        # Clean the query
        cleaned_query = self._clean_query(query)

        # Optionally expand with LLM
        if self.use_llm_expansion:
            expanded_query = self._expand_with_llm(cleaned_query)
            return expanded_query

        return cleaned_query

    def generate_search_queries(self, query: str, num_variants: int = 3) -> List[str]:
        """Generate multiple search query variants.

        Args:
            query: Original user query.
            num_variants: Number of query variants to generate.

        Returns:
            List of query variants.
        """
        if not self.use_llm_expansion:
            # Simple variants without LLM
            return [query]

        prompt = f"""Given this question about quality documentation, generate {num_variants} different search queries that would help find relevant information. Make the queries specific and focused.

Original question: {query}

Generate {num_variants} search queries (one per line):"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse variants
            variants = [line.strip() for line in content.split("\n") if line.strip()]
            variants = [v.lstrip("0123456789.-) ") for v in variants]  # Remove numbering

            # Keep original query as first variant
            all_queries = [query] + variants[:num_variants]

            logger.info(f"Generated {len(all_queries)} query variants")
            return all_queries

        except Exception as e:
            logger.error(f"Error generating query variants: {e}")
            return [query]

    def extract_keywords(self, query: str) -> List[str]:
        """Extract key terms from the query.

        Args:
            query: User query.

        Returns:
            List of keywords.
        """
        # Simple keyword extraction (can be enhanced with NLP)
        stop_words = {
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "is",
            "are",
            "was",
            "were",
            "the",
            "a",
            "an",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
        }

        # Tokenize and filter
        words = query.lower().split()
        keywords = [
            word.strip(".,!?;:")
            for word in words
            if word.lower() not in stop_words and len(word) > 2
        ]

        return keywords

    def classify_query_type(self, query: str) -> str:
        """Classify the type of query.

        Args:
            query: User query.

        Returns:
            Query type (e.g., 'factual', 'procedural', 'comparison').
        """
        query_lower = query.lower()

        # Check for question words
        if any(
            query_lower.startswith(word) for word in ["what is", "what are", "define"]
        ):
            return "factual"

        if any(
            query_lower.startswith(word) for word in ["how to", "how do", "steps"]
        ):
            return "procedural"

        if "compare" in query_lower or "difference" in query_lower:
            return "comparison"

        if "why" in query_lower:
            return "explanation"

        if "list" in query_lower or "all" in query_lower:
            return "enumeration"

        return "general"

    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query.

        Args:
            query: Raw query text.

        Returns:
            Cleaned query.
        """
        # Remove excessive whitespace
        query = " ".join(query.split())

        # Remove trailing punctuation
        query = query.rstrip("?!.")

        return query.strip()

    def _expand_with_llm(self, query: str) -> str:
        """Expand query using LLM.

        Args:
            query: Original query.

        Returns:
            Expanded query.
        """
        prompt = f"""Given this question about quality documentation, rephrase it to be more specific and include relevant terminology that would help find the answer in technical documents.

Original question: {query}

Rephrased question (keep it concise, one sentence):"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            expanded = content.strip()

            logger.debug(f"Query expansion: '{query}' -> '{expanded}'")
            return expanded

        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return query

    def suggest_filters(self, query: str) -> dict:
        """Suggest metadata filters based on query content.

        Args:
            query: User query.

        Returns:
            Dictionary of suggested filters.
        """
        filters = {}
        query_lower = query.lower()

        # Detect document type mentions
        if "pdf" in query_lower or "document" in query_lower:
            filters["doc_type"] = "pdf"
        elif "spreadsheet" in query_lower or "excel" in query_lower:
            filters["doc_type"] = "excel"
        elif "table" in query_lower:
            filters["has_tables"] = True

        return filters if filters else None

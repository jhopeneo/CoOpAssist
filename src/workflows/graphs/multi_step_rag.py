"""
Multi-step RAG workflow for QmanAssist.
Handles complex queries with query decomposition and multi-step reasoning.
"""

from typing import Dict, Any, List
from loguru import logger

from src.core.llm_factory import create_llm
from src.rag.query_processor import QueryProcessor
from src.rag.retriever import DocumentRetriever
from src.rag.response_generator import ResponseGenerator


class MultiStepRAGWorkflow:
    """Multi-step RAG workflow for complex queries."""

    def __init__(self, top_k: int = None):
        """Initialize multi-step RAG workflow.

        Args:
            top_k: Number of documents to retrieve per sub-query.
        """
        self.llm = create_llm(temperature=0.3)
        self.query_processor = QueryProcessor()
        self.retriever = DocumentRetriever(top_k=top_k or 3)
        self.response_generator = ResponseGenerator()

        logger.info("MultiStepRAGWorkflow initialized")

    def run(self, query: str) -> Dict[str, Any]:
        """Run the multi-step RAG workflow.

        Args:
            query: Complex user query.

        Returns:
            Dictionary with answer, sources, and reasoning steps.
        """
        logger.info(f"Running multi-step RAG for query: '{query[:50]}...'")

        # Step 1: Determine if query needs decomposition
        needs_decomposition = self._needs_decomposition(query)

        if not needs_decomposition:
            logger.info("Query doesn't need decomposition, using simple workflow")
            from src.workflows.graphs.simple_rag import SimpleRAGWorkflow

            simple_workflow = SimpleRAGWorkflow()
            return simple_workflow.run(query)

        # Step 2: Decompose query into sub-questions
        sub_questions = self._decompose_query(query)
        logger.info(f"Decomposed into {len(sub_questions)} sub-questions")

        # Step 3: Answer each sub-question
        sub_answers = []
        all_sources = []

        for i, sub_q in enumerate(sub_questions, start=1):
            logger.info(f"Processing sub-question {i}/{len(sub_questions)}: {sub_q}")

            # Retrieve and answer
            docs = self.retriever.retrieve(query=sub_q)
            sub_response = self.response_generator.generate_response(
                query=sub_q, documents=docs
            )

            sub_answers.append({
                "question": sub_q,
                "answer": sub_response["answer"],
                "sources": sub_response["sources"],
            })

            # Collect sources
            all_sources.extend(sub_response["sources"])

        # Step 4: Synthesize final answer
        final_answer = self._synthesize_answer(query, sub_answers)

        # Deduplicate sources
        unique_sources = self._deduplicate_sources(all_sources)

        return {
            "answer": final_answer,
            "sources": unique_sources,
            "num_sources": len(unique_sources),
            "workflow": {
                "type": "multi_step_rag",
                "sub_questions": sub_questions,
                "sub_answers": sub_answers,
                "reasoning_steps": len(sub_questions),
            },
        }

    def _needs_decomposition(self, query: str) -> bool:
        """Determine if a query needs to be decomposed.

        Args:
            query: User query.

        Returns:
            True if query should be decomposed.
        """
        # Simple heuristics
        indicators = [
            "and",
            "compare",
            "difference between",
            "steps",
            "process",
            "multiple",
            "both",
            "all",
        ]

        query_lower = query.lower()

        # Check for indicators
        has_indicators = any(indicator in query_lower for indicator in indicators)

        # Check for multiple questions
        has_multiple_questions = query.count("?") > 1

        # Check query length (longer queries often need decomposition)
        is_long = len(query.split()) > 15

        return has_indicators or has_multiple_questions or is_long

    def _decompose_query(self, query: str) -> List[str]:
        """Decompose a complex query into sub-questions.

        Args:
            query: Complex query.

        Returns:
            List of sub-questions.
        """
        prompt = f"""Break down this complex question about quality documentation into 2-4 simpler sub-questions that can be answered independently. Each sub-question should focus on one specific aspect.

Complex question: {query}

Sub-questions (one per line, numbered):"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse sub-questions
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            sub_questions = []

            for line in lines:
                # Remove numbering
                clean_line = line.lstrip("0123456789.-) ")
                if clean_line and len(clean_line) > 10:  # Filter out too-short lines
                    sub_questions.append(clean_line)

            # Fallback if parsing failed
            if not sub_questions:
                logger.warning("Failed to parse sub-questions, using original query")
                return [query]

            return sub_questions[:4]  # Limit to 4 sub-questions

        except Exception as e:
            logger.error(f"Error decomposing query: {e}")
            return [query]

    def _synthesize_answer(
        self, original_query: str, sub_answers: List[Dict[str, Any]]
    ) -> str:
        """Synthesize final answer from sub-answers.

        Args:
            original_query: Original user query.
            sub_answers: List of sub-question answers.

        Returns:
            Synthesized final answer.
        """
        # Build context from sub-answers
        context_parts = []
        for i, sub in enumerate(sub_answers, start=1):
            context_parts.append(
                f"Sub-question {i}: {sub['question']}\n"
                f"Answer: {sub['answer']}\n"
            )

        context = "\n".join(context_parts)

        prompt = f"""Based on the answers to these sub-questions, provide a comprehensive answer to the original question. Synthesize the information coherently and reference the relevant parts.

Original question: {original_query}

Information from sub-questions:
{context}

Comprehensive answer:"""

        try:
            response = self.llm.invoke(prompt)
            answer = (
                response.content if hasattr(response, "content") else str(response)
            )
            return answer

        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")

            # Fallback: concatenate sub-answers
            fallback = f"Here's what I found:\n\n"
            for i, sub in enumerate(sub_answers, start=1):
                fallback += f"**{sub['question']}**\n{sub['answer']}\n\n"

            return fallback

    def _deduplicate_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate sources.

        Args:
            sources: List of source dictionaries.

        Returns:
            Deduplicated list of sources.
        """
        seen = set()
        unique_sources = []

        for source in sources:
            # Create unique key
            key = f"{source['file']}:{source.get('page', '')}"

            if key not in seen:
                seen.add(key)
                unique_sources.append(source)

        return unique_sources

#!/usr/bin/env python3
"""
Test script for IntelligentAgent to verify intent detection and tool routing.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.workflows.graphs.intelligent_agent import IntelligentAgent
from loguru import logger

# Test queries covering all intent types
TEST_QUERIES = [
    {
        "query": "How many process instructions do we have?",
        "expected_intent": "count",
        "expected_tool": "metadata_query",
        "description": "Count query - should count specific doc type"
    },
    {
        "query": "How many documents are in the database?",
        "expected_intent": "count",
        "expected_tool": "metadata_query",
        "description": "Count query - general count"
    },
    {
        "query": "List all work instructions",
        "expected_intent": "list",
        "expected_tool": "document_list",
        "description": "List query - enumerate documents"
    },
    {
        "query": "Show me process instructions for welding",
        "expected_intent": "list",
        "expected_tool": "document_list",
        "description": "List query - filtered by topic"
    },
    {
        "query": "What documents were recently updated?",
        "expected_intent": "recent",
        "expected_tool": "metadata_query",
        "description": "Recent query - show recent changes"
    },
    {
        "query": "What categories of documents do we have?",
        "expected_intent": "categories",
        "expected_tool": "metadata_query",
        "description": "Categories query - list doc categories"
    },
    {
        "query": "What is PPAP?",
        "expected_intent": "factual",
        "expected_tool": "semantic_search",
        "description": "Factual query - definition/explanation"
    },
    {
        "query": "How do I perform a quality inspection?",
        "expected_intent": "procedural",
        "expected_tool": "semantic_search",
        "description": "Procedural query - how-to question"
    },
    {
        "query": "Find information about environmental procedures",
        "expected_intent": "search",
        "expected_tool": "semantic_search",
        "description": "Search query - general content search"
    },
]


def test_agent():
    """Test the intelligent agent with various query types."""

    logger.info("="*80)
    logger.info("Starting IntelligentAgent Tests")
    logger.info("="*80)

    # Initialize agent
    try:
        agent = IntelligentAgent(top_k=5)
        logger.success("✅ Agent initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize agent: {e}")
        return False

    # Test each query
    results = []
    for i, test_case in enumerate(TEST_QUERIES, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Test {i}/{len(TEST_QUERIES)}: {test_case['description']}")
        logger.info(f"Query: '{test_case['query']}'")
        logger.info(f"Expected: intent={test_case['expected_intent']}, tool={test_case['expected_tool']}")
        logger.info(f"{'='*80}")

        try:
            # Run the agent
            result = agent.run(test_case['query'])

            # Check results
            actual_intent = result.get("intent", "unknown")
            actual_tool = result.get("tool_used", "unknown")
            answer = result.get("answer", "")

            # Validate
            intent_match = actual_intent == test_case["expected_intent"]
            tool_match = actual_tool == test_case["expected_tool"]

            status = "✅ PASS" if (intent_match and tool_match) else "❌ FAIL"

            logger.info(f"\nResults:")
            logger.info(f"  Intent: {actual_intent} {'✅' if intent_match else '❌'}")
            logger.info(f"  Tool: {actual_tool} {'✅' if tool_match else '❌'}")
            logger.info(f"  Answer preview: {answer[:150]}...")
            logger.info(f"\n{status}")

            results.append({
                "test": test_case["description"],
                "query": test_case["query"],
                "passed": intent_match and tool_match,
                "expected_intent": test_case["expected_intent"],
                "actual_intent": actual_intent,
                "expected_tool": test_case["expected_tool"],
                "actual_tool": actual_tool,
            })

        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            logger.exception("Full traceback:")
            results.append({
                "test": test_case["description"],
                "query": test_case["query"],
                "passed": False,
                "error": str(e)
            })

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*80}")

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    logger.info(f"\nResults: {passed}/{total} tests passed")
    logger.info(f"\nDetailed Results:")

    for r in results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        logger.info(f"\n{status} - {r['test']}")
        logger.info(f"  Query: {r['query']}")

        if "error" in r:
            logger.info(f"  Error: {r['error']}")
        else:
            if not r["passed"]:
                logger.info(f"  Expected: intent={r['expected_intent']}, tool={r['expected_tool']}")
                logger.info(f"  Actual: intent={r['actual_intent']}, tool={r['actual_tool']}")

    logger.info(f"\n{'='*80}")

    if passed == total:
        logger.success(f"🎉 All {total} tests passed!")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = test_agent()
    sys.exit(0 if success else 1)

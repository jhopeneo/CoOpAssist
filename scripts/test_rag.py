#!/usr/bin/env python3
"""
Test the RAG system for QmanAssist.
Interactive script to test retrieval and response generation.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.logging_config import setup_logging
from src.workflows.graphs.simple_rag import SimpleRAGWorkflow
from src.workflows.graphs.multi_step_rag import MultiStepRAGWorkflow
from src.core.vector_store import get_vector_store
from config.settings import get_settings


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test QmanAssist RAG system")

    parser.add_argument(
        "--query",
        type=str,
        help="Query to test (if not provided, enters interactive mode)",
    )

    parser.add_argument(
        "--workflow",
        type=str,
        choices=["simple", "multi-step"],
        default="simple",
        help="Workflow type to use",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of documents to retrieve",
    )

    parser.add_argument(
        "--expand-query",
        action="store_true",
        help="Use LLM query expansion",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    return parser.parse_args()


def test_single_query(query: str, workflow_type: str, **kwargs):
    """Test a single query.

    Args:
        query: Query to test.
        workflow_type: Type of workflow to use.
        **kwargs: Additional workflow arguments.
    """
    print("\n" + "=" * 60)
    print(f"Query: {query}")
    print("=" * 60)

    # Select workflow
    if workflow_type == "multi-step":
        workflow = MultiStepRAGWorkflow(top_k=kwargs.get("top_k"))
    else:
        workflow = SimpleRAGWorkflow(
            use_query_expansion=kwargs.get("expand_query", False),
            top_k=kwargs.get("top_k"),
        )

    # Run workflow
    try:
        result = workflow.run(query)

        # Display answer
        print("\n📝 Answer:")
        print("-" * 60)
        print(result["answer"])

        # Display sources
        if result["sources"]:
            print("\n📚 Sources:")
            print("-" * 60)
            for i, source in enumerate(result["sources"], start=1):
                source_name = Path(source["file"]).name
                page = source.get("page", "")
                page_info = f" (Page {page})" if page else ""
                print(f"{i}. {source_name}{page_info}")

        # Display workflow info
        if "workflow" in result:
            print("\n🔧 Workflow Info:")
            print("-" * 60)
            workflow_info = result["workflow"]
            print(f"Type: {workflow_info.get('type', 'unknown')}")

            if "retrieval_stats" in workflow_info:
                stats = workflow_info["retrieval_stats"]
                print(f"Documents retrieved: {stats.get('num_results', 0)}")
                print(f"Unique sources: {stats.get('unique_sources', 0)}")

            if "sub_questions" in workflow_info:
                print(f"\nSub-questions:")
                for i, sub_q in enumerate(workflow_info["sub_questions"], start=1):
                    print(f"  {i}. {sub_q}")

        print("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"Error testing query: {e}")
        logger.exception("Full traceback:")
        print(f"\n❌ Error: {e}")


def interactive_mode(workflow_type: str, **kwargs):
    """Run in interactive mode.

    Args:
        workflow_type: Type of workflow to use.
        **kwargs: Additional workflow arguments.
    """
    print("\n" + "=" * 60)
    print("QmanAssist RAG System - Interactive Test Mode")
    print("=" * 60)
    print("\nCommands:")
    print("  - Enter a question to get an answer")
    print("  - 'stats' to see database statistics")
    print("  - 'switch' to change workflow type")
    print("  - 'quit' or 'exit' to exit")
    print()

    current_workflow = workflow_type

    while True:
        try:
            # Get user input
            query = input("\n💬 Your question: ").strip()

            if not query:
                continue

            # Handle commands
            if query.lower() in ["quit", "exit", "q"]:
                print("\nGoodbye!")
                break

            elif query.lower() == "stats":
                show_stats()
                continue

            elif query.lower() == "switch":
                current_workflow = (
                    "multi-step" if current_workflow == "simple" else "simple"
                )
                print(f"\n✓ Switched to {current_workflow} workflow")
                continue

            # Process query
            test_single_query(query, current_workflow, **kwargs)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break

        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"\n❌ Error: {e}")


def show_stats():
    """Display vector store statistics."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_collection_stats()

        print("\n" + "=" * 60)
        print("Database Statistics")
        print("=" * 60)
        print(f"Collection: {stats['collection_name']}")
        print(f"Total documents: {stats['document_count']}")

        if stats['doc_types']:
            print(f"\nDocument types:")
            for doc_type, count in stats['doc_types'].items():
                print(f"  - {doc_type}: {count}")

        print("=" * 60)

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        print(f"\n❌ Error getting stats: {e}")


def main():
    """Main function."""
    args = parse_args()

    # Setup logging
    setup_logging(log_level=args.log_level)

    # Load settings
    settings = get_settings()

    # Check API key
    if not settings.validate_api_key():
        logger.error(
            f"\nAPI key not configured for provider: {settings.llm_provider}\n"
            f"Please set the appropriate API key in .env file"
        )
        return 1

    # Check if vector store has data
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_collection_stats()

        if stats["document_count"] == 0:
            logger.warning(
                "\n⚠️  Vector store is empty. Please run document ingestion first:\n"
                "   python scripts/ingest_documents.py"
            )
            print("\nContinue anyway? (y/n): ", end="")
            response = input().strip().lower()
            if response != "y":
                return 0

    except Exception as e:
        logger.error(f"Error checking vector store: {e}")
        return 1

    # Prepare kwargs
    kwargs = {
        "top_k": args.top_k,
        "expand_query": args.expand_query,
    }

    # Run test
    if args.query:
        # Single query mode
        test_single_query(args.query, args.workflow, **kwargs)
    else:
        # Interactive mode
        interactive_mode(args.workflow, **kwargs)

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Ingest documents from Q:\ drive into QmanAssist vector store.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.logging_config import setup_logging
from src.utils.network_utils import validate_network_access
from src.ingestion.pipeline import IngestionPipeline
from src.core.vector_store import get_vector_store
from config.settings import get_settings


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest documents from Q:\\ drive into QmanAssist"
    )

    parser.add_argument(
        "--source",
        type=str,
        help="Source directory to ingest from (default: configured Q:\\ path)",
    )

    parser.add_argument(
        "--file-types",
        type=str,
        nargs="+",
        help="File types to ingest (e.g., .pdf .docx .xlsx)",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't search subdirectories recursively",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest all documents (don't skip existing)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    return parser.parse_args()


def main():
    """Main ingestion function."""
    args = parse_args()

    # Setup logging
    setup_logging(log_level=args.log_level)

    logger.info("=" * 60)
    logger.info("QmanAssist - Document Ingestion")
    logger.info("=" * 60)

    # Load settings
    settings = get_settings()

    # Validate API key
    if not settings.validate_api_key():
        logger.error(
            f"\nAPI key not configured for provider: {settings.llm_provider}\n"
            f"Please set the appropriate API key in .env file:\n"
            f"  - OpenAI: OPENAI_API_KEY\n"
            f"  - Claude: ANTHROPIC_API_KEY"
        )
        return 1

    # Validate network access
    logger.info("\nValidating network access...")
    success, message = validate_network_access()

    if not success:
        logger.error(f"\nNetwork access validation failed: {message}")
        logger.error("\nPlease ensure:")
        logger.error("  1. Q:\\ drive is mapped (Windows) or mounted (Linux)")
        logger.error("  2. You have read permissions")
        logger.error("  3. Path is set correctly in .env file")
        return 1

    logger.info(f"✓ {message}")

    # Determine source directory
    source_dir = None
    if args.source:
        source_dir = Path(args.source)
        logger.info(f"\nSource directory: {source_dir}")
    else:
        logger.info(f"\nUsing configured path: {settings.qmanuals_path}")

    # Initialize pipeline
    logger.info("\nInitializing ingestion pipeline...")
    pipeline = IngestionPipeline(skip_existing=not args.force)

    # Show current vector store stats
    vector_store = get_vector_store()
    initial_stats = vector_store.get_collection_stats()
    logger.info(f"\nCurrent vector store status:")
    logger.info(f"  Documents: {initial_stats['document_count']}")

    # Run ingestion
    logger.info("\n" + "=" * 60)
    logger.info("Starting document ingestion...")
    logger.info("=" * 60)

    try:
        stats = pipeline.ingest_directory(
            directory=source_dir,
            recursive=not args.no_recursive,
            file_types=args.file_types,
        )

        # Show final results
        logger.info("\n" + "=" * 60)
        logger.info("Ingestion Complete!")
        logger.info("=" * 60)

        logger.info(f"\nResults:")
        logger.info(f"  Total files found: {stats['total_files']}")
        logger.info(f"  Successfully processed: {stats['successful']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Skipped (existing): {stats['skipped']}")
        logger.info(f"  Total chunks added: {stats['total_chunks']}")

        # Show updated vector store stats
        final_stats = vector_store.get_collection_stats()
        logger.info(f"\nVector store status:")
        logger.info(f"  Total documents: {final_stats['document_count']}")
        logger.info(f"  Document types:")
        for doc_type, count in final_stats['doc_types'].items():
            logger.info(f"    - {doc_type}: {count}")

        logger.info("\nNext step:")
        logger.info("  Launch the app: streamlit run src/ui/app.py")

        return 0

    except KeyboardInterrupt:
        logger.warning("\n\nIngestion interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"\nError during ingestion: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())

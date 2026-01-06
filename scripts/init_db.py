#!/usr/bin/env python3
"""
Initialize ChromaDB for QmanAssist.
Creates the vector store and verifies configuration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.utils.logging_config import setup_logging
from src.core.vector_store import VectorStore, get_vector_store
from config.settings import get_settings


def main():
    """Initialize the database."""
    # Setup logging
    setup_logging()

    logger.info("=" * 60)
    logger.info("QmanAssist - Database Initialization")
    logger.info("=" * 60)

    # Load settings
    settings = get_settings()

    logger.info(f"Collection name: {settings.chroma_collection_name}")
    logger.info(f"Persist directory: {settings.chroma_db_path}")
    logger.info(f"Embedding provider: {settings.embedding_provider}")
    logger.info(f"Embedding model: {settings.embedding_model}")

    # Check API keys
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            logger.error("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")
            sys.exit(1)
        logger.info("✓ OpenAI API key configured")

    try:
        # Initialize vector store
        logger.info("\nInitializing vector store...")
        vector_store = get_vector_store()

        # Get stats
        stats = vector_store.get_collection_stats()

        logger.info("\n" + "=" * 60)
        logger.info("Database initialized successfully!")
        logger.info("=" * 60)
        logger.info(f"Collection: {stats['collection_name']}")
        logger.info(f"Document count: {stats['document_count']}")
        logger.info(f"Storage path: {stats['persist_directory']}")

        if stats['document_count'] > 0:
            logger.info(f"\nDocument types:")
            for doc_type, count in stats['doc_types'].items():
                logger.info(f"  - {doc_type}: {count}")

        logger.info("\nDatabase is ready to use!")
        logger.info("\nNext steps:")
        logger.info("  1. Run: python scripts/ingest_documents.py")
        logger.info("  2. Start the app: streamlit run src/ui/app.py")

        return 0

    except Exception as e:
        logger.error(f"\nError initializing database: {e}")
        logger.error("\nPlease check:")
        logger.error("  1. Your .env file is configured correctly")
        logger.error("  2. API keys are valid")
        logger.error("  3. ChromaDB directory is writable")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Vector store wrapper for QmanAssist.
Provides a clean interface to ChromaDB for storing and retrieving document embeddings.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from config.settings import get_settings
from src.core.llm_factory import create_embeddings
from src.ingestion.loaders.base_loader import Document


class VectorStore:
    """ChromaDB vector store wrapper."""

    def __init__(
        self,
        collection_name: str = None,
        persist_directory: str = None,
        embedding_function=None,
    ):
        """Initialize vector store.

        Args:
            collection_name: Name of the ChromaDB collection. If None, uses setting.
            persist_directory: Directory for persistent storage. If None, uses setting.
            embedding_function: Custom embedding function. If None, uses configured embeddings.
        """
        settings = get_settings()
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_directory = persist_directory or settings.chroma_db_path

        # Ensure persist directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.Client(
            ChromaSettings(
                persist_directory=self.persist_directory,
                anonymized_telemetry=False,
            )
        )

        # Set up embedding function
        if embedding_function is None:
            embedding_function = self._create_embedding_function()

        self.embedding_function = embedding_function

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name, embedding_function=self.embedding_function
        )

        logger.info(
            f"VectorStore initialized: collection='{self.collection_name}', "
            f"path='{self.persist_directory}'"
        )

    def _create_embedding_function(self):
        """Create ChromaDB-compatible embedding function."""
        settings = get_settings()

        if settings.embedding_provider == "openai":
            # Use OpenAI embeddings
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name=settings.embedding_model,
            )
        else:
            # Use sentence transformers (local)
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model
            )

    def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to the vector store.

        Args:
            documents: List of Document objects to add.

        Returns:
            List of document IDs added.
        """
        if not documents:
            logger.warning("No documents to add")
            return []

        # Prepare data for ChromaDB
        ids = []
        texts = []
        metadatas = []

        for doc in documents:
            doc_id = doc.metadata.get("doc_id", None)
            if not doc_id:
                # Generate ID if not present
                import hashlib

                doc_id = hashlib.sha256(doc.content.encode()).hexdigest()[:16]

            ids.append(doc_id)
            texts.append(doc.content)
            metadatas.append(doc.metadata)

        # Add to collection
        try:
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

            logger.info(f"Added {len(documents)} documents to vector store")
            return ids

        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query the vector store for similar documents.

        Args:
            query_text: Query text to search for.
            n_results: Number of results to return.
            where: Metadata filter conditions.
            where_document: Document content filter conditions.

        Returns:
            List of matching documents with metadata and scores.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where,
                where_document=where_document,
            )

            # Format results
            documents = []
            if results["documents"] and results["documents"][0]:
                for i, doc_text in enumerate(results["documents"][0]):
                    doc_data = {
                        "id": results["ids"][0][i],
                        "content": doc_text,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                    }
                    documents.append(doc_data)

            logger.info(f"Query returned {len(documents)} results")
            return documents

        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            raise

    def delete_by_source(self, source_path: str) -> int:
        """Delete all documents from a specific source file.

        Args:
            source_path: Path to the source file.

        Returns:
            Number of documents deleted.
        """
        try:
            # Get all documents from this source
            results = self.collection.get(where={"source": str(source_path)})

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                count = len(results["ids"])
                logger.info(f"Deleted {count} documents from source: {source_path}")
                return count

            return 0

        except Exception as e:
            logger.error(f"Error deleting documents from source {source_path}: {e}")
            raise

    def delete_collection(self):
        """Delete the entire collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics.
        """
        try:
            count = self.collection.count()

            # Get sample metadata to determine doc types
            sample = self.collection.get(limit=100)
            doc_types = {}
            if sample["metadatas"]:
                for metadata in sample["metadatas"]:
                    doc_type = metadata.get("doc_type", "unknown")
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            stats = {
                "collection_name": self.collection_name,
                "document_count": count,
                "doc_types": doc_types,
                "persist_directory": self.persist_directory,
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise

    def document_exists(self, doc_id: str) -> bool:
        """Check if a document with the given ID exists.

        Args:
            doc_id: Document ID to check.

        Returns:
            True if document exists, False otherwise.
        """
        try:
            result = self.collection.get(ids=[doc_id])
            return len(result["ids"]) > 0
        except Exception as e:
            logger.error(f"Error checking document existence: {e}")
            return False


# Global vector store instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance.

    Returns:
        VectorStore instance.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


def reset_vector_store():
    """Reset the global vector store instance."""
    global _vector_store_instance
    _vector_store_instance = None

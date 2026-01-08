"""
Document ingestion pipeline for QmanAssist.
Orchestrates the entire process: load → chunk → enrich → embed → store.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing

from config.settings import get_settings
from src.utils.network_utils import NetworkPathAccessor
from src.ingestion.loaders.base_loader import Document
from src.ingestion.loaders.pdf_loader import PDFLoader
from src.ingestion.loaders.docx_loader import WordDocumentLoader
from src.ingestion.loaders.excel_loader import ExcelLoader
from src.ingestion.chunkers.semantic_chunker import SemanticChunker
from src.ingestion.chunkers.table_chunker import TableChunker
from src.ingestion.chunkers.metadata_enricher import MetadataEnricher
from src.core.vector_store import VectorStore, get_vector_store


def _process_single_file(file_path: Path, skip_existing: bool) -> Dict[str, Any]:
    """Process a single file for parallel ingestion.

    This is a module-level function to support multiprocessing.

    Args:
        file_path: Path to the file to process.
        skip_existing: Whether to skip existing documents.

    Returns:
        Dictionary with processing result including documents ready for vector store.
    """
    from src.ingestion.loaders.pdf_loader import PDFLoader
    from src.ingestion.loaders.docx_loader import WordDocumentLoader
    from src.ingestion.loaders.excel_loader import ExcelLoader
    from src.ingestion.chunkers.semantic_chunker import SemanticChunker
    from src.ingestion.chunkers.table_chunker import TableChunker
    from src.ingestion.chunkers.metadata_enricher import MetadataEnricher
    from src.utils.network_utils import NetworkPathAccessor
    from config.settings import get_settings
    import smbclient
    from smbclient import register_session

    try:
        # Initialize SMB session for this worker process
        # Each worker process needs its own SMB session registration
        settings = get_settings()
        if settings.is_network_path():
            path_str = settings.qmanuals_network_path
            parts = path_str.replace("\\\\", "//").strip("/").split("/")
            server = parts[0] if parts else "neonas-01"

            if settings.smb_username and settings.smb_password:
                username_with_domain = f"{settings.smb_domain}\\{settings.smb_username}" if settings.smb_domain else settings.smb_username
                try:
                    register_session(server, username=username_with_domain, password=settings.smb_password)
                except Exception:
                    # Session might already be registered, ignore error
                    pass
        # Loader registry
        loaders = {
            ".pdf": PDFLoader,
            ".doc": WordDocumentLoader,
            ".docx": WordDocumentLoader,
            ".xlsx": ExcelLoader,
            ".xls": ExcelLoader,
            ".xlsm": ExcelLoader,
            ".csv": ExcelLoader,
        }

        ext = file_path.suffix.lower()
        if ext not in loaders:
            return {"status": "failed", "error": f"Unsupported file type: {ext}"}

        # Load document
        loader_class = loaders[ext]
        loader = loader_class(file_path)
        documents = loader.load()

        if not documents:
            return {"status": "failed", "error": "No content loaded"}

        # Chunk documents
        table_chunker = TableChunker()
        semantic_chunker = SemanticChunker()

        table_chunked = table_chunker.chunk_documents(documents)
        final_chunks = semantic_chunker.chunk_documents(table_chunked)

        # Enrich metadata
        network_accessor = NetworkPathAccessor()
        metadata_enricher = MetadataEnricher(
            base_path=network_accessor.get_document_path()
        )
        enriched_docs = metadata_enricher.enrich_documents(final_chunks)

        # Return documents for batch adding (skip vector store check for performance)
        # The vector store will handle duplicates
        return {
            "status": "success",
            "documents": enriched_docs,
            "chunks_count": len(enriched_docs)
        }

    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return {"status": "failed", "error": str(e)}


class IngestionPipeline:
    """Pipeline for ingesting documents into the vector store."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        skip_existing: bool = True,
        workers: Optional[int] = None,
    ):
        """Initialize ingestion pipeline.

        Args:
            vector_store: VectorStore instance. If None, uses global instance.
            skip_existing: Whether to skip documents that already exist in the store.
            workers: Number of parallel workers. If None, uses setting.
        """
        self.settings = get_settings()
        self.vector_store = vector_store or get_vector_store()
        self.skip_existing = skip_existing
        self.workers = workers or self.settings.ingestion_workers

        # Initialize components
        self.network_accessor = NetworkPathAccessor()
        self.semantic_chunker = SemanticChunker()
        self.table_chunker = TableChunker()
        self.metadata_enricher = MetadataEnricher(
            base_path=self.network_accessor.get_document_path()
        )

        # Loader registry
        self.loaders = {
            ".pdf": PDFLoader,
            ".doc": WordDocumentLoader,
            ".docx": WordDocumentLoader,
            ".xlsx": ExcelLoader,
            ".xls": ExcelLoader,
            ".xlsm": ExcelLoader,
            ".csv": ExcelLoader,
        }

        logger.info(f"IngestionPipeline initialized with {self.workers} workers")

    def ingest_directory(
        self,
        directory: Optional[Path] = None,
        recursive: bool = True,
        file_types: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """Ingest all documents from a directory.

        Args:
            directory: Directory to ingest from. If None, uses configured Q:\\ drive.
            recursive: Whether to search subdirectories.
            file_types: List of file extensions to include. If None, uses all supported types.
            parallel: Whether to use parallel processing. Defaults to True.

        Returns:
            Dictionary with ingestion statistics.
        """
        if directory is None:
            directory = self.network_accessor.get_document_path()
        else:
            directory = Path(directory)

        if file_types is None:
            file_types = list(self.loaders.keys())

        logger.info(f"Starting ingestion from: {directory}")

        # List all documents
        documents = self.network_accessor.list_documents(
            path=directory, extensions=file_types, recursive=recursive
        )

        logger.info(f"Found {len(documents)} documents to process")

        # Choose processing mode
        if parallel and self.workers > 1:
            return self._ingest_parallel(documents)
        else:
            return self._ingest_sequential(documents)

    def _ingest_sequential(self, documents: List[Path]) -> Dict[str, Any]:
        """Ingest documents sequentially (original implementation).

        Args:
            documents: List of file paths to process.

        Returns:
            Dictionary with ingestion statistics.
        """
        stats = {
            "total_files": len(documents),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
        }

        for file_path in tqdm(documents, desc="Ingesting documents"):
            try:
                result = self.ingest_file(file_path)
                if result["status"] == "success":
                    stats["successful"] += 1
                    stats["total_chunks"] += result["chunks_added"]
                elif result["status"] == "skipped":
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["failed"] += 1

        logger.info(
            f"Ingestion complete: {stats['successful']} successful, "
            f"{stats['failed']} failed, {stats['skipped']} skipped, "
            f"{stats['total_chunks']} total chunks"
        )

        return stats

    def _ingest_parallel(self, documents: List[Path]) -> Dict[str, Any]:
        """Ingest documents in parallel using multiple workers.

        Args:
            documents: List of file paths to process.

        Returns:
            Dictionary with ingestion statistics.
        """
        stats = {
            "total_files": len(documents),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
        }

        logger.info(f"Processing {len(documents)} documents with {self.workers} workers")

        # Process documents in batches
        batch_size = self.settings.ingestion_batch_size
        all_docs_to_add = []

        # Use ThreadPoolExecutor instead of ProcessPoolExecutor for better SMB/network support
        # Thread-based parallelism works better with network I/O and shared SMB sessions
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(_process_single_file, file_path, self.skip_existing): file_path
                for file_path in documents
            }

            # Process results as they complete
            with tqdm(total=len(documents), desc="Ingesting documents") as pbar:
                for future in as_completed(future_to_path):
                    file_path = future_to_path[future]
                    try:
                        result = future.result()

                        if result["status"] == "success":
                            stats["successful"] += 1
                            # Collect documents for batch adding
                            if "documents" in result:
                                all_docs_to_add.extend(result["documents"])
                        elif result["status"] == "skipped":
                            stats["skipped"] += 1
                        else:
                            stats["failed"] += 1

                        # Batch add to vector store
                        if len(all_docs_to_add) >= batch_size:
                            chunks_added = len(all_docs_to_add)
                            self.vector_store.add_documents(all_docs_to_add)
                            stats["total_chunks"] += chunks_added
                            all_docs_to_add = []

                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        stats["failed"] += 1

                    pbar.update(1)

        # Add remaining documents
        if all_docs_to_add:
            chunks_added = len(all_docs_to_add)
            self.vector_store.add_documents(all_docs_to_add)
            stats["total_chunks"] += chunks_added

        logger.info(
            f"Parallel ingestion complete: {stats['successful']} successful, "
            f"{stats['failed']} failed, {stats['skipped']} skipped, "
            f"{stats['total_chunks']} total chunks"
        )

        return stats

    def ingest_file(self, file_path: Path) -> Dict[str, Any]:
        """Ingest a single file.

        Args:
            file_path: Path to the file to ingest.

        Returns:
            Dictionary with ingestion result.
        """
        file_path = Path(file_path)

        logger.debug(f"Processing file: {file_path.name}")

        # 1. Load document
        documents = self._load_document(file_path)
        if not documents:
            return {"status": "failed", "error": "No content loaded"}

        # 2. Chunk documents
        chunked_docs = self._chunk_documents(documents)

        # 3. Enrich metadata
        enriched_docs = self.metadata_enricher.enrich_documents(chunked_docs)

        # 4. Filter existing documents if needed
        if self.skip_existing:
            enriched_docs = self._filter_existing(enriched_docs)
            if not enriched_docs:
                logger.debug(f"Skipping {file_path.name} - all chunks already exist")
                return {"status": "skipped", "reason": "already_exists"}

        # 5. Add to vector store
        doc_ids = self.vector_store.add_documents(enriched_docs)

        logger.info(
            f"Successfully ingested {file_path.name}: {len(doc_ids)} chunks added"
        )

        return {"status": "success", "chunks_added": len(doc_ids), "doc_ids": doc_ids}

    def _load_document(self, file_path: Path) -> List[Document]:
        """Load a document using the appropriate loader.

        Args:
            file_path: Path to the document.

        Returns:
            List of Document objects.
        """
        ext = file_path.suffix.lower()

        if ext not in self.loaders:
            logger.warning(f"Unsupported file type: {ext}")
            return []

        loader_class = self.loaders[ext]

        try:
            loader = loader_class(file_path)
            documents = loader.load()
            return documents

        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []

    def _chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Chunk documents using appropriate chunkers.

        Args:
            documents: List of Document objects.

        Returns:
            List of chunked Document objects.
        """
        # First, apply table-aware chunking
        table_chunked = self.table_chunker.chunk_documents(documents)

        # Then, apply semantic chunking for text content
        final_chunks = self.semantic_chunker.chunk_documents(table_chunked)

        return final_chunks

    def _filter_existing(self, documents: List[Document]) -> List[Document]:
        """Filter out documents that already exist in the vector store.

        Args:
            documents: List of Document objects.

        Returns:
            List of documents that don't exist in the store.
        """
        new_documents = []

        for doc in documents:
            doc_id = doc.metadata.get("doc_id")
            if doc_id and not self.vector_store.document_exists(doc_id):
                new_documents.append(doc)

        return new_documents

    def reindex_file(self, file_path: Path) -> Dict[str, Any]:
        """Reindex a file (delete old chunks and re-ingest).

        Args:
            file_path: Path to the file to reindex.

        Returns:
            Dictionary with reindex result.
        """
        file_path = Path(file_path)

        logger.info(f"Reindexing file: {file_path}")

        # Delete existing chunks for this file
        deleted_count = self.vector_store.delete_by_source(str(file_path))

        # Ingest the file
        result = self.ingest_file(file_path)
        result["deleted_chunks"] = deleted_count

        return result

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics about the ingestion pipeline.

        Returns:
            Dictionary with pipeline statistics.
        """
        vector_stats = self.vector_store.get_collection_stats()

        stats = {
            "vector_store": vector_stats,
            "supported_file_types": list(self.loaders.keys()),
            "chunk_size": self.semantic_chunker.chunk_size,
            "chunk_overlap": self.semantic_chunker.chunk_overlap,
        }

        return stats

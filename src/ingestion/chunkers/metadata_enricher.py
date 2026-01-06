"""
Metadata enricher for QmanAssist.
Adds additional context and identifiers to document chunks.
"""

import hashlib
from typing import List
from datetime import datetime
from pathlib import Path
from loguru import logger

from src.ingestion.loaders.base_loader import Document


class MetadataEnricher:
    """Enriches document metadata with additional context."""

    def __init__(self, base_path: Path = None):
        """Initialize metadata enricher.

        Args:
            base_path: Base path for calculating relative paths.
        """
        self.base_path = base_path

    def enrich_documents(self, documents: List[Document]) -> List[Document]:
        """Enrich metadata for a list of documents.

        Args:
            documents: List of Document objects.

        Returns:
            List of documents with enriched metadata.
        """
        enriched_documents = []

        for doc in documents:
            enriched_doc = self.enrich_document(doc)
            enriched_documents.append(enriched_doc)

        logger.info(f"Enriched metadata for {len(documents)} documents")
        return enriched_documents

    def enrich_document(self, document: Document) -> Document:
        """Enrich metadata for a single document.

        Args:
            document: Document to enrich.

        Returns:
            Document with enriched metadata.
        """
        metadata = document.metadata.copy()

        # Add document ID (hash of content)
        metadata["doc_id"] = self._generate_doc_id(document.content, metadata)

        # Add ingestion timestamp
        metadata["ingestion_timestamp"] = datetime.now().isoformat()

        # Add relative path if base path is provided
        if self.base_path and "source" in metadata:
            source_path = Path(metadata["source"])
            try:
                rel_path = source_path.relative_to(self.base_path)
                metadata["relative_path"] = str(rel_path)
            except ValueError:
                pass  # Path not relative to base_path

        # Add category/subdirectory info
        if "source" in metadata:
            metadata["category"] = self._extract_category(metadata["source"])

        # Add content statistics
        metadata["char_count"] = len(document.content)
        metadata["word_count"] = len(document.content.split())

        # Add searchable text preview
        metadata["preview"] = self._generate_preview(document.content)

        return Document(content=document.content, metadata=metadata)

    def _generate_doc_id(self, content: str, metadata: dict) -> str:
        """Generate a unique ID for the document chunk.

        Args:
            content: Document content.
            metadata: Document metadata.

        Returns:
            Unique document ID (hash).
        """
        # Create hash from content + key metadata
        hash_input = content
        if "source" in metadata:
            hash_input += metadata["source"]
        if "page_number" in metadata:
            hash_input += str(metadata["page_number"])
        if "chunk_index" in metadata:
            hash_input += str(metadata["chunk_index"])

        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _extract_category(self, source_path: str) -> str:
        """Extract category/subdirectory from source path.

        Args:
            source_path: Full path to source file.

        Returns:
            Category name (subdirectory or 'root').
        """
        path = Path(source_path)

        if self.base_path:
            try:
                rel_path = path.relative_to(self.base_path)
                parts = rel_path.parts
                if len(parts) > 1:
                    return parts[0]  # First subdirectory
            except ValueError:
                pass

        # Fallback: use parent directory name
        return path.parent.name if path.parent.name else "root"

    def _generate_preview(self, content: str, max_length: int = 200) -> str:
        """Generate a short preview of the content.

        Args:
            content: Full content.
            max_length: Maximum preview length.

        Returns:
            Preview text.
        """
        if len(content) <= max_length:
            return content

        # Truncate and add ellipsis
        preview = content[:max_length].rsplit(" ", 1)[0]
        return preview + "..."

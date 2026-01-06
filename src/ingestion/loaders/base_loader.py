"""
Base document loader interface for QmanAssist.
Defines the abstract interface that all document loaders must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Document:
    """Represents a loaded document with content and metadata."""

    content: str
    metadata: Dict[str, Any]

    def __post_init__(self):
        """Ensure metadata has required fields."""
        if "source" not in self.metadata:
            self.metadata["source"] = "unknown"
        if "doc_type" not in self.metadata:
            self.metadata["doc_type"] = "unknown"


class BaseDocumentLoader(ABC):
    """Abstract base class for document loaders."""

    def __init__(self, file_path: Path):
        """Initialize the loader with a file path.

        Args:
            file_path: Path to the document file.
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

    @abstractmethod
    def load(self) -> List[Document]:
        """Load the document and return Document objects.

        Returns:
            List of Document objects with content and metadata.

        Raises:
            Exception: If loading fails.
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Get list of file extensions supported by this loader.

        Returns:
            List of file extensions (e.g., ['.pdf', '.PDF'])
        """
        pass

    def can_load(self, file_path: Path) -> bool:
        """Check if this loader can handle the given file.

        Args:
            file_path: Path to check.

        Returns:
            True if this loader supports the file type.
        """
        ext = file_path.suffix.lower()
        return ext in [e.lower() for e in self.get_supported_extensions()]

    def _get_base_metadata(self) -> Dict[str, Any]:
        """Get common metadata for all documents.

        Returns:
            Dictionary with base metadata fields.
        """
        stat = self.file_path.stat()
        return {
            "source": str(self.file_path),
            "filename": self.file_path.name,
            "file_type": self.file_path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content.

        Args:
            text: Raw text to clean.

        Returns:
            Cleaned text.
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = " ".join(text.split())

        # Remove null bytes
        text = text.replace("\x00", "")

        return text.strip()

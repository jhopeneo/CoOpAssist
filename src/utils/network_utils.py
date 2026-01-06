"""
Network utilities for accessing the Q:\ drive (\\neonas-01\qmanuals).
Handles both Windows mapped drives and Linux SMB mounts.
"""

import os
import platform
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger

from config.settings import get_settings


class NetworkPathAccessor:
    """Utility class for accessing network share paths."""

    def __init__(self, settings=None):
        """Initialize network path accessor.

        Args:
            settings: Application settings. If None, uses global settings.
        """
        self.settings = settings or get_settings()
        self.platform = platform.system().lower()

    def get_document_path(self) -> Path:
        """Get the document source path for the current platform.

        Returns:
            Path object for the document source.

        Raises:
            FileNotFoundError: If the path doesn't exist or isn't accessible.
        """
        path_str = self.settings.qmanuals_path

        # Convert to Path object
        path = Path(path_str)

        # Check if path exists and is accessible
        if not self.is_path_accessible(path):
            # Try alternative network path
            network_path = self.settings.qmanuals_network_path
            logger.warning(
                f"Primary path {path} not accessible, trying network path {network_path}"
            )

            if self.platform == "windows":
                # Try UNC path on Windows
                path = Path(network_path)
            else:
                # On Linux, suggest mounting
                logger.error(
                    f"Network path not accessible. Please mount {network_path} "
                    f"using: sudo mount -t cifs {network_path} /mnt/q"
                )
                raise FileNotFoundError(
                    f"Document path not accessible: {path_str}. "
                    f"Please ensure Q:\\ drive is mapped or network share is mounted."
                )

        logger.info(f"Using document path: {path}")
        return path

    def is_path_accessible(self, path: Path) -> bool:
        """Check if a path exists and is accessible.

        Args:
            path: Path to check.

        Returns:
            True if path is accessible, False otherwise.
        """
        try:
            return path.exists() and path.is_dir()
        except (OSError, PermissionError) as e:
            logger.debug(f"Path {path} not accessible: {e}")
            return False

    def list_documents(
        self,
        path: Optional[Path] = None,
        extensions: Optional[List[str]] = None,
        recursive: bool = True,
    ) -> List[Path]:
        """List all documents in the specified path.

        Args:
            path: Path to search. If None, uses configured document path.
            extensions: List of file extensions to include (e.g., ['.pdf', '.docx']).
                       If None, includes all supported types.
            recursive: Whether to search subdirectories recursively.

        Returns:
            List of Path objects for matching documents.
        """
        if path is None:
            path = self.get_document_path()

        if extensions is None:
            extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv"]

        # Normalize extensions
        extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions]

        documents = []

        try:
            if recursive:
                # Recursively search all subdirectories
                for ext in extensions:
                    pattern = f"**/*{ext}"
                    documents.extend(path.glob(pattern))
            else:
                # Only search immediate directory
                for ext in extensions:
                    pattern = f"*{ext}"
                    documents.extend(path.glob(pattern))

            logger.info(f"Found {len(documents)} documents in {path}")
            return sorted(documents)

        except (OSError, PermissionError) as e:
            logger.error(f"Error listing documents in {path}: {e}")
            return []

    def get_file_info(self, file_path: Path) -> dict:
        """Get metadata information about a file.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with file metadata.
        """
        try:
            stat = file_path.stat()
            return {
                "path": str(file_path),
                "name": file_path.name,
                "extension": file_path.suffix.lower(),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
            }
        except (OSError, PermissionError) as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {}

    def validate_network_access(self) -> Tuple[bool, str]:
        """Validate that the network share is accessible.

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            path = self.get_document_path()

            if not self.is_path_accessible(path):
                return False, f"Path {path} is not accessible"

            # Try to list files to verify read permissions
            test_list = list(path.iterdir())
            logger.info(f"Network access validated. Found {len(test_list)} items in root.")

            return True, f"Network access successful to {path}"

        except FileNotFoundError as e:
            return False, str(e)
        except PermissionError as e:
            return False, f"Permission denied: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def get_relative_path(self, file_path: Path, base_path: Optional[Path] = None) -> str:
        """Get relative path from base document path.

        Args:
            file_path: Full path to file.
            base_path: Base path to calculate relative path from.
                      If None, uses configured document path.

        Returns:
            Relative path as string.
        """
        if base_path is None:
            base_path = self.get_document_path()

        try:
            return str(file_path.relative_to(base_path))
        except ValueError:
            # If paths don't share a common base
            return str(file_path)


# Convenience functions
def get_document_path() -> Path:
    """Get the configured document path."""
    accessor = NetworkPathAccessor()
    return accessor.get_document_path()


def list_documents(
    path: Optional[Path] = None,
    extensions: Optional[List[str]] = None,
    recursive: bool = True,
) -> List[Path]:
    """List all documents in the specified path."""
    accessor = NetworkPathAccessor()
    return accessor.list_documents(path, extensions, recursive)


def validate_network_access() -> Tuple[bool, str]:
    """Validate network share access."""
    accessor = NetworkPathAccessor()
    return accessor.validate_network_access()

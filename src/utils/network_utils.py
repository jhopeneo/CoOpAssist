"""
Network utilities for accessing the Q:\\ drive (\\\\neonas-01\\qmanuals).
Handles both Windows mapped drives and Linux SMB mounts/connections.
"""

import os
import platform
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger
import smbclient
from smbclient import register_session

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
        self._smb_initialized = False

        # Initialize SMB session if using network path
        if self.settings.is_network_path():
            self._init_smb_session()

    def _init_smb_session(self):
        """Initialize SMB session with credentials."""
        try:
            # Extract server from path (//server/share)
            path = self.settings.qmanuals_network_path
            parts = path.replace("\\\\", "//").strip("/").split("/")
            server = parts[0] if parts else "neonas-01"

            # Register SMB session with credentials
            if self.settings.smb_username and self.settings.smb_password:
                username_with_domain = f"{self.settings.smb_domain}\\{self.settings.smb_username}" if self.settings.smb_domain else self.settings.smb_username
                register_session(server, username=username_with_domain, password=self.settings.smb_password)
                self._smb_initialized = True
                logger.info(f"SMB session initialized for {server}")
            else:
                logger.warning("SMB credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize SMB session: {e}")

    def get_document_path(self) -> str:
        """Get the document source path for the current platform.

        Returns:
            Path string for the document source (may be SMB path).

        Raises:
            FileNotFoundError: If the path doesn't exist or isn't accessible.
        """
        path_str = self.settings.qmanuals_path

        # For network paths, validate using SMB and return the string path
        if path_str.startswith("//") or path_str.startswith("\\\\"):
            if self._smb_initialized:
                # Return the network path as-is for SMB operations
                logger.info(f"Using SMB document path: {path_str}")
                return path_str
            else:
                raise FileNotFoundError(
                    f"SMB session not initialized. Cannot access {path_str}"
                )

        # For local paths, check accessibility
        path = Path(path_str)
        if not self.is_path_accessible(path):
            raise FileNotFoundError(
                f"Document path not accessible: {path_str}"
            )

        logger.info(f"Using local document path: {path}")
        return str(path)

    def is_path_accessible(self, path: Path) -> bool:
        """Check if a path exists and is accessible.

        Args:
            path: Path to check.

        Returns:
            True if path is accessible, False otherwise.
        """
        path_str = str(path)

        # Check if it's a network path
        if path_str.startswith("//") or path_str.startswith("\\\\"):
            try:
                # Use smbclient to check if path is accessible
                smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
                items = list(smbclient.listdir(smb_path))
                return True
            except Exception as e:
                logger.debug(f"SMB path {path} not accessible: {e}")
                return False
        else:
            # Local path check
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
        path_str = str(path)

        try:
            # Check if it's a network path
            if path_str.startswith("//") or path_str.startswith("\\\\"):
                # Use smbclient for SMB paths
                smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
                documents = self._list_smb_documents(smb_path, extensions, recursive)
            else:
                # Use standard path.glob for local paths
                if recursive:
                    for ext in extensions:
                        pattern = f"**/*{ext}"
                        documents.extend(path.glob(pattern))
                else:
                    for ext in extensions:
                        pattern = f"*{ext}"
                        documents.extend(path.glob(pattern))
                documents = sorted(documents)

            logger.info(f"Found {len(documents)} documents in {path}")
            return documents

        except (OSError, PermissionError) as e:
            logger.error(f"Error listing documents in {path}: {e}")
            return []

    def _list_smb_documents(self, smb_path: str, extensions: List[str], recursive: bool) -> List[Path]:
        """List documents from SMB share.

        Args:
            smb_path: SMB path in UNC format (\\\\server\\share\\path)
            extensions: List of file extensions to include
            recursive: Whether to search recursively

        Returns:
            List of Path objects for matching documents
        """
        documents = []

        try:
            if recursive:
                # Recursively walk the directory tree
                for root, dirs, files in smbclient.walk(smb_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in extensions):
                            full_path = os.path.join(root, file).replace("\\", "/")
                            documents.append(Path(full_path))
            else:
                # Only list files in the immediate directory
                for item in smbclient.scandir(smb_path):
                    if item.is_file():
                        if any(item.name.lower().endswith(ext) for ext in extensions):
                            full_path = os.path.join(smb_path, item.name).replace("\\", "/")
                            documents.append(Path(full_path))

            return sorted(documents)

        except Exception as e:
            logger.error(f"Error listing SMB documents in {smb_path}: {e}")
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
            path_str = self.get_document_path()

            # Try to list files to verify read permissions
            if path_str.startswith("//") or path_str.startswith("\\\\"):
                # SMB path
                smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
                test_list = list(smbclient.listdir(smb_path))
            else:
                # Local path
                test_list = list(Path(path_str).iterdir())

            logger.info(f"Network access validated. Found {len(test_list)} items in root.")
            return True, f"Network access successful to {path_str}"

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

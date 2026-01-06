"""
PDF document loader for QmanAssist.
Uses PyPDF2 for basic text extraction and pdfplumber for tables.
Supports both local files and SMB network shares.
"""

from pathlib import Path
from typing import List
from loguru import logger
import PyPDF2
import pdfplumber
import smbclient
import tempfile
import io

from .base_loader import BaseDocumentLoader, Document


class PDFLoader(BaseDocumentLoader):
    """Loader for PDF documents with table support."""

    def __init__(self, file_path: Path, extract_tables: bool = True):
        """Initialize PDF loader.

        Args:
            file_path: Path to PDF file.
            extract_tables: Whether to extract tables using pdfplumber.
        """
        super().__init__(file_path)
        self.extract_tables = extract_tables

    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".pdf", ".PDF"]

    def load(self) -> List[Document]:
        """Load PDF document and extract text and tables.

        Returns:
            List of Document objects (one per page).
        """
        documents = []

        try:
            # Use pdfplumber for better extraction if requested
            if self.extract_tables:
                documents = self._load_with_pdfplumber()
            else:
                documents = self._load_with_pypdf2()

            logger.info(f"Loaded {len(documents)} pages from {self.file_path.name}")
            return documents

        except Exception as e:
            logger.error(f"Error loading PDF {self.file_path}: {e}")
            # Try fallback method
            if self.extract_tables:
                logger.info("Falling back to PyPDF2")
                return self._load_with_pypdf2()
            raise

    def _load_with_pdfplumber(self) -> List[Document]:
        """Load PDF using pdfplumber (better for tables).

        Returns:
            List of Document objects.
        """
        documents = []
        base_metadata = self._get_base_metadata()

        # Check if it's an SMB path
        path_str = str(self.file_path)
        if path_str.startswith("//") or path_str.startswith("\\\\"):
            # Read from SMB into memory
            smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
            with smbclient.open_file(smb_path, mode="rb") as smb_file:
                pdf_data = io.BytesIO(smb_file.read())
                with pdfplumber.open(pdf_data) as pdf:
                    documents = self._extract_with_pdfplumber(pdf, base_metadata)
        else:
            # Local file
            with pdfplumber.open(self.file_path) as pdf:
                documents = self._extract_with_pdfplumber(pdf, base_metadata)

        return documents

    def _extract_with_pdfplumber(self, pdf, base_metadata: dict) -> List[Document]:
        """Extract content from pdfplumber PDF object.

        Args:
            pdf: pdfplumber PDF object
            base_metadata: Base metadata dictionary

        Returns:
            List of Document objects
        """
        documents = []
        base_metadata["page_count"] = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            # Extract text
            text = page.extract_text() or ""

            # Extract tables
            tables = page.extract_tables()
            table_text = self._format_tables(tables)

            # Combine text and tables
            content = text
            if table_text:
                content += "\n\n" + table_text

            content = self._clean_text(content)

            if content:  # Only create document if there's content
                metadata = base_metadata.copy()
                metadata.update({
                    "page_number": page_num,
                    "doc_type": "pdf",
                    "has_tables": bool(tables),
                    "table_count": len(tables) if tables else 0,
                })

                documents.append(Document(content=content, metadata=metadata))

        return documents

    def _load_with_pypdf2(self) -> List[Document]:
        """Load PDF using PyPDF2 (basic text extraction).

        Returns:
            List of Document objects.
        """
        documents = []
        base_metadata = self._get_base_metadata()

        # Check if it's an SMB path
        path_str = str(self.file_path)
        if path_str.startswith("//") or path_str.startswith("\\\\"):
            # Read from SMB into memory
            smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
            with smbclient.open_file(smb_path, mode="rb") as smb_file:
                pdf_data = io.BytesIO(smb_file.read())
                reader = PyPDF2.PdfReader(pdf_data)
                documents = self._extract_with_pypdf2(reader, base_metadata)
        else:
            # Local file
            with open(self.file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                documents = self._extract_with_pypdf2(reader, base_metadata)

        return documents

    def _extract_with_pypdf2(self, reader, base_metadata: dict) -> List[Document]:
        """Extract content from PyPDF2 reader object.

        Args:
            reader: PyPDF2 PdfReader object
            base_metadata: Base metadata dictionary

        Returns:
            List of Document objects
        """
        documents = []
        base_metadata["page_count"] = len(reader.pages)

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text()
                content = self._clean_text(text)

                if content:
                    metadata = base_metadata.copy()
                    metadata.update({
                        "page_number": page_num,
                        "doc_type": "pdf",
                        "has_tables": False,
                    })

                    documents.append(Document(content=content, metadata=metadata))

            except Exception as e:
                logger.warning(f"Error extracting page {page_num}: {e}")
                continue

        return documents

    def _format_tables(self, tables: List[List[List[str]]]) -> str:
        """Format extracted tables as text.

        Args:
            tables: List of tables (each table is a list of rows).

        Returns:
            Formatted table text.
        """
        if not tables:
            return ""

        formatted_tables = []

        for table_idx, table in enumerate(tables, start=1):
            if not table:
                continue

            # Format table
            table_lines = [f"Table {table_idx}:"]

            for row in table:
                if row:
                    # Join cells with pipe separator
                    row_text = " | ".join(str(cell) if cell else "" for cell in row)
                    table_lines.append(row_text)

            formatted_tables.append("\n".join(table_lines))

        return "\n\n".join(formatted_tables)

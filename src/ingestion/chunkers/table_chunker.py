"""
Table-aware chunker for QmanAssist.
Special handling for documents containing tables.
"""

from typing import List
from loguru import logger

from src.ingestion.loaders.base_loader import Document


class TableChunker:
    """Chunks documents with special handling for tables."""

    def __init__(self, preserve_tables: bool = True):
        """Initialize table chunker.

        Args:
            preserve_tables: Whether to keep tables intact in single chunks.
        """
        self.preserve_tables = preserve_tables

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Chunk documents with table-aware splitting.

        Args:
            documents: List of Document objects.

        Returns:
            List of chunked Document objects.
        """
        if not self.preserve_tables:
            # If not preserving tables, return as-is
            return documents

        chunked_documents = []

        for doc in documents:
            # Check if document has tables
            has_tables = doc.metadata.get("has_tables", False)

            if has_tables:
                # For documents with tables, keep them intact
                chunks = self._chunk_with_tables(doc)
            else:
                # Regular documents can be chunked normally
                chunks = [doc]

            chunked_documents.extend(chunks)

        logger.info(
            f"Table-aware chunking: {len(documents)} documents -> "
            f"{len(chunked_documents)} chunks"
        )

        return chunked_documents

    def _chunk_with_tables(self, document: Document) -> List[Document]:
        """Chunk document while preserving table structures.

        Args:
            document: Document containing tables.

        Returns:
            List of chunked documents.
        """
        # For now, keep tables in their own chunks
        # More sophisticated splitting could separate text and tables
        return [document]

    def split_text_and_tables(self, document: Document) -> tuple[List[Document], List[Document]]:
        """Separate text content from table content.

        Args:
            document: Document to split.

        Returns:
            Tuple of (text_documents, table_documents)
        """
        content = document.content
        text_parts = []
        table_parts = []

        # Simple heuristic: look for "Table" markers
        lines = content.split("\n")
        current_part = []
        in_table = False

        for line in lines:
            if line.strip().startswith("Table"):
                # Start of table
                if current_part and not in_table:
                    # Save previous text
                    text_parts.append("\n".join(current_part))
                    current_part = []

                in_table = True
                current_part.append(line)

            elif in_table and line.strip() == "":
                # End of table (empty line)
                if current_part:
                    table_parts.append("\n".join(current_part))
                    current_part = []
                in_table = False

            else:
                current_part.append(line)

        # Add remaining content
        if current_part:
            if in_table:
                table_parts.append("\n".join(current_part))
            else:
                text_parts.append("\n".join(current_part))

        # Create separate documents
        text_docs = []
        for i, text in enumerate(text_parts):
            if text.strip():
                metadata = document.metadata.copy()
                metadata.update({
                    "content_type": "text",
                    "part_index": i,
                })
                text_docs.append(Document(content=text, metadata=metadata))

        table_docs = []
        for i, table in enumerate(table_parts):
            if table.strip():
                metadata = document.metadata.copy()
                metadata.update({
                    "content_type": "table",
                    "table_index": i,
                })
                table_docs.append(Document(content=table, metadata=metadata))

        return text_docs, table_docs

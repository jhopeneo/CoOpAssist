"""
Semantic text chunker for QmanAssist.
Uses LangChain's RecursiveCharacterTextSplitter for context-aware chunking.
"""

from typing import List, Dict, Any
from loguru import logger
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config.settings import get_settings
from src.ingestion.loaders.base_loader import Document


class SemanticChunker:
    """Chunks documents using semantic boundaries."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None,
    ):
        """Initialize semantic chunker.

        Args:
            chunk_size: Size of chunks in characters. If None, uses setting from config.
            chunk_overlap: Overlap between chunks. If None, uses setting from config.
            separators: List of separators to split on. If None, uses default.
        """
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        # Default separators prioritize semantic boundaries
        self.separators = separators or [
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            ". ",  # Sentences
            " ",  # Words
            "",  # Characters
        ]

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
        )

        logger.info(
            f"SemanticChunker initialized: chunk_size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}"
        )

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Chunk a list of documents into smaller pieces.

        Args:
            documents: List of Document objects to chunk.

        Returns:
            List of chunked Document objects.
        """
        chunked_documents = []

        for doc in documents:
            chunks = self.chunk_document(doc)
            chunked_documents.extend(chunks)

        logger.info(
            f"Chunked {len(documents)} documents into {len(chunked_documents)} chunks"
        )

        return chunked_documents

    def chunk_document(self, document: Document) -> List[Document]:
        """Chunk a single document.

        Args:
            document: Document to chunk.

        Returns:
            List of chunked Document objects.
        """
        # Skip if document is already small enough
        if len(document.content) <= self.chunk_size:
            return [document]

        # Split the text
        texts = self.text_splitter.split_text(document.content)

        # Create new documents for each chunk
        chunked_docs = []
        for i, text in enumerate(texts):
            # Copy metadata and add chunk info
            chunk_metadata = document.metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(texts),
                "chunk_size": len(text),
            })

            chunked_docs.append(Document(content=text, metadata=chunk_metadata))

        return chunked_docs

    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Chunk raw text into documents.

        Args:
            text: Text to chunk.
            metadata: Optional metadata to attach to chunks.

        Returns:
            List of Document objects.
        """
        metadata = metadata or {}
        texts = self.text_splitter.split_text(text)

        documents = []
        for i, chunk_text in enumerate(texts):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(texts),
                "chunk_size": len(chunk_text),
            })

            documents.append(Document(content=chunk_text, metadata=chunk_metadata))

        return documents

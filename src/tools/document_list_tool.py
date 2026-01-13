"""
Document listing tool for browsing and exploring documents.
Handles queries like "show me", "browse", "what documents about X".
"""

from typing import Dict, Any
from loguru import logger
from pathlib import Path

from src.core.vector_store import get_vector_store


class DocumentListTool:
    """Tool for listing and browsing documents."""

    def __init__(self):
        """Initialize document listing tool."""
        self.vector_store = get_vector_store()
        logger.info("DocumentListTool initialized")

    @property
    def name(self) -> str:
        """Tool name."""
        return "document_list"

    @property
    def description(self) -> str:
        """Tool description for the agent."""
        return """List and browse documents in the database.

Use this tool when the user wants to:
- "Show me documents about X"
- "Browse X documents"
- "What documents do we have for X?"
- "List documents in category X"

Input should be a dictionary with:
- search_term: term to search for in filenames and paths
- category: filter by document category (optional)
- doc_type: filter by document type (pdf, docx, xlsx)
- limit: max number of documents to return (default 15)

Returns a formatted list of matching documents with metadata."""

    def run(self, query_params: Dict[str, Any]) -> str:
        """List documents matching criteria.

        Args:
            query_params: Dictionary with search_term, category, doc_type, limit.

        Returns:
            Formatted list of documents.
        """
        search_term = query_params.get("search_term", "").lower()
        category = query_params.get("category", "").lower()
        doc_type = query_params.get("doc_type", "").lower()
        limit = query_params.get("limit", 15)

        logger.info(
            f"DocumentListTool: search={search_term}, category={category}, "
            f"type={doc_type}, limit={limit}"
        )

        try:
            # Get all metadata
            all_docs = self.vector_store.collection.get(include=["metadatas"])

            if not all_docs["metadatas"]:
                return "No documents found in the database."

            # Filter and get unique documents
            matching_docs = []
            seen_sources = set()

            for metadata in all_docs["metadatas"]:
                source = metadata.get("source", "")

                # Skip if already seen
                if source in seen_sources:
                    continue

                # Apply filters
                if doc_type and metadata.get("doc_type", "").lower() != doc_type:
                    continue

                if category and metadata.get("category", "").lower() != category:
                    continue

                # Search in filename and path
                if search_term:
                    searchable = " ".join([
                        metadata.get("filename", ""),
                        metadata.get("relative_path", ""),
                    ]).lower()

                    if search_term not in searchable:
                        continue

                # Add to results
                matching_docs.append(metadata)
                seen_sources.add(source)

                if len(matching_docs) >= limit:
                    break

            if not matching_docs:
                criteria = []
                if search_term:
                    criteria.append(f"matching '{search_term}'")
                if category:
                    criteria.append(f"in category '{category}'")
                if doc_type:
                    criteria.append(f"of type '{doc_type}'")

                criteria_str = " ".join(criteria) if criteria else ""
                return f"No documents found {criteria_str}."

            # Build response
            result = f"**Documents Found:** ({len(matching_docs)} matching)\n\n"

            for i, metadata in enumerate(matching_docs, 1):
                filename = metadata.get("filename", "Unknown")
                dtype = metadata.get("doc_type", "unknown")
                cat = metadata.get("category", "N/A")
                rel_path = metadata.get("relative_path", "N/A")
                page_count = metadata.get("page_count", "N/A")

                result += f"{i}. **{filename}**\n"
                result += f"   - Type: {dtype}\n"
                result += f"   - Category: {cat}\n"

                if page_count != "N/A":
                    result += f"   - Pages: {page_count}\n"

                # Shorten path if too long
                if len(rel_path) > 80:
                    rel_path = "..." + rel_path[-77:]
                result += f"   - Location: {rel_path}\n\n"

            return result

        except Exception as e:
            logger.error(f"Error in DocumentListTool: {e}")
            return f"Error listing documents: {str(e)}"

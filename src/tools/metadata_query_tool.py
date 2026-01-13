"""
Metadata query tool for counting and filtering documents.
Handles queries like "how many", "list all", "show recent", etc.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime
from collections import Counter

from src.core.vector_store import get_vector_store


class MetadataQueryTool:
    """Tool for querying document metadata (count, filter, aggregate)."""

    def __init__(self):
        """Initialize metadata query tool."""
        self.vector_store = get_vector_store()
        logger.info("MetadataQueryTool initialized")

    @property
    def name(self) -> str:
        """Tool name."""
        return "metadata_query"

    @property
    def description(self) -> str:
        """Tool description for the agent."""
        return """Query document metadata for counting, filtering, and listing documents.

Use this tool when the user asks:
- "How many X do we have?"
- "List all X documents"
- "Show me documents about X"
- "What are the categories?"
- "Show recent X documents"

Input should be a dictionary with:
- action: "count" | "list" | "categories" | "recent"
- filter_term: search term to filter by (optional, searches in filename, path, category)
- limit: max results for "list" or "recent" (default 20)
- doc_type: filter by document type (pdf, docx, xlsx, etc.)

Returns statistics and document lists based on metadata only."""

    def run(self, query_params: Dict[str, Any]) -> str:
        """Execute metadata query.

        Args:
            query_params: Dictionary with action, filter_term, limit, etc.

        Returns:
            Formatted string with results.
        """
        action = query_params.get("action", "count")
        filter_term = query_params.get("filter_term", "").lower()
        limit = query_params.get("limit", 20)
        doc_type = query_params.get("doc_type", "").lower()

        logger.info(f"MetadataQueryTool: action={action}, filter={filter_term}")

        try:
            if action == "count":
                return self._count_documents(filter_term, doc_type)
            elif action == "list":
                return self._list_documents(filter_term, doc_type, limit)
            elif action == "categories":
                return self._list_categories()
            elif action == "recent":
                return self._list_recent_documents(filter_term, doc_type, limit)
            else:
                return f"Unknown action: {action}. Valid actions: count, list, categories, recent"

        except Exception as e:
            logger.error(f"Error in MetadataQueryTool: {e}")
            return f"Error querying metadata: {str(e)}"

    def _count_documents(self, filter_term: str, doc_type: str) -> str:
        """Count documents matching filter.

        Args:
            filter_term: Term to filter by.
            doc_type: Document type to filter by.

        Returns:
            Formatted count string.
        """
        # Get all metadata
        all_docs = self.vector_store.collection.get(include=["metadatas"])

        if not all_docs["metadatas"]:
            return "No documents found in the database."

        # Filter documents
        matching_docs = self._filter_metadata(
            all_docs["metadatas"], filter_term, doc_type
        )

        # Group by unique source files
        unique_files = set()
        doc_types = Counter()
        categories = Counter()

        for metadata in matching_docs:
            source = metadata.get("source", "")
            if source:
                unique_files.add(source)

            doc_type_val = metadata.get("doc_type", "unknown")
            doc_types[doc_type_val] += 1

            category = metadata.get("category", "uncategorized")
            categories[category] += 1

        # Build response
        filter_desc = f" matching '{filter_term}'" if filter_term else ""
        type_desc = f" ({doc_type} only)" if doc_type else ""

        result = f"**Document Count{filter_desc}{type_desc}:**\n\n"
        result += f"- **Total unique documents:** {len(unique_files)}\n"
        result += f"- **Total chunks:** {len(matching_docs)}\n\n"

        if doc_types:
            result += "**By Type:**\n"
            for dtype, count in doc_types.most_common():
                # Count unique files of this type
                type_files = set()
                for m in matching_docs:
                    if m.get("doc_type") == dtype:
                        type_files.add(m.get("source", ""))
                result += f"- {dtype}: {len(type_files)} documents ({count} chunks)\n"

        if categories:
            result += "\n**By Category:**\n"
            for cat, count in categories.most_common(5):
                # Count unique files in this category
                cat_files = set()
                for m in matching_docs:
                    if m.get("category") == cat:
                        cat_files.add(m.get("source", ""))
                result += f"- {cat}: {len(cat_files)} documents\n"

        return result

    def _list_documents(
        self, filter_term: str, doc_type: str, limit: int
    ) -> str:
        """List documents matching filter.

        Args:
            filter_term: Term to filter by.
            doc_type: Document type filter.
            limit: Max results.

        Returns:
            Formatted list string.
        """
        # Get all metadata
        all_docs = self.vector_store.collection.get(include=["metadatas"])

        if not all_docs["metadatas"]:
            return "No documents found in the database."

        # Filter and get unique documents
        matching_docs = self._filter_metadata(
            all_docs["metadatas"], filter_term, doc_type
        )

        # Group by source file
        docs_by_source = {}
        for metadata in matching_docs:
            source = metadata.get("source", "")
            if source not in docs_by_source:
                docs_by_source[source] = metadata

        # Convert to list and limit
        doc_list = list(docs_by_source.values())[:limit]

        if not doc_list:
            filter_desc = f" matching '{filter_term}'" if filter_term else ""
            return f"No documents found{filter_desc}."

        # Build response
        filter_desc = f" matching '{filter_term}'" if filter_term else ""
        result = f"**Documents{filter_desc}:** (showing {len(doc_list)} of {len(docs_by_source)})\n\n"

        for i, metadata in enumerate(doc_list, 1):
            filename = metadata.get("filename", "Unknown")
            rel_path = metadata.get("relative_path", "N/A")
            dtype = metadata.get("doc_type", "unknown")
            category = metadata.get("category", "N/A")

            result += f"{i}. **{filename}**\n"
            result += f"   - Type: {dtype}\n"
            result += f"   - Category: {category}\n"
            result += f"   - Path: {rel_path}\n\n"

        return result

    def _list_categories(self) -> str:
        """List all document categories.

        Returns:
            Formatted category list.
        """
        # Get all metadata
        all_docs = self.vector_store.collection.get(include=["metadatas"])

        if not all_docs["metadatas"]:
            return "No documents found in the database."

        # Count by category
        categories = Counter()
        for metadata in all_docs["metadatas"]:
            category = metadata.get("category", "uncategorized")
            categories[category] += 1

        # Build response
        result = "**Document Categories:**\n\n"
        for category, count in categories.most_common():
            result += f"- **{category}**: {count} chunks\n"

        return result

    def _list_recent_documents(
        self, filter_term: str, doc_type: str, limit: int
    ) -> str:
        """List recently modified/ingested documents.

        Args:
            filter_term: Term to filter by.
            doc_type: Document type filter.
            limit: Max results.

        Returns:
            Formatted list string.
        """
        # Get all metadata
        all_docs = self.vector_store.collection.get(include=["metadatas"])

        if not all_docs["metadatas"]:
            return "No documents found in the database."

        # Filter and get unique documents
        matching_docs = self._filter_metadata(
            all_docs["metadatas"], filter_term, doc_type
        )

        # Group by source and get most recent ingestion timestamp
        docs_by_source = {}
        for metadata in matching_docs:
            source = metadata.get("source", "")
            ingestion_ts = metadata.get("ingestion_timestamp", "")

            if source not in docs_by_source or ingestion_ts > docs_by_source[source].get("ingestion_timestamp", ""):
                docs_by_source[source] = metadata

        # Sort by ingestion timestamp
        doc_list = sorted(
            docs_by_source.values(),
            key=lambda x: x.get("ingestion_timestamp", ""),
            reverse=True
        )[:limit]

        if not doc_list:
            return "No recent documents found."

        # Build response
        result = f"**Recently Ingested Documents:** (showing {len(doc_list)})\n\n"

        for i, metadata in enumerate(doc_list, 1):
            filename = metadata.get("filename", "Unknown")
            dtype = metadata.get("doc_type", "unknown")
            category = metadata.get("category", "N/A")
            ingestion_ts = metadata.get("ingestion_timestamp", "N/A")

            # Format timestamp
            try:
                if ingestion_ts != "N/A":
                    dt = datetime.fromisoformat(ingestion_ts)
                    ingestion_str = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    ingestion_str = "N/A"
            except:
                ingestion_str = ingestion_ts

            result += f"{i}. **{filename}** ({dtype})\n"
            result += f"   - Category: {category}\n"
            result += f"   - Ingested: {ingestion_str}\n\n"

        return result

    def _filter_metadata(
        self, metadatas: List[Dict[str, Any]], filter_term: str, doc_type: str
    ) -> List[Dict[str, Any]]:
        """Filter metadata by term and type.

        Args:
            metadatas: List of metadata dictionaries.
            filter_term: Term to search for.
            doc_type: Document type to filter by.

        Returns:
            Filtered list of metadata.
        """
        filtered = []

        for metadata in metadatas:
            # Apply doc_type filter
            if doc_type and metadata.get("doc_type", "").lower() != doc_type:
                continue

            # Apply filter_term (search in multiple fields)
            if filter_term:
                searchable = " ".join([
                    metadata.get("filename", ""),
                    metadata.get("relative_path", ""),
                    metadata.get("category", ""),
                ]).lower()

                if filter_term not in searchable:
                    continue

            filtered.append(metadata)

        return filtered

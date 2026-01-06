"""
Document explorer component for QmanAssist.
Browse and manage indexed documents.
"""

import streamlit as st
from pathlib import Path
from loguru import logger

from src.core.vector_store import get_vector_store
from src.ingestion.pipeline import IngestionPipeline
from src.utils.network_utils import NetworkPathAccessor, validate_network_access


def render_document_explorer():
    """Render the document explorer interface."""
    st.header("📁 Document Explorer")

    # Get vector store stats
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_collection_stats()
    except Exception as e:
        st.error(f"Error loading vector store: {e}")
        logger.error(f"Error in document explorer: {e}")
        return

    # Display statistics
    st.subheader("📊 Database Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Documents", stats["document_count"])

    with col2:
        st.metric("Collection", stats["collection_name"])

    with col3:
        num_types = len(stats.get("doc_types", {}))
        st.metric("Document Types", num_types)

    # Document types breakdown
    if stats.get("doc_types"):
        st.markdown("---")
        st.subheader("📄 Document Types")

        # Create columns for document types
        doc_types = stats["doc_types"]
        cols = st.columns(len(doc_types))

        for i, (doc_type, count) in enumerate(doc_types.items()):
            with cols[i]:
                st.metric(doc_type.upper(), count)

    # Document ingestion section
    st.markdown("---")
    st.subheader("📥 Document Ingestion")

    # Check network access
    success, message = validate_network_access()

    if success:
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")
        st.warning("Please ensure Q:\\ drive is accessible before ingesting documents.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Ingest Documents", use_container_width=True, type="primary"):
            run_ingestion()

    with col2:
        if st.button("🗑️ Clear Database", use_container_width=True):
            confirm_clear_database()

    # Browse source files
    st.markdown("---")
    st.subheader("📂 Browse Source Files")

    if success:
        try:
            accessor = NetworkPathAccessor()
            doc_path = accessor.get_document_path()

            # List available documents
            documents = accessor.list_documents(
                path=doc_path, extensions=[".pdf", ".docx", ".xlsx", ".csv"]
            )

            if documents:
                st.info(f"Found {len(documents)} documents in Q:\\ drive")

                # Group by subdirectory
                by_dir = {}
                for doc in documents:
                    rel_path = doc.relative_to(doc_path)
                    dir_name = rel_path.parts[0] if len(rel_path.parts) > 1 else "Root"

                    if dir_name not in by_dir:
                        by_dir[dir_name] = []
                    by_dir[dir_name].append(doc)

                # Display by directory
                for dir_name, docs in sorted(by_dir.items()):
                    with st.expander(f"📁 {dir_name} ({len(docs)} files)"):
                        for doc in sorted(docs):
                            file_info = accessor.get_file_info(doc)

                            col1, col2, col3 = st.columns([3, 1, 1])

                            with col1:
                                st.text(f"📄 {doc.name}")

                            with col2:
                                st.text(f"{file_info.get('size_mb', 0)} MB")

                            with col3:
                                doc_type = file_info.get("extension", "").upper()
                                st.text(doc_type)

            else:
                st.warning("No documents found in Q:\\ drive")

        except Exception as e:
            st.error(f"Error browsing documents: {e}")
            logger.error(f"Error browsing source files: {e}")

    # Advanced options
    st.markdown("---")

    with st.expander("🔧 Advanced Options"):
        st.markdown("**Re-index Specific File**")
        st.text_input("File path", key="reindex_path")

        if st.button("Re-index File"):
            reindex_specific_file(st.session_state.reindex_path)

        st.markdown("---")

        st.markdown("**Database Management**")
        st.caption("Storage location: " + stats["persist_directory"])

        if st.button("🔍 Inspect Collection"):
            inspect_collection()


def run_ingestion():
    """Run document ingestion process."""
    with st.spinner("Ingesting documents from Q:\\ drive..."):
        try:
            pipeline = IngestionPipeline(skip_existing=True)

            # Create progress placeholder
            progress_text = st.empty()
            progress_bar = st.progress(0)

            progress_text.text("Starting ingestion...")

            # Run ingestion (simplified - no real-time progress yet)
            stats = pipeline.ingest_directory()

            # Update progress
            progress_bar.progress(100)
            progress_text.text("Ingestion complete!")

            # Display results
            st.success(
                f"✅ Ingestion complete!\n\n"
                f"- Total files: {stats['total_files']}\n"
                f"- Successfully processed: {stats['successful']}\n"
                f"- Failed: {stats['failed']}\n"
                f"- Skipped (existing): {stats['skipped']}\n"
                f"- Total chunks added: {stats['total_chunks']}"
            )

            logger.info(f"Ingestion completed via UI: {stats}")

            # Refresh page
            st.rerun()

        except Exception as e:
            st.error(f"Error during ingestion: {e}")
            logger.error(f"Ingestion error: {e}")
            logger.exception("Full traceback:")


def confirm_clear_database():
    """Confirm before clearing database."""
    st.warning("⚠️ This will delete all indexed documents!")

    confirm = st.text_input(
        "Type 'DELETE' to confirm:", key="confirm_delete"
    )

    if st.button("Confirm Delete", type="primary"):
        if confirm == "DELETE":
            clear_database()
        else:
            st.error("Confirmation text doesn't match. Database not cleared.")


def clear_database():
    """Clear the entire vector database."""
    try:
        vector_store = get_vector_store()
        vector_store.delete_collection()

        st.success("✅ Database cleared successfully!")
        logger.info("Database cleared via UI")

        # Reinitialize
        from src.core.vector_store import reset_vector_store

        reset_vector_store()
        st.rerun()

    except Exception as e:
        st.error(f"Error clearing database: {e}")
        logger.error(f"Error clearing database: {e}")


def reindex_specific_file(file_path: str):
    """Re-index a specific file."""
    if not file_path:
        st.warning("Please enter a file path")
        return

    try:
        pipeline = IngestionPipeline()
        result = pipeline.reindex_file(Path(file_path))

        if result["status"] == "success":
            st.success(
                f"✅ File re-indexed successfully!\n\n"
                f"- Deleted chunks: {result.get('deleted_chunks', 0)}\n"
                f"- Added chunks: {result.get('chunks_added', 0)}"
            )
        else:
            st.error(f"Failed to re-index file: {result.get('error', 'Unknown error')}")

    except Exception as e:
        st.error(f"Error re-indexing file: {e}")
        logger.error(f"Re-index error: {e}")


def inspect_collection():
    """Inspect collection details."""
    try:
        vector_store = get_vector_store()

        # Get sample documents
        sample = vector_store.collection.get(limit=10)

        st.subheader("Sample Documents")

        if sample["documents"]:
            for i, (doc_id, content, metadata) in enumerate(
                zip(sample["ids"], sample["documents"], sample["metadatas"]), start=1
            ):
                with st.expander(f"Document {i}: {doc_id}"):
                    st.text(f"Content preview: {content[:200]}...")
                    st.json(metadata)
        else:
            st.info("No documents in collection")

    except Exception as e:
        st.error(f"Error inspecting collection: {e}")
        logger.error(f"Inspection error: {e}")

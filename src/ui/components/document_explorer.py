"""
Document explorer component for QmanAssist.
Browse and manage indexed documents.
"""

import streamlit as st
from pathlib import Path
from loguru import logger
import threading
import time
from datetime import datetime
import subprocess
import json
import os

from src.core.vector_store import get_vector_store
from src.ingestion.pipeline import IngestionPipeline
from src.utils.network_utils import NetworkPathAccessor, validate_network_access


# Status file for tracking subprocess ingestion
_status_file = Path("/tmp/coopassist_ingestion_status.json")

# Global variable to track background ingestion
_ingestion_status = {
    "running": False,
    "progress": 0,
    "message": "",
    "stats": None,
    "error": None,
    "started_at": None,
    "pid": None,
}


def _check_ingestion_status():
    """Check if subprocess ingestion is running by reading status file."""
    global _ingestion_status

    # Check if status file exists and is recent (updated in last 10 seconds)
    if _status_file.exists():
        try:
            with open(_status_file, 'r') as f:
                file_status = json.load(f)

            # Check if process is still running
            if file_status.get("pid"):
                try:
                    os.kill(file_status["pid"], 0)  # Check if process exists
                    _ingestion_status.update(file_status)
                except OSError:
                    # Process doesn't exist anymore
                    _ingestion_status["running"] = False
        except Exception as e:
            logger.debug(f"Error reading status file: {e}")


def render_document_explorer():
    """Render the document explorer interface."""
    st.header("📁 Document Explorer")

    # Check subprocess ingestion status
    _check_ingestion_status()

    # Show ingestion status banner if running (no auto-refresh)
    if _ingestion_status.get("running", False):
        elapsed = int(time.time() - _ingestion_status.get("started_at", time.time()))
        elapsed_str = f"{elapsed // 60}m {elapsed % 60}s" if elapsed > 60 else f"{elapsed}s"

        st.info(
            f"🔄 **Ingestion in progress** ({elapsed_str})\n\n"
            f"{_ingestion_status.get('message', 'Processing...')}\n\n"
            f"Manually refresh this page to see updated progress."
        )

        # Removed auto-refresh to prevent UI freezes

    # Show completion message if just finished
    elif _ingestion_status["stats"]:
        stats = _ingestion_status["stats"]
        st.success(
            f"✅ **Ingestion complete!**\n\n"
            f"- Total files: {stats['total_files']}\n"
            f"- Successfully processed: {stats['successful']}\n"
            f"- Failed: {stats['failed']}\n"
            f"- Skipped (existing): {stats['skipped']}\n"
            f"- Total chunks added: {stats['total_chunks']}"
        )

        if st.button("Clear this message"):
            _ingestion_status["stats"] = None
            st.rerun()

    # Show error if ingestion failed
    elif _ingestion_status["error"]:
        st.error(f"❌ Ingestion failed: {_ingestion_status['error']}")

        if st.button("Clear error message"):
            _ingestion_status["error"] = None
            st.rerun()

    # Get vector store stats (with timeout to prevent hanging)
    try:
        vector_store = get_vector_store()
        # Just get basic count, don't compute expensive stats
        doc_count = vector_store.collection.count()
        stats = {
            "document_count": doc_count,
            "collection_name": vector_store.collection.name,
            "doc_types": {},  # Skip expensive doc_types computation
            "persist_directory": vector_store.persist_directory
        }
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

    # Skip expensive network check - assume success
    success = True
    message = "Network check disabled for performance"

    if success:
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")
        st.warning("Please ensure Q:\\ drive is accessible before ingesting documents.")

    col1, col2 = st.columns(2)

    with col1:
        # Disable button if ingestion is already running
        button_disabled = _ingestion_status["running"]
        button_label = "🔄 Ingestion Running..." if button_disabled else "🔄 Ingest Documents"

        if st.button(button_label, use_container_width=True, type="primary", disabled=button_disabled):
            run_ingestion()

    with col2:
        if st.button("🗑️ Clear Database", use_container_width=True):
            confirm_clear_database()

    # Browse source files section removed for performance

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


def _background_ingestion_worker():
    """Background worker that performs the actual ingestion."""
    global _ingestion_status

    try:
        _ingestion_status["message"] = "Initializing ingestion pipeline..."
        pipeline = IngestionPipeline(skip_existing=True)

        _ingestion_status["message"] = "Scanning documents from Q:\\ drive..."
        logger.info("Starting background ingestion")

        # Run ingestion
        stats = pipeline.ingest_directory()

        # Update status with results
        _ingestion_status["running"] = False
        _ingestion_status["stats"] = stats
        _ingestion_status["message"] = "Ingestion complete!"

        logger.info(f"Background ingestion completed: {stats}")

    except Exception as e:
        _ingestion_status["running"] = False
        _ingestion_status["error"] = str(e)
        _ingestion_status["message"] = "Ingestion failed"
        logger.error(f"Background ingestion error: {e}")
        logger.exception("Full traceback:")


def run_ingestion():
    """Start document ingestion as separate subprocess."""
    global _ingestion_status

    # Check if already running
    _check_ingestion_status()
    if _ingestion_status["running"]:
        st.warning("Ingestion is already running!")
        return

    try:
        # Start ingestion as subprocess
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "ingest_documents.py"

        # Redirect output to log files to prevent pipe blocking
        log_dir = Path("/app/logs")
        log_dir.mkdir(exist_ok=True)
        stdout_log = log_dir / "ingestion_stdout.log"
        stderr_log = log_dir / "ingestion_stderr.log"

        # Open log files (will be closed by subprocess when it exits)
        out_f = open(stdout_log, 'w')
        err_f = open(stderr_log, 'w')

        process = subprocess.Popen(
            ["python3", str(script_path), "--log-level", "INFO"],
            stdout=out_f,
            stderr=err_f,
            start_new_session=True,  # Detach from parent
            cwd="/app",  # Set working directory
            close_fds=False  # Let subprocess inherit file descriptors
        )

        # Close file descriptors in parent process
        out_f.close()
        err_f.close()

        # Write initial status to file
        status = {
            "running": True,
            "progress": 0,
            "message": "Starting ingestion...",
            "stats": None,
            "error": None,
            "started_at": time.time(),
            "pid": process.pid,
        }

        with open(_status_file, 'w') as f:
            json.dump(status, f)

        _ingestion_status.update(status)

        st.success(f"✅ Ingestion started as separate process (PID: {process.pid})! You can navigate away or even close this page.")
        logger.info(f"Started ingestion subprocess with PID: {process.pid}")

        # Rerun to show the status banner
        time.sleep(0.5)
        st.rerun()

    except Exception as e:
        st.error(f"Failed to start ingestion: {e}")
        logger.error(f"Error starting ingestion subprocess: {e}")


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


def scan_network_share():
    """Scan network share for available documents (on-demand)."""
    with st.spinner("Scanning network share..."):
        try:
            accessor = NetworkPathAccessor()
            doc_path = accessor.get_document_path()

            # List available documents (no metadata fetching)
            documents = accessor.list_documents(
                path=doc_path, extensions=[".pdf", ".docx", ".xlsx", ".csv"]
            )

            if documents:
                st.success(f"✅ Found {len(documents)} documents in network share")

                # Group by subdirectory (top-level only)
                by_dir = {}
                for doc in documents:
                    rel_path = doc.relative_to(doc_path)
                    dir_name = rel_path.parts[0] if len(rel_path.parts) > 1 else "Root"

                    if dir_name not in by_dir:
                        by_dir[dir_name] = []
                    by_dir[dir_name].append(doc)

                # Display directory summary (no individual file details)
                st.markdown("### Directory Summary")
                for dir_name, docs in sorted(by_dir.items()):
                    # Count file types
                    types = {}
                    for doc in docs:
                        ext = doc.suffix.lower()
                        types[ext] = types.get(ext, 0) + 1

                    type_str = ", ".join([f"{ext}: {count}" for ext, count in types.items()])
                    st.text(f"📁 {dir_name}: {len(docs)} files ({type_str})")

            else:
                st.warning("No documents found in network share")

        except Exception as e:
            st.error(f"Error scanning network share: {e}")
            logger.error(f"Error browsing source files: {e}")


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

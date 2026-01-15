"""
Chat interface component for CoOpAssist.
Handles the conversational interface for asking questions.
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
from loguru import logger

from src.workflows.graphs.simple_rag import SimpleRAGWorkflow
from src.workflows.graphs.multi_step_rag import MultiStepRAGWorkflow
from src.workflows.graphs.intelligent_agent import IntelligentAgent


def render_chat_interface():
    """Render the main chat interface."""
    st.header("💬 Chat with Student Testing & Product Research Documentation")

    # Chat configuration
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        workflow_type = st.selectbox(
            "Workflow",
            ["Intelligent Agent (Recommended)", "Simple RAG", "Multi-Step RAG"],
            help="Intelligent Agent automatically routes queries. Simple for quick questions, Multi-Step for complex queries",
        )

    with col2:
        top_k = st.slider(
            "Context chunks",
            min_value=1,
            max_value=20,
            value=5,
            help="Number of relevant chunks to retrieve (searches ALL documents)",
        )

    with col3:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.markdown("---")

    # Display chat messages
    chat_container = st.container()

    with chat_container:
        if not st.session_state.messages:
            # Welcome message
            with st.chat_message("assistant", avatar="📚"):
                st.markdown(
                    """
                    👋 **Welcome to CoOpAssist!**

                    I'm here to help you find information across **all your Student Testing and Product Research documentation**.
                    The system automatically searches through all documents in the database.

                    Ask me anything about:
                    - Student testing procedures and protocols
                    - Product research data and reports
                    - Test results and analysis
                    - Research methodologies
                    - Product specifications
                    - Testing standards and requirements

                    **Try asking:**
                    - "What are the student testing procedures?"
                    - "Find product research reports from recent studies"
                    - "What testing standards are we following?"
                    """
                )
        else:
            # Display message history
            for message in st.session_state.messages:
                with st.chat_message(message["role"], avatar=message.get("avatar", None)):
                    st.markdown(message["content"])

                    # Display sources if available
                    if message.get("sources"):
                        with st.expander(f"📚 Sources ({len(message['sources'])})"):
                            for i, source in enumerate(message["sources"], start=1):
                                source_name = Path(source["file"]).name
                                page = source.get("page", "")
                                page_info = f" - Page {page}" if page else ""
                                doc_type = source.get("doc_type", "unknown")

                                st.markdown(
                                    f"**{i}.** `{source_name}`{page_info} *({doc_type})*"
                                )

    # Chat input
    if prompt := st.chat_input("Ask a question about student testing or product research..."):
        # Validate settings
        if not st.session_state.settings.validate_api_key():
            st.error(
                f"⚠️ API key not configured for {st.session_state.settings.llm_provider}. "
                "Please configure in Settings."
            )
            return

        # Add user message
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "avatar": "👤"}
        )

        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant", avatar="📚"):
            with st.spinner("Searching student testing & product research documentation..."):
                try:
                    # Select workflow
                    if workflow_type == "Intelligent Agent (Recommended)":
                        workflow = IntelligentAgent(top_k=top_k)
                        result = workflow.run(prompt)
                    elif workflow_type == "Multi-Step RAG":
                        workflow = MultiStepRAGWorkflow(top_k=top_k)
                        result = workflow.run(prompt)
                    else:
                        workflow = SimpleRAGWorkflow(
                            use_query_expansion=False, top_k=top_k
                        )
                        result = workflow.run(prompt)

                    # Display answer
                    st.markdown(result["answer"])

                    # Display sources
                    if result.get("sources"):
                        with st.expander(
                            f"📚 Sources ({len(result['sources'])})", expanded=True
                        ):
                            for i, source in enumerate(result["sources"], start=1):
                                source_name = Path(source["file"]).name
                                page = source.get("page", "")
                                page_info = f" - Page {page}" if page else ""
                                doc_type = source.get("doc_type", "unknown")

                                st.markdown(
                                    f"**{i}.** `{source_name}`{page_info} *({doc_type})*"
                                )

                    # Add assistant message to history
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": result.get("sources", []),
                            "avatar": "📚",
                        }
                    )

                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Error in chat interface: {e}")
                    logger.exception("Full traceback:")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_msg,
                            "avatar": "❌",
                        }
                    )

    # Export conversation
    if st.session_state.messages:
        st.markdown("---")
        col1, col2 = st.columns([3, 1])

        with col2:
            if st.button("💾 Export Chat", use_container_width=True):
                export_conversation()


def export_conversation():
    """Export conversation to a text file."""
    if not st.session_state.messages:
        st.warning("No messages to export")
        return

    # Build conversation text
    lines = ["CoOpAssist Chat Export", "=" * 60, ""]
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Model: {st.session_state.settings.llm_provider}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    for i, message in enumerate(st.session_state.messages, start=1):
        role = "You" if message["role"] == "user" else "CoOpAssist"
        lines.append(f"[{role}]")
        lines.append(message["content"])

        if message.get("sources"):
            lines.append("")
            lines.append("Sources:")
            for j, source in enumerate(message["sources"], start=1):
                source_name = Path(source["file"]).name
                page = source.get("page", "")
                page_info = f" (Page {page})" if page else ""
                lines.append(f"  {j}. {source_name}{page_info}")

        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    conversation_text = "\n".join(lines)

    # Offer download
    st.download_button(
        label="📥 Download Chat History",
        data=conversation_text,
        file_name=f"coopassist_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
    )

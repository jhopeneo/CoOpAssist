"""
QmanAssist - Main Streamlit Application
AI-powered quality documentation assistant for Neocon International.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
from loguru import logger

from config.settings import get_settings
from src.utils.logging_config import setup_logging
from src.ui.components.chat_interface import render_chat_interface
from src.ui.components.settings_panel import render_settings_panel
from src.ui.components.document_explorer import render_document_explorer


# Page configuration
st.set_page_config(
    page_title="QmanAssist - Quality Documentation Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "settings" not in st.session_state:
        st.session_state.settings = get_settings()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "chat"

    if "initialized" not in st.session_state:
        setup_logging(log_level=st.session_state.settings.log_level)
        logger.info("QmanAssist application started")
        st.session_state.initialized = True


def render_header():
    """Render application header."""
    # Removed ingestion status banner - was causing UI freezes
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("📚 QmanAssist")
        st.caption("AI-Powered Quality Documentation Assistant | Neocon International")

    with col2:
        # Status indicator (removed DB check to improve speed)
        settings = st.session_state.settings
        if settings.validate_api_key():
            st.success(f"🟢 {settings.llm_provider.upper()} Connected")
        else:
            st.error(f"🔴 {settings.llm_provider.upper()} Not Configured")


def render_sidebar():
    """Render sidebar navigation and settings."""
    with st.sidebar:
        # Branding header
        st.markdown("""
        <div style='text-align: center; padding: 10px 0;'>
            <h1 style='color: #1f77b4; margin: 0; font-size: 28px;'>📚 QmanAssist</h1>
            <p style='color: #666; margin: 5px 0 0 0; font-size: 12px;'>Quality Documentation Assistant</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation
        st.subheader("Navigation")

        if st.button("💬 Chat", use_container_width=True, type="primary" if st.session_state.current_page == "chat" else "secondary"):
            st.session_state.current_page = "chat"
            st.rerun()

        if st.button("📁 Documents", use_container_width=True, type="primary" if st.session_state.current_page == "documents" else "secondary"):
            st.session_state.current_page = "documents"
            st.rerun()

        if st.button("⚙️ Settings", use_container_width=True, type="primary" if st.session_state.current_page == "settings" else "secondary"):
            st.session_state.current_page = "settings"
            st.rerun()

        st.markdown("---")

        # Removed stats from sidebar - was causing slowness
        # Stats now only shown on Documents page

        st.markdown("---")

        # Footer
        st.caption("© 2026 Neocon International")
        st.caption("Powered by Claude AI")


def main():
    """Main application entry point."""
    # Initialize
    initialize_session_state()

    # Render header
    render_header()

    # Render sidebar
    render_sidebar()

    # Render main content based on current page
    st.markdown("---")

    if st.session_state.current_page == "chat":
        render_chat_interface()

    elif st.session_state.current_page == "documents":
        render_document_explorer()

    elif st.session_state.current_page == "settings":
        render_settings_panel()


if __name__ == "__main__":
    main()

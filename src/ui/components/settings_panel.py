"""
Settings panel component for QmanAssist.
Allows configuration of LLM provider, models, and retrieval parameters.
"""

import streamlit as st
from loguru import logger

from config.settings import get_settings, reload_settings
from src.core.llm_factory import LLMFactory


def render_settings_panel():
    """Render the settings configuration panel."""
    st.header("⚙️ Settings")

    settings = st.session_state.settings

    # LLM Provider Settings
    st.subheader("🤖 LLM Provider Configuration")

    col1, col2 = st.columns(2)

    with col1:
        llm_provider = st.selectbox(
            "LLM Provider",
            ["openai", "claude", "ollama"],
            index=["openai", "claude", "ollama"].index(settings.llm_provider),
            help="Select the AI model provider",
        )

    with col2:
        # Model selection based on provider
        if llm_provider == "openai":
            models = [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo",
            ]
            default_model = "gpt-4-turbo-preview"
        elif llm_provider == "claude":
            models = [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ]
            default_model = "claude-3-5-sonnet-20241022"
        else:  # ollama
            models = ["llama3:8b", "llama3:70b", "mistral:7b"]
            default_model = "llama3:8b"

        current_model = (
            settings.llm_model if settings.llm_model in models else default_model
        )

        llm_model = st.selectbox(
            "Model",
            models,
            index=models.index(current_model),
            help="Select the specific model to use",
        )

    # API Key Configuration
    st.markdown("---")
    st.subheader("🔑 API Keys")

    api_key_updated = False

    if llm_provider in ["openai", "claude"]:
        key_field = (
            "openai_api_key" if llm_provider == "openai" else "anthropic_api_key"
        )
        current_key = getattr(settings, key_field, "")

        api_key = st.text_input(
            f"{llm_provider.upper()} API Key",
            value=current_key if current_key else "",
            type="password",
            help=f"Enter your {llm_provider.upper()} API key",
        )

        if api_key and api_key != current_key:
            api_key_updated = True

        # Test connection button
        if api_key:
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔌 Test Connection", use_container_width=True):
                    with st.spinner("Testing connection..."):
                        try:
                            # Temporarily update settings
                            setattr(settings, key_field, api_key)
                            factory = LLMFactory(settings)

                            # Test connection
                            success = factory.test_connection(llm_provider)

                            if success:
                                st.success("✅ Connection successful!")
                            else:
                                st.error("❌ Connection failed. Check your API key.")

                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            logger.error(f"Connection test failed: {e}")
    else:
        st.info("Ollama does not require an API key. Make sure Ollama is running locally.")

    # Model Parameters
    st.markdown("---")
    st.subheader("🎛️ Model Parameters")

    col1, col2 = st.columns(2)

    with col1:
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(settings.llm_temperature),
            step=0.1,
            help="Higher values make output more random, lower values more focused",
        )

    with col2:
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=8000,
            value=settings.llm_max_tokens,
            step=100,
            help="Maximum length of generated responses",
        )

    # Retrieval Settings
    st.markdown("---")
    st.subheader("🔍 Retrieval Settings")

    col1, col2 = st.columns(2)

    with col1:
        top_k = st.slider(
            "Documents to Retrieve (top_k)",
            min_value=1,
            max_value=20,
            value=settings.top_k,
            help="Number of relevant document chunks to retrieve",
        )

    with col2:
        similarity_threshold = st.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=float(settings.similarity_threshold),
            step=0.05,
            help="Minimum similarity score for retrieved documents",
        )

    # Chunking Settings
    st.markdown("---")
    st.subheader("✂️ Chunking Settings")

    col1, col2 = st.columns(2)

    with col1:
        chunk_size = st.number_input(
            "Chunk Size",
            min_value=100,
            max_value=2000,
            value=settings.chunk_size,
            step=50,
            help="Size of text chunks in characters",
        )

    with col2:
        chunk_overlap = st.number_input(
            "Chunk Overlap",
            min_value=0,
            max_value=500,
            value=settings.chunk_overlap,
            step=25,
            help="Overlap between chunks for context preservation",
        )

    # Save Settings
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Settings", use_container_width=True, type="primary"):
            # Update settings
            settings.llm_provider = llm_provider
            settings.llm_model = llm_model
            settings.llm_temperature = temperature
            settings.llm_max_tokens = max_tokens
            settings.top_k = top_k
            settings.similarity_threshold = similarity_threshold
            settings.chunk_size = chunk_size
            settings.chunk_overlap = chunk_overlap

            if api_key_updated and llm_provider == "openai":
                settings.openai_api_key = api_key
            elif api_key_updated and llm_provider == "claude":
                settings.anthropic_api_key = api_key

            st.session_state.settings = settings

            st.success("✅ Settings saved successfully!")
            logger.info("Settings updated via UI")

    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            st.session_state.settings = reload_settings()
            st.success("✅ Settings reset to defaults")
            st.rerun()

    # Current Configuration Display
    st.markdown("---")
    st.subheader("📋 Current Configuration")

    with st.expander("View Current Settings", expanded=False):
        st.json(
            {
                "llm_provider": settings.llm_provider,
                "llm_model": settings.llm_model,
                "temperature": settings.llm_temperature,
                "max_tokens": settings.llm_max_tokens,
                "top_k": settings.top_k,
                "similarity_threshold": settings.similarity_threshold,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "embedding_provider": settings.embedding_provider,
                "embedding_model": settings.embedding_model,
            }
        )

    # Help & Documentation
    st.markdown("---")
    st.subheader("📖 Help")

    with st.expander("API Key Setup"):
        st.markdown(
            """
            **OpenAI:**
            1. Visit https://platform.openai.com/api-keys
            2. Create a new API key
            3. Paste it in the field above

            **Anthropic Claude:**
            1. Visit https://console.anthropic.com/settings/keys
            2. Create a new API key
            3. Paste it in the field above

            **Ollama:**
            1. Install Ollama from https://ollama.ai
            2. Run `ollama serve` to start the server
            3. No API key required
            """
        )

    with st.expander("Model Selection Guide"):
        st.markdown(
            """
            **OpenAI GPT-4 Turbo:** Best quality, most expensive
            **OpenAI GPT-3.5 Turbo:** Fast and cost-effective

            **Claude 3.5 Sonnet:** Excellent reasoning, large context
            **Claude 3 Haiku:** Fast and efficient

            **Ollama:** Free, runs locally, requires powerful hardware
            """
        )

"""
LLM Factory for QmanAssist.
Provides a factory pattern for creating LLM and embedding instances
with support for multiple providers (OpenAI, Claude, Ollama).
"""

from typing import Optional, Any
from pathlib import Path
import yaml
from loguru import logger

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.schema.language_model import BaseLanguageModel
from langchain.schema.embeddings import Embeddings

from config.settings import Settings, get_settings


class LLMFactory:
    """Factory class for creating LLM instances based on provider configuration."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize LLM factory with settings.

        Args:
            settings: Application settings. If None, uses global settings.
        """
        self.settings = settings or get_settings()
        self.provider_config = self._load_provider_config()

    def _load_provider_config(self) -> dict:
        """Load provider configuration from YAML file."""
        config_path = Path("config/llm_providers.yaml")
        if config_path.exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        logger.warning(f"Provider config not found at {config_path}, using defaults")
        return {}

    def create_llm(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> BaseLanguageModel:
        """Create an LLM instance based on the specified provider.

        Args:
            provider: LLM provider name ('openai', 'claude', 'ollama').
                     If None, uses setting from config.
            model: Model name to use. If None, uses default from config.
            temperature: Sampling temperature. If None, uses default from config.
            max_tokens: Maximum tokens for response. If None, uses default from config.
            **kwargs: Additional provider-specific arguments.

        Returns:
            Configured LLM instance.

        Raises:
            ValueError: If provider is invalid or API key is missing.
        """
        provider = provider or self.settings.llm_provider
        model = model or self.settings.llm_model
        temperature = temperature if temperature is not None else self.settings.llm_temperature
        max_tokens = max_tokens or self.settings.llm_max_tokens

        logger.info(f"Creating LLM: provider={provider}, model={model}")

        if provider == "openai":
            return self._create_openai_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "claude":
            return self._create_claude_llm(model, temperature, max_tokens, **kwargs)
        elif provider == "ollama":
            return self._create_ollama_llm(model, temperature, max_tokens, **kwargs)
        else:
            raise ValueError(
                f"Invalid LLM provider: {provider}. "
                f"Supported providers: openai, claude, ollama"
            )

    def _create_openai_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ChatOpenAI:
        """Create OpenAI LLM instance."""
        api_key = self.settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in .env"
            )

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            **kwargs
        )

    def _create_claude_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ChatAnthropic:
        """Create Anthropic Claude LLM instance."""
        api_key = self.settings.anthropic_api_key
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY in .env"
            )

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            anthropic_api_key=api_key,
            **kwargs
        )

    def _create_ollama_llm(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> BaseLanguageModel:
        """Create Ollama LLM instance (local model)."""
        try:
            from langchain_community.llms import Ollama

            base_url = self.provider_config.get("providers", {}).get("ollama", {}).get(
                "base_url", "http://localhost:11434"
            )

            return Ollama(
                model=model,
                temperature=temperature,
                base_url=base_url,
                **kwargs
            )
        except ImportError:
            raise ImportError(
                "Ollama support requires langchain-community. "
                "Install with: pip install langchain-community"
            )

    def create_embeddings(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Embeddings:
        """Create an embeddings instance based on the specified provider.

        Args:
            provider: Embedding provider name. If None, uses setting from config.
            model: Embedding model name. If None, uses default from config.
            **kwargs: Additional provider-specific arguments.

        Returns:
            Configured embeddings instance.

        Raises:
            ValueError: If provider is invalid or API key is missing.
        """
        provider = provider or self.settings.embedding_provider
        model = model or self.settings.embedding_model

        logger.info(f"Creating embeddings: provider={provider}, model={model}")

        if provider == "openai":
            return self._create_openai_embeddings(model, **kwargs)
        elif provider == "sentence-transformers":
            return self._create_sentence_transformer_embeddings(model, **kwargs)
        else:
            raise ValueError(
                f"Invalid embedding provider: {provider}. "
                f"Supported providers: openai, sentence-transformers"
            )

    def _create_openai_embeddings(
        self,
        model: str,
        **kwargs
    ) -> OpenAIEmbeddings:
        """Create OpenAI embeddings instance."""
        api_key = self.settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in .env"
            )

        return OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            **kwargs
        )

    def _create_sentence_transformer_embeddings(
        self,
        model: str,
        **kwargs
    ) -> Embeddings:
        """Create Sentence Transformer embeddings instance (local)."""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(
                model_name=model,
                **kwargs
            )
        except ImportError:
            raise ImportError(
                "Sentence Transformers support requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            )

    def test_connection(self, provider: Optional[str] = None) -> bool:
        """Test connection to the specified LLM provider.

        Args:
            provider: Provider to test. If None, uses current provider setting.

        Returns:
            True if connection successful, False otherwise.
        """
        provider = provider or self.settings.llm_provider

        try:
            llm = self.create_llm(provider=provider)
            # Try a simple test query
            response = llm.invoke("Hello")
            logger.info(f"Connection test successful for provider: {provider}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed for provider {provider}: {str(e)}")
            return False

    def get_available_models(self, provider: Optional[str] = None) -> list[str]:
        """Get list of available models for a provider.

        Args:
            provider: Provider name. If None, uses current provider setting.

        Returns:
            List of available model names.
        """
        provider = provider or self.settings.llm_provider

        providers_config = self.provider_config.get("providers", {})
        provider_config = providers_config.get(provider, {})
        models = provider_config.get("models", {})

        return list(models.keys())


# Global factory instance
_factory_instance: Optional[LLMFactory] = None


def get_llm_factory(settings: Optional[Settings] = None) -> LLMFactory:
    """Get or create the global LLM factory instance.

    Args:
        settings: Application settings. If None, uses global settings.

    Returns:
        LLM factory instance.
    """
    global _factory_instance
    if _factory_instance is None or settings is not None:
        _factory_instance = LLMFactory(settings)
    return _factory_instance


def create_llm(**kwargs) -> BaseLanguageModel:
    """Convenience function to create an LLM instance.

    Args:
        **kwargs: Arguments passed to LLMFactory.create_llm()

    Returns:
        Configured LLM instance.
    """
    factory = get_llm_factory()
    return factory.create_llm(**kwargs)


def create_embeddings(**kwargs) -> Embeddings:
    """Convenience function to create an embeddings instance.

    Args:
        **kwargs: Arguments passed to LLMFactory.create_embeddings()

    Returns:
        Configured embeddings instance.
    """
    factory = get_llm_factory()
    return factory.create_embeddings(**kwargs)

"""
Configuration management for QmanAssist using Pydantic.
Loads settings from environment variables and provides type-safe access.
"""

from pathlib import Path
from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main settings class for QmanAssist application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ==================== LLM Provider Settings ====================
    llm_provider: Literal["openai", "claude", "ollama"] = Field(
        default="openai",
        description="LLM provider to use"
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )

    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic Claude API key"
    )

    # ==================== LLM Model Configuration ====================
    llm_model: str = Field(
        default="gpt-4-turbo-preview",
        description="LLM model name"
    )

    llm_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation"
    )

    llm_max_tokens: int = Field(
        default=2000,
        gt=0,
        description="Maximum tokens for LLM response"
    )

    # ==================== Embedding Configuration ====================
    embedding_provider: Literal["openai", "sentence-transformers"] = Field(
        default="openai",
        description="Embedding provider to use"
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name"
    )

    # ==================== Document Source Settings ====================
    qmanuals_path: str = Field(
        default="Q:\\",
        description="Path to quality manuals (local mount or network path)"
    )

    qmanuals_network_path: str = Field(
        default="//neonas-01/qmanuals",
        description="Network path to quality manuals"
    )

    smb_username: Optional[str] = Field(
        default=None,
        description="SMB username for network access"
    )

    smb_password: Optional[str] = Field(
        default=None,
        description="SMB password for network access"
    )

    smb_domain: Optional[str] = Field(
        default=None,
        description="SMB domain for network access"
    )

    # ==================== ChromaDB Configuration ====================
    chroma_db_path: str = Field(
        default="./data/chroma_db",
        description="Path to ChromaDB persistent storage"
    )

    chroma_collection_name: str = Field(
        default="qmanuals",
        description="ChromaDB collection name"
    )

    # ==================== Retrieval Settings ====================
    top_k: int = Field(
        default=5,
        gt=0,
        le=20,
        description="Number of documents to retrieve"
    )

    similarity_threshold: float = Field(
        default=0.35,  # Lowered to allow broader matches - L2 distances of ~1.85 will pass
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for retrieval (adjusted for L2 distance)"
    )

    # ==================== Chunking Configuration ====================
    chunk_size: int = Field(
        default=800,
        gt=0,
        description="Size of text chunks in tokens"
    )

    chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Overlap between chunks in tokens"
    )

    # ==================== Ingestion Performance Settings ====================
    ingestion_workers: int = Field(
        default=4,
        gt=0,
        le=32,
        description="Number of parallel workers for document ingestion"
    )

    ingestion_batch_size: int = Field(
        default=50,
        gt=0,
        description="Number of documents to process in a batch before adding to vector store"
    )

    # ==================== Application Settings ====================
    app_name: str = Field(
        default="QmanAssist",
        description="Application name"
    )

    app_port: int = Field(
        default=8501,
        gt=0,
        lt=65536,
        description="Application port"
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    # ==================== Streamlit Configuration ====================
    streamlit_server_port: int = Field(
        default=8501,
        gt=0,
        lt=65536,
        description="Streamlit server port"
    )

    streamlit_server_address: str = Field(
        default="localhost",
        description="Streamlit server address"
    )

    # ==================== Authentication Settings ====================
    auth_enabled: bool = Field(
        default=False,
        description="Enable authentication (LDAP/AD)"
    )

    ldap_server: Optional[str] = Field(
        default=None,
        description="LDAP/AD server hostname or IP (e.g., dc.neocon.local)"
    )

    ldap_port: int = Field(
        default=636,
        gt=0,
        lt=65536,
        description="LDAP port (389 for LDAP, 636 for LDAPS)"
    )

    ldap_use_ssl: bool = Field(
        default=True,
        description="Use LDAPS (SSL/TLS) for secure connection"
    )

    ldap_domain: Optional[str] = Field(
        default=None,
        description="AD domain name (e.g., NEOCON)"
    )

    ldap_base_dn: Optional[str] = Field(
        default=None,
        description="Base DN for user searches (e.g., DC=neocon,DC=local)"
    )

    ldap_bind_user: Optional[str] = Field(
        default=None,
        description="Service account for LDAP binding (optional, for group lookups)"
    )

    ldap_bind_password: Optional[str] = Field(
        default=None,
        description="Service account password (optional)"
    )

    ldap_user_search_filter: str = Field(
        default="(sAMAccountName={username})",
        description="LDAP search filter for users"
    )

    ldap_group_search_filter: str = Field(
        default="(member={user_dn})",
        description="LDAP search filter for groups"
    )

    ldap_allowed_groups: Optional[str] = Field(
        default=None,
        description="Comma-separated list of AD groups allowed access (e.g., QualityTeam,Admins)"
    )

    ldap_require_group: bool = Field(
        default=False,
        description="Require users to be in one of the allowed groups"
    )

    ldap_timeout: int = Field(
        default=10,
        gt=0,
        description="LDAP connection timeout in seconds"
    )

    session_timeout_minutes: int = Field(
        default=480,
        gt=0,
        description="Session timeout in minutes (default 8 hours)"
    )

    # ==================== Validators ====================
    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider selection."""
        valid_providers = ["openai", "claude", "ollama"]
        if v not in valid_providers:
            raise ValueError(f"LLM provider must be one of {valid_providers}")
        return v

    @field_validator("chroma_db_path")
    @classmethod
    def validate_chroma_path(cls, v: str) -> str:
        """Ensure ChromaDB path exists or can be created."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    # ==================== Helper Methods ====================
    def get_api_key(self) -> Optional[str]:
        """Get API key for the selected LLM provider."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        elif self.llm_provider == "claude":
            return self.anthropic_api_key
        elif self.llm_provider == "ollama":
            return None  # Ollama doesn't need API key
        return None

    def validate_api_key(self) -> bool:
        """Check if API key is configured for the selected provider."""
        if self.llm_provider in ["openai", "claude"]:
            api_key = self.get_api_key()
            return api_key is not None and len(api_key) > 0
        return True  # Ollama doesn't need API key

    def get_document_path(self) -> Path:
        """Get the document source path."""
        return Path(self.qmanuals_path)

    def is_network_path(self) -> bool:
        """Check if the document path is a network path."""
        path_str = self.qmanuals_path.lower()
        return path_str.startswith("//") or path_str.startswith("\\\\")


# Global settings instance
settings = Settings()


# Convenience function to reload settings
def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings()
    return settings


# Convenience function to get settings
def get_settings() -> Settings:
    """Get the current settings instance."""
    return settings

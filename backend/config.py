from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google AI
    google_api_key: str

    # Clerk Auth
    clerk_secret_key: str

    # Admin
    admin_token: str

    # Email (placeholder for v2)
    resend_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./metadata.db"

    # Vector DB
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "india_schemes"

    # RAG Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "gemini-1.5-flash"
    top_k: int = 15
    temperature: float = 0.4

    # Chunking (for scheme ingestion)
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Sync
    sitemap_url: str = "https://www.myscheme.gov.in/sitemap.xml"
    sync_batch_size: int = 50
    sync_delay_seconds: int = 1

    # File limits
    max_file_size_mb: int = 10

    # API
    api_title: str = "YojnaSaathi API"
    api_version: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

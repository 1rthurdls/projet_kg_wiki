from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Neo4j settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # API settings
    api_title: str = "Knowledge Graph Wiki API"
    api_version: str = "0.1.0"
    api_description: str = "FastAPI backend for querying Wikipedia knowledge graph"

    # CORS settings
    allowed_origins: list[str] = ["*"]

    # Debug mode
    debug: bool = False


settings = Settings()

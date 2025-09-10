from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    # Required settings
    OPENAI_API_KEY: str

    # Optional settings with defaults
    LLM_MODEL: str = "gpt-4-mini"
    MCP_SERVER_CONFIGS_PATH: str = "MCP/mcp_server_config.json"

    # FastAPI settings
    APP_NAME: str = "Human In The Loop Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LangFuse Tracking
    LANGFUSE_DEBUG: bool = False
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_HOST: str


@lru_cache
def get_settings() -> Settings:
    return Settings()

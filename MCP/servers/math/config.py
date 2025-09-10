from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVER_NAME: str = "Math"

    SERVER_TRANSPORT_PROTOCOL: str = "streamable-http"
    SERVER_PORT: int = 3111


@lru_cache
def get_settings() -> Settings:
    return Settings()

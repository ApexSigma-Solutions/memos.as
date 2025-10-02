from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    qdrant_url: Optional[str] = None
    neo4j_url: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Only initialize settings when needed, not at import time
settings = None


def get_settings():
    global settings
    if settings is None:
        settings = Settings()
    return settings

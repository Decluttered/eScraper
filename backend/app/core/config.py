from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "eScraper"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://escraper:escraper@localhost:5432/escraper"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: str = "http://localhost:5173"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @field_validator("frontend_origin", mode="before")
    @classmethod
    def _strip_trailing_slash(cls, value: object) -> object:
        if isinstance(value, str) and value.endswith("/"):
            return value.rstrip("/")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

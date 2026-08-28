from functools import lru_cache

from pydantic import AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "eScraper"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://escraper:escraper@localhost:5432/escraper"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origin: AnyHttpUrl = "http://localhost:5173"
    log_level: str = "INFO"
    ebay_client_id: SecretStr | None = None
    ebay_client_secret: SecretStr | None = None
    ebay_marketplace_id: str = "EBAY_DE"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

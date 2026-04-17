from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SNS Calendar API"
    environment: str = "development"

    model_config = SettingsConfigDict(env_prefix="SNS_CALENDAR_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


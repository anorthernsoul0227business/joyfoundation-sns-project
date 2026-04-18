from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    app_name: str = Field(default="SNS Calendar API", validation_alias="APP_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    frontend_url: Optional[str] = Field(default=None, validation_alias="FRONTEND_URL")
    supabase_url: Optional[str] = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(
        default=None,
        validation_alias="SUPABASE_ANON_KEY",
    )
    supabase_service_role_key: Optional[SecretStr] = Field(
        default=None,
        validation_alias="SUPABASE_SERVICE_ROLE_KEY"
    )

    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

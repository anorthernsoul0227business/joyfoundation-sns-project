from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _safe_env_file(levels: int) -> Path | None:
    """指定階層の .env パスを返す。Cloud Run 等浅い階層では None.

    ローカル開発では monorepo ルートの .env を使い、Cloud Run 等の
    コンテナ環境では存在しないので pathlib IndexError を避ける。
    """
    try:
        return Path(__file__).resolve().parents[levels] / ".env"
    except IndexError:
        return None


API_ENV_FILE = _safe_env_file(1)
ROOT_ENV_FILE = _safe_env_file(3)
_ENV_FILES = tuple(p for p in (API_ENV_FILE, ROOT_ENV_FILE) if p is not None)


class Settings(BaseSettings):
    app_name: str = Field(default="SNS Calendar API", validation_alias="APP_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    frontend_url: str | None = Field(default=None, validation_alias="FRONTEND_URL")
    allowed_origins: str | None = Field(default=None, validation_alias="ALLOWED_ORIGINS")
    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(
        default=None,
        validation_alias="SUPABASE_ANON_KEY",
    )
    supabase_service_role_key: SecretStr | None = Field(
        default=None,
        validation_alias="SUPABASE_SERVICE_ROLE_KEY"
    )
    x_consumer_key: str | None = Field(default=None, validation_alias="X_CONSUMER_KEY")
    x_consumer_secret: str | None = Field(
        default=None,
        validation_alias="X_CONSUMER_SECRET",
    )
    meta_app_id: str | None = Field(default=None, validation_alias="META_APP_ID")
    meta_app_secret: str | None = Field(
        default=None,
        validation_alias="META_APP_SECRET",
    )
    oauth_redirect_base: str | None = Field(
        default=None,
        validation_alias="OAUTH_REDIRECT_BASE",
    )
    smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=465, validation_alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, validation_alias="SMTP_USER")
    smtp_password: SecretStr | None = Field(
        default=None,
        validation_alias="SMTP_PASSWORD",
    )
    smtp_from_address: str | None = Field(
        default=None,
        validation_alias="SMTP_FROM_ADDRESS",
    )
    r2_account_id: str | None = Field(default=None, validation_alias="R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(
        default=None,
        validation_alias="R2_ACCESS_KEY_ID",
    )
    r2_secret_access_key: SecretStr | None = Field(
        default=None,
        validation_alias="R2_SECRET_ACCESS_KEY",
    )
    r2_bucket_name: str | None = Field(default=None, validation_alias="R2_BUCKET_NAME")
    r2_public_url: str | None = Field(default=None, validation_alias="R2_PUBLIC_URL")

    # ARCH-001: GitHub Actions Cron → /internal/publish/flush 認証トークン
    internal_api_token: SecretStr | None = Field(
        default=None,
        validation_alias="INTERNAL_API_TOKEN",
    )

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

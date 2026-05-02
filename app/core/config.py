from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GALPyra API"
    api_prefix: str = "/api"

    database_url: str = Field(alias="DATABASE_URL")

    jwt_secret: str = Field(min_length=32, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    cors_allowed_origins: str = Field(default="*", alias="CORS_ALLOWED_ORIGINS")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    auth_login_rate_limit: int = Field(default=10, alias="AUTH_LOGIN_RATE_LIMIT")
    sync_rate_limit: int = Field(default=30, alias="SYNC_RATE_LIMIT")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    aws_s3_bucket: str | None = Field(default=None, alias="AWS_S3_BUCKET")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(
        default=None,
        alias="AWS_SECRET_ACCESS_KEY",
    )
    aws_region: str | None = Field(default=None, alias="AWS_REGION")
    aws_s3_expected_bucket_owner: str | None = Field(
        default=None,
        alias="AWS_S3_EXPECTED_BUCKET_OWNER",
    )

    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@galpyra.com", alias="SMTP_FROM")
    frontend_url: str = Field(default="", alias="FRONTEND_URL")
    password_reset_token_expire_minutes: int = Field(
        default=15,
        alias="PASSWORD_RESET_TOKEN_EXPIRE_MINUTES",
    )

    yolo_mock: bool = Field(
        default=False,
        alias="YOLO_MOCK",
    )
    upload_dir: str = Field(default="./tmp_uploads", alias="UPLOAD_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# settings/config.py
from __future__ import annotations

from builtins import bool, int, str
from pydantic import Field, AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Auth / Security ---
    max_login_attempts: int = Field(default=3, description="Max failed login attempts before lock")
    secret_key: str = Field(default="secret-key", description="Legacy secret (if used elsewhere)")
    algorithm: str = Field(default="HS256", description="Legacy algorithm (if used elsewhere)")

    # JWT
    jwt_secret_key: str = Field(default="a_very_secret_key", description="JWT signing key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token TTL (minutes)")
    refresh_token_expire_minutes: int = Field(default=1440, description="Refresh token TTL (minutes)")

    # --- Server / App ---
    server_base_url: AnyUrl = Field(default="http://localhost", description="Base URL of the server")
    server_download_folder: str = Field(default="downloads", description="Folder for storing downloaded files")
    admin_user: str = Field(default="admin", description="Default admin username")
    admin_password: str = Field(default="secret", description="Default admin password")
    debug: bool = Field(default=False, description="Debug mode outputs errors and sqlalchemy queries")

    # --- Database (async at runtime) ---
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@postgres/myappdb",
        description="URL for connecting to the database",
    )

    # Optional DB components (if you ever build the URL dynamically)
    postgres_user: str = Field(default="user", description="PostgreSQL username")
    postgres_password: str = Field(default="password", description="PostgreSQL password")
    postgres_server: str = Field(default="localhost", description="PostgreSQL server address")
    postgres_port: str = Field(default="5432", description="PostgreSQL port")
    postgres_db: str = Field(default="myappdb", description="PostgreSQL database name")

    # --- Discord / OpenAI ---
    discord_bot_token: str = Field(default="NONE", description="Discord bot token")
    discord_channel_id: int = Field(default=1234567890, description="Default Discord channel ID for the bot to interact")
    openai_api_key: str = Field(default="NONE", description="Open AI Api Key")

    # --- Email / SMTP ---
    send_real_mail: bool = Field(default=False, description="use mock")
    smtp_server: str = Field(default="smtp.mailtrap.io", description="SMTP server for sending emails")
    smtp_port: int = Field(default=2525, description="SMTP port for sending emails")
    smtp_username: str = Field(default="your-mailtrap-username", description="Username for SMTP server")
    smtp_password: str = Field(default="your-mailtrap-password", description="Password for SMTP server")

    # --- S3 / MinIO (NEW) ---
    s3_endpoint: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT", description="S3/MinIO endpoint URL")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION", description="S3 region")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY", description="S3 access key")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY", description="S3 secret key")
    s3_bucket: str = Field(default="profile-pics", alias="S3_BUCKET", description="Bucket for profile pictures")
    s3_use_ssl: bool = Field(default=False, alias="S3_USE_SSL", description="Use SSL for S3 endpoint")
    s3_force_path_style: bool = Field(default=True, alias="S3_FORCE_PATH_STYLE", description="Force path-style addressing")

    # --- Avatar constraints (NEW) ---
    max_avatar_mb: int = Field(default=5, alias="MAX_AVATAR_MB", description="Max avatar size in MB")
    avatar_allowed_mime: str = Field(
        default="image/jpeg,image/png,image/webp",
        alias="AVATAR_ALLOWED_MIME",
        description="Comma-separated allowed MIME types",
    )
    avatar_resize_max: int = Field(default=512, alias="AVATAR_RESIZE_MAX", description="Max width/height in px (0 disables)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",         # <- IMPORTANT: don't crash on unknown keys like ALEMBIC_DATABASE_URL
        case_sensitive=False,
    )


# Instantiate settings to be imported in your application
settings = Settings()

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings. Secrets come from the process environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "gd-os"
    product_name: str = "Gamers District Operating System"
    cafe_timezone: str = "Asia/Kolkata"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://gdos:change-me@localhost:5432/gdos"
    jwt_secret: str = "change-me"
    jwt_ttl_hours: int = 12
    admin_username: str = Field(default="admin", validation_alias="GD_OS_ADMIN_USERNAME")
    admin_password: str = Field(default="change-me", validation_alias="GD_OS_ADMIN_PASSWORD")
    login_attempt_limit: int = 5
    login_window_seconds: int = 300


def get_settings() -> Settings:
    return Settings()

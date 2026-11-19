from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings. Secrets come from the process environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "gd-os"
    product_name: str = "Gamers District Operating System"
    cafe_timezone: str = "Asia/Kolkata"
    log_level: str = "info"
    database_url: str = "postgresql+psycopg://gdos:change-me@localhost:5432/gdos"


def get_settings() -> Settings:
    return Settings()

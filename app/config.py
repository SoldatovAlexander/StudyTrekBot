from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-v4-flash:free"

    database_url: str = "sqlite:///./data/app.db"
    catalog_seed_path: Path = Field(default=Path("./data/catalog_seed.json"))
    google_sheets_spreadsheet_id: str = "1Ur-UDG6lvvxW3X7VORZ6KqPmBqRkdM0qLxVmdjxzkYU"
    catalog_auto_sync_enabled: bool = False
    catalog_auto_sync_time: str = "03:00"
    catalog_auto_sync_timezone: str = "Europe/Moscow"

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// DATABASE_URL is supported in the MVP.")
        return Path(self.database_url.removeprefix(prefix))


@lru_cache
def get_settings() -> Settings:
    return Settings()

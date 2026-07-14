from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def extract_google_spreadsheet_id(value: str) -> str:
    spreadsheet = value.strip()
    if not spreadsheet:
        raise ValueError("Google Sheets spreadsheet URL or ID is empty.")
    marker = "/spreadsheets/d/"
    if marker not in spreadsheet:
        return spreadsheet
    return spreadsheet.split(marker, 1)[1].split("/", 1)[0].strip()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-v4-flash:free"

    database_url: str = "sqlite:///./data/app.db"
    catalog_seed_path: Path = Field(default=Path("./data/catalog_seed.json"))
    google_sheets_spreadsheet_url: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    catalog_auto_sync_enabled: bool = False
    catalog_auto_sync_time: str = "03:00"
    catalog_auto_sync_timezone: str = "Europe/Moscow"

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("Only sqlite:/// DATABASE_URL is supported in the MVP.")
        return Path(self.database_url.removeprefix(prefix))

    @property
    def catalog_spreadsheet_id(self) -> str:
        spreadsheet = self.google_sheets_spreadsheet_url or self.google_sheets_spreadsheet_id
        if not spreadsheet:
            raise ValueError("Set GOOGLE_SHEETS_SPREADSHEET_URL in .env before syncing the catalog.")
        return extract_google_spreadsheet_id(spreadsheet)


@lru_cache
def get_settings() -> Settings:
    return Settings()

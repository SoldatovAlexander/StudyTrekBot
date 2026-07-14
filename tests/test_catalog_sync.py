from app.catalog_sync import CatalogSyncScheduler, parse_hhmm
from app.config import Settings, extract_google_spreadsheet_id


SPREADSHEET_ID = "1Ur-UDG6lvvxW3X7VORZ6KqPmBqRkdM0qLxVmdjxzkYU"
SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit?gid=1023357165#gid=1023357165"


def test_parse_hhmm() -> None:
    parsed = parse_hhmm("03:15")

    assert parsed.hour == 3
    assert parsed.minute == 15


def test_extract_google_spreadsheet_id_from_url() -> None:
    assert extract_google_spreadsheet_id(SPREADSHEET_URL) == SPREADSHEET_ID


def test_catalog_spreadsheet_id_uses_url() -> None:
    settings = Settings(google_sheets_spreadsheet_url=SPREADSHEET_URL)

    assert settings.catalog_spreadsheet_id == SPREADSHEET_ID


def test_catalog_sync_scheduler_disabled_by_default(tmp_path) -> None:
    scheduler = CatalogSyncScheduler(
        Settings(
            catalog_auto_sync_enabled=False,
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            catalog_seed_path=tmp_path / "catalog.json",
        )
    )

    scheduler.start()

    assert not scheduler.is_running
    assert scheduler.status()["enabled"] is False

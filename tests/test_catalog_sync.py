from app.catalog_sync import CatalogSyncScheduler, parse_hhmm
from app.config import Settings


def test_parse_hhmm() -> None:
    parsed = parse_hhmm("03:15")

    assert parsed.hour == 3
    assert parsed.minute == 15


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


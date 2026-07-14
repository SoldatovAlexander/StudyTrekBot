import asyncio
import logging
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import Settings
from scripts.sync_google_sheet_catalog import sync_catalog


logger = logging.getLogger(__name__)


class CatalogSyncScheduler:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task | None = None
        self._last_result: dict | None = None
        self._last_error: str | None = None
        self._next_run_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> dict:
        return {
            "enabled": self.settings.catalog_auto_sync_enabled,
            "running": self.is_running,
            "time": self.settings.catalog_auto_sync_time,
            "timezone": self.settings.catalog_auto_sync_timezone,
            "next_run_at": self._next_run_at.isoformat() if self._next_run_at else None,
            "last_error": self._last_error,
            "last_result": self._last_result,
        }

    def start(self) -> None:
        if not self.settings.catalog_auto_sync_enabled:
            logger.info("Catalog auto sync is disabled.")
            return
        if self.is_running:
            return
        self._task = asyncio.create_task(self._run_loop(), name="catalog-auto-sync")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def sync_once(self) -> dict:
        logger.info("Starting Google Sheets catalog sync.")
        try:
            payload = await asyncio.to_thread(
                sync_catalog,
                self.settings.google_sheets_spreadsheet_id,
                Path(self.settings.catalog_seed_path),
            )
        except Exception as exc:
            self._last_error = f"{type(exc).__name__}: {exc}"
            logger.exception("Google Sheets catalog sync failed.")
            raise

        self._last_error = None
        self._last_result = payload["source"]
        logger.info(
            "Google Sheets catalog sync complete: %s lessons, %s sheets.",
            payload["source"]["lesson_count"],
            payload["source"]["sheet_count"],
        )
        return payload["source"]

    async def _run_loop(self) -> None:
        while True:
            delay = self._seconds_until_next_run()
            logger.info("Next catalog auto sync at %s.", self._next_run_at)
            await asyncio.sleep(delay)
            try:
                await self.sync_once()
            except Exception:
                # Keep the scheduler alive; the next nightly run can recover.
                pass

    def _seconds_until_next_run(self) -> float:
        zone = ZoneInfo(self.settings.catalog_auto_sync_timezone)
        now = datetime.now(zone)
        target_time = parse_hhmm(self.settings.catalog_auto_sync_time)
        next_run = datetime.combine(now.date(), target_time, tzinfo=zone)
        if next_run <= now:
            next_run += timedelta(days=1)
        self._next_run_at = next_run
        return max(1.0, (next_run - now).total_seconds())


def parse_hhmm(value: str) -> time:
    try:
        hour, minute = value.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except Exception as exc:
        raise ValueError("catalog_auto_sync_time must use HH:MM format") from exc


from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from app.container import Container, get_container
from app.models import GeneratedTrack, StudentProfile
from app.renderer import render_track
from app.telegram_adapter import TelegramWebhookHandler


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = get_container()
    container.catalog_sync_scheduler.start()
    try:
        yield
    finally:
        await container.catalog_sync_scheduler.stop()


app = FastAPI(title="Learning Track Bot MVP", lifespan=lifespan)


def get_telegram_handler(container: Container) -> TelegramWebhookHandler:
    token = container.settings.telegram_bot_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TELEGRAM_BOT_TOKEN is not configured.",
        )
    return TelegramWebhookHandler(token, container.dialog_manager)


@app.get("/health")
def health(container: Container = Depends(get_container)) -> dict:
    return {
        "status": "ok",
        "llm": {"configured": container.llm_client.is_configured, "model": container.settings.openrouter_model},
        "database": container.database.health(),
        "catalog": container.catalog.status(),
        "catalog_sync": container.catalog_sync_scheduler.status(),
    }


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    container: Container = Depends(get_container),
) -> dict[str, bool]:
    expected_secret = container.settings.telegram_webhook_secret
    if expected_secret and x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret.")
    handler = get_telegram_handler(container)
    await handler.feed_update(await request.json())
    return {"ok": True}


@app.get("/admin/catalog/status")
def catalog_status(container: Container = Depends(get_container)) -> dict:
    return {"catalog": container.catalog.status(), "sync": container.catalog_sync_scheduler.status()}


@app.post("/admin/sync-catalog")
async def sync_catalog_now(container: Container = Depends(get_container)) -> dict:
    try:
        result = await container.catalog_sync_scheduler.sync_once()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Catalog sync failed: {type(exc).__name__}: {exc}",
        ) from exc
    return {"ok": True, "result": result, "catalog": container.catalog.status()}


@app.post("/tracks/generate")
async def generate_track(profile: StudentProfile, container: Container = Depends(get_container)) -> dict:
    if not profile.is_ready_for_track:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"missing_fields": profile.missing_required_fields()},
        )
    track = await container.track_builder.build(profile, container.catalog.filter_lessons_for_profile(profile))
    container.database.save_track(None, track)
    return {"track": track, "text": render_track(track)}


@app.get("/tracks/{track_id}", response_model=GeneratedTrack)
def get_track(track_id: str, container: Container = Depends(get_container)) -> GeneratedTrack:
    track = container.database.get_track(track_id)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found.")
    return track

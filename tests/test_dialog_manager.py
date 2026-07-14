from app.catalog import CatalogRepository
from app.database import Database
from app.dialog_manager import DialogManager
from app.models import StudentProfile
from app.track_builder import TrackBuilder


class StaticProfileExtractor:
    async def merge_from_message(self, profile, message):
        return StudentProfile(
            goal="ai_assistant",
            target_result="собрать AI-ассистента",
            technical_level="beginner",
            role="sales",
            weekly_time="3-5 hours",
        )


class StaticCourseMatcher:
    async def match(self, message, course_titles):
        return ["Нейропродажник"], [], "AI для продаж"


class AsyncTrackBuilder:
    def __init__(self):
        self.fallback = TrackBuilder()
        self.seen_lessons = []

    async def build(self, profile, lessons):
        self.seen_lessons = lessons
        return self.fallback.build(profile, lessons)


def test_dialog_manager_limits_track_to_matched_courses(tmp_path) -> None:
    track_builder = AsyncTrackBuilder()
    manager = DialogManager(
        database=Database(tmp_path / "test.db"),
        catalog=CatalogRepository(seed_path="data/catalog_seed.json"),
        track_builder=track_builder,
        profile_extractor=StaticProfileExtractor(),
        course_matcher=StaticCourseMatcher(),
    )

    response = awaitable(manager.handle_message("user-1", "купил курс продаж"))

    assert response.profile.package_name == "AI для продаж"
    assert response.profile.available_course_titles == ["Нейропродажник"]
    assert {lesson.course_title for lesson in track_builder.seen_lessons} == {"Нейропродажник"}
    assert "Я учел только эти купленные курсы" in response.reply


def awaitable(coro):
    import asyncio

    return asyncio.run(coro)

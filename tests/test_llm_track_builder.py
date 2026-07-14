import json

from app.llm_track_builder import LLMTrackBuilder
from app.models import Lesson, StudentProfile
from app.track_builder import TrackBuilder


class FakeLLMClient:
    is_configured = True

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "goal": "собрать AI-ассистента для продаж",
                "route_logic": "Сначала база, затем продажный сценарий.",
                "stages": [
                    {
                        "title": "База",
                        "why": "Нужна база промптов.",
                        "lesson_ids": ["1"],
                        "expected_result": "Понятна логика промптов.",
                    },
                    {
                        "title": "Продажи",
                        "why": "Нужен прикладной сценарий.",
                        "lesson_ids": ["2"],
                        "expected_result": "Готов сценарий ассистента.",
                    },
                ],
                "optional_lesson_ids": ["2"],
                "skipped_now": ["RAG"],
                "estimated_duration": "2-3 недели",
            },
            ensure_ascii=False,
        )


def test_llm_track_builder_uses_llm_selection() -> None:
    lessons = [
        Lesson(
            lesson_id="1",
            course_title="База ИИ",
            lesson_title="Промпты",
            track_position="start",
        ),
        Lesson(
            lesson_id="2",
            course_title="Продажи",
            lesson_title="AI-консультант",
            track_position="core",
        ),
    ]
    profile = StudentProfile(
        goal="ai_assistant",
        target_result="собрать AI-ассистента",
        technical_level="beginner",
        role="sales",
        weekly_time="3-5 hours",
    )

    track = awaitable(LLMTrackBuilder(FakeLLMClient(), TrackBuilder()).build(profile, lessons))

    assert track.generation_mode == "llm"
    assert track.route_logic == "Сначала база, затем продажный сценарий."
    assert [lesson.lesson_id for lesson in track.mandatory] == ["1"]
    assert [lesson.lesson_id for lesson in track.optional] == ["2"]


def test_llm_track_builder_limits_large_catalog_before_prompt() -> None:
    lessons = [
        Lesson(
            lesson_id=str(index),
            course_title="Курс",
            lesson_title=f"Урок {index}",
            level="beginner",
            roles=["sales"],
            topics=["ai_assistant"],
            mandatory_for_goals=["ai_assistant"],
        )
        for index in range(120)
    ]
    profile = StudentProfile(
        goal="ai_assistant",
        target_result="собрать AI-ассистента",
        technical_level="beginner",
        role="sales",
        weekly_time="3-5 hours",
    )
    builder = LLMTrackBuilder(FakeLLMClient(), TrackBuilder())

    limited = builder._limit_catalog_for_llm(profile, lessons)

    assert len(limited) == 80


def awaitable(coro):
    import asyncio

    return asyncio.run(coro)

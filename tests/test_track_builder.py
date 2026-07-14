from app.models import Lesson, StudentProfile
from app.track_builder import TrackBuilder


def test_builds_track_with_mandatory_and_optional_materials() -> None:
    lessons = [
        Lesson(
            lesson_id="1",
            course_title="База ИИ",
            lesson_title="Промпты",
            level="zero",
            roles=["sales"],
            topics=["ai_assistant"],
            mandatory_for_goals=["ai_assistant"],
            track_position="start",
            estimated_hours=2,
        ),
        Lesson(
            lesson_id="2",
            course_title="Автоматизация",
            lesson_title="n8n",
            level="beginner",
            roles=["sales"],
            topics=["no_code_automation"],
            mandatory_for_goals=["no_code_automation"],
            track_position="optional",
            estimated_hours=4,
        ),
    ]
    profile = StudentProfile(
        goal="ai_assistant",
        target_result="собрать AI-ассистента",
        technical_level="beginner",
        role="sales",
        weekly_time="3-5 hours",
        priority_topics=["no_code_automation"],
    )

    track = TrackBuilder().build(profile, lessons)

    assert track.mandatory[0].lesson_id == "1"
    assert track.optional[0].lesson_id == "2"
    assert track.stages[0].title == "Быстрый старт"


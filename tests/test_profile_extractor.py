from app.models import StudentProfile
from app.profile_extractor import merge_profile_from_message, next_question


def test_extracts_ready_sales_assistant_profile() -> None:
    profile = merge_profile_from_message(
        StudentProfile(),
        "Хочу делать AI-ассистента для продаж, я не программист, готов 3-4 часа в неделю.",
    )

    assert profile.goal == "ai_assistant"
    assert profile.target_result == "собрать AI-ассистента"
    assert profile.technical_level == "beginner"
    assert profile.role == "sales"
    assert profile.weekly_time == "3-5 hours"
    assert profile.is_ready_for_track


def test_asks_for_missing_technical_level() -> None:
    profile = StudentProfile(
        goal="ai_assistant",
        target_result="собрать AI-ассистента",
        role="sales",
        weekly_time="3-5 hours",
    )

    assert "техническая часть" in next_question(profile)


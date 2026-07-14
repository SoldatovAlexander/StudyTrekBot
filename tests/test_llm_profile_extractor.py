import json

from app.llm_profile_extractor import LLMProfileExtractor
from app.models import StudentProfile


class FakeProfileLLMClient:
    is_configured = True

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(
            {
                "goal": "ai_assistant",
                "target_result": "собрать AI-ассистента для отдела продаж",
                "technical_level": "beginner",
                "role": "sales",
                "weekly_time": "3-5 hours",
                "depth": "balanced",
                "known_tools": ["ChatGPT"],
                "priority_topics": ["sales", "no_code_automation"],
                "constraints": ["без глубокого программирования"],
                "package_name": "AI для продаж",
                "available_course_titles": ["AI-консультант и нейро-продажник"],
                "unmatched_course_titles": [],
                "strategy": "quick practical result",
            },
            ensure_ascii=False,
        )


def test_llm_profile_extractor_merges_llm_result() -> None:
    profile = awaitable(
        LLMProfileExtractor(FakeProfileLLMClient()).merge_from_message(
            StudentProfile(),
            "Хочу ассистента для продаж без кода, 3-4 часа в неделю.",
        )
    )

    assert profile.goal == "ai_assistant"
    assert profile.role == "sales"
    assert profile.weekly_time == "3-5 hours"
    assert "no_code_automation" in profile.priority_topics
    assert profile.package_name == "AI для продаж"
    assert profile.available_course_titles == ["AI-консультант и нейро-продажник"]


def awaitable(coro):
    import asyncio

    return asyncio.run(coro)

import json
import logging
import re
from typing import Any

from app.llm_client import OpenRouterClient
from app.models import StudentProfile
from app.profile_extractor import merge_profile_from_message


logger = logging.getLogger(__name__)


class LLMProfileExtractor:
    def __init__(self, llm_client: OpenRouterClient) -> None:
        self.llm_client = llm_client

    async def merge_from_message(self, profile: StudentProfile, message: str) -> StudentProfile:
        if not self.llm_client.is_configured:
            return merge_profile_from_message(profile, message)

        try:
            content = await self.llm_client.complete(
                system_prompt=self._system_prompt(),
                user_prompt=self._user_prompt(profile, message),
            )
            if not content:
                return merge_profile_from_message(profile, message)
            return self._profile_from_llm_json(profile, message, content)
        except Exception:
            logger.exception("LLM profile extraction failed; falling back to keyword extractor.")
            return merge_profile_from_message(profile, message)

    def _system_prompt(self) -> str:
        return (
            "Ты извлекаешь профиль слушателя из естественного русского текста для бота-навигатора по обучению. "
            "Обнови только те поля, которые явно или достаточно надежно следуют из нового сообщения. "
            "Не выдумывай факты. Если поле неизвестно, верни null или пустой список. "
            "Ответь строго JSON без markdown."
        )

    def _user_prompt(self, profile: StudentProfile, message: str) -> str:
        payload = {
            "current_profile": profile.model_dump(),
            "new_message": message,
            "allowed_values": {
                "goal": [
                    "ai_literacy",
                    "prompt_engineering",
                    "ai_assistant",
                    "ai_agent",
                    "no_code_automation",
                    "telegram_bot",
                    "web_ai_app",
                    "rag_knowledge_base",
                    "local_llm",
                    "ml_ds",
                    "commercial_ai_product",
                ],
                "technical_level": [
                    "zero",
                    "beginner",
                    "beginner_to_intermediate",
                    "intermediate",
                    "advanced",
                ],
                "role": [
                    "business",
                    "marketing",
                    "sales",
                    "manager",
                    "product",
                    "developer",
                    "data_scientist",
                    "analyst",
                    "teacher",
                    "hr",
                    "support",
                    "student",
                ],
                "weekly_time": ["up to 2 hours", "3-5 hours", "6-10 hours", "10+ hours"],
                "depth": ["short practical", "balanced", "deep"],
            },
            "required_json_schema": {
                "goal": "string|null",
                "target_result": "string|null",
                "technical_level": "string|null",
                "role": "string|null",
                "weekly_time": "string|null",
                "depth": "string|null",
                "known_tools": ["string"],
                "priority_topics": ["string"],
                "constraints": ["string"],
                "package_name": "string|null",
                "available_course_titles": ["string"],
                "unmatched_course_titles": ["string"],
                "strategy": "string|null",
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _profile_from_llm_json(self, profile: StudentProfile, message: str, content: str) -> StudentProfile:
        parsed = self._parse_json(content)
        fallback_profile = merge_profile_from_message(profile, message)
        data = profile.model_dump()

        for field in ["goal", "target_result", "technical_level", "role", "weekly_time", "depth", "package_name", "strategy"]:
            value = parsed.get(field)
            if isinstance(value, str) and value.strip():
                data[field] = value.strip()

        for field in [
            "known_tools",
            "priority_topics",
            "constraints",
            "available_course_titles",
            "unmatched_course_titles",
        ]:
            merged = set(data.get(field) or [])
            value = parsed.get(field)
            if isinstance(value, list):
                merged.update(str(item).strip() for item in value if str(item).strip())
            data[field] = sorted(merged)

        if message.strip():
            data["free_goal"] = message.strip()

        candidate = StudentProfile.model_validate(data)
        if len(candidate.missing_required_fields()) > len(fallback_profile.missing_required_fields()):
            return fallback_profile
        return candidate

    def _parse_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

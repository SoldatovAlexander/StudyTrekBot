import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any

from app.llm_client import OpenRouterClient


logger = logging.getLogger(__name__)


class CourseMatcher:
    def __init__(self, llm_client: OpenRouterClient) -> None:
        self.llm_client = llm_client

    async def match(self, message: str, course_titles: list[str]) -> tuple[list[str], list[str], str | None]:
        if not course_titles:
            return [], [], None

        local_matches = self._local_match(message, course_titles)
        if not self.llm_client.is_configured:
            return local_matches, [], None

        try:
            content = await self.llm_client.complete(
                system_prompt=self._system_prompt(),
                user_prompt=self._user_prompt(message, course_titles),
            )
            if not content:
                return local_matches, [], None
            parsed = self._parse_json(content)
            matched = self._valid_titles(parsed.get("matched_course_titles", []), course_titles)
            unmatched = self._unmatched_titles(parsed.get("unmatched_course_titles", []), course_titles)
            package_name = parsed.get("package_name")
            if not matched:
                matched = local_matches
            return matched, unmatched, str(package_name).strip() if package_name else None
        except Exception:
            logger.exception("LLM course matching failed; falling back to local matching.")
            return local_matches, [], None

    def _system_prompt(self) -> str:
        return (
            "Ты сопоставляешь список уже купленных курсов с точными названиями курсов из каталога. "
            "Выбирай только course_title из catalog_course_titles. Не выдумывай названия. "
            "Если пользователь назвал пакет, сохрани его в package_name. "
            "Ответь строго JSON без markdown."
        )

    def _user_prompt(self, message: str, course_titles: list[str]) -> str:
        payload = {
            "message": message,
            "catalog_course_titles": course_titles,
            "required_json_schema": {
                "package_name": "string|null",
                "matched_course_titles": ["string"],
                "unmatched_course_titles": ["string"],
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _valid_titles(self, titles: Any, course_titles: list[str]) -> list[str]:
        if not isinstance(titles, list):
            return []
        by_fold = {title.casefold(): title for title in course_titles}
        valid: list[str] = []
        for title in titles:
            normalized = str(title).strip().casefold()
            if normalized in by_fold:
                valid.append(by_fold[normalized])
        return sorted(set(valid), key=valid.index)

    def _unmatched_titles(self, titles: Any, course_titles: list[str]) -> list[str]:
        if not isinstance(titles, list):
            return []
        catalog_titles = {title.casefold() for title in course_titles}
        unmatched: list[str] = []
        for title in titles:
            normalized = str(title).strip()
            if normalized and normalized.casefold() not in catalog_titles:
                unmatched.append(normalized)
        return sorted(set(unmatched), key=unmatched.index)

    def _local_match(self, message: str, course_titles: list[str]) -> list[str]:
        text = message.casefold()
        matches: list[str] = []
        for title in course_titles:
            normalized_title = title.casefold()
            if normalized_title in text:
                matches.append(title)
                continue
            title_words = set(re.findall(r"[\w-]+", normalized_title))
            text_words = set(re.findall(r"[\w-]+", text))
            if title_words and len(title_words.intersection(text_words)) / len(title_words) >= 0.6:
                matches.append(title)
                continue
            if SequenceMatcher(None, normalized_title, text).ratio() >= 0.55:
                matches.append(title)
        return matches

    def _parse_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

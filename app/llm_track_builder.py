import json
import logging
import re
from typing import Any
from uuid import uuid4

from app.llm_client import OpenRouterClient
from app.models import GeneratedTrack, Lesson, StudentProfile, TrackStage
from app.track_builder import TrackBuilder


logger = logging.getLogger(__name__)


class LLMTrackBuilder:
    def __init__(self, llm_client: OpenRouterClient, fallback_builder: TrackBuilder) -> None:
        self.llm_client = llm_client
        self.fallback_builder = fallback_builder

    async def build(self, profile: StudentProfile, lessons: list[Lesson]) -> GeneratedTrack:
        if not self.llm_client.is_configured:
            return self.fallback_builder.build(profile, lessons)

        active_lessons = [lesson for lesson in lessons if lesson.status == "active"]
        if not active_lessons:
            return self.fallback_builder.build(profile, lessons)
        llm_lessons = self._limit_catalog_for_llm(profile, active_lessons)

        try:
            content = await self.llm_client.complete(
                system_prompt=self._system_prompt(),
                user_prompt=self._user_prompt(profile, llm_lessons),
            )
            if not content:
                return self.fallback_builder.build(profile, lessons)
            return self._track_from_llm_json(profile, llm_lessons, content)
        except Exception:
            logger.exception("LLM track generation failed; falling back to rule-based builder.")
            return self.fallback_builder.build(profile, lessons)

    def _limit_catalog_for_llm(self, profile: StudentProfile, lessons: list[Lesson]) -> list[Lesson]:
        if len(lessons) <= 80:
            return lessons
        scored = sorted(
            ((self.fallback_builder._score_lesson(profile, lesson), lesson) for lesson in lessons),
            key=lambda item: (-item[0], item[1].course_title, item[1].lesson_id),
        )
        selected = [lesson for score, lesson in scored if score >= 2][:80]
        if len(selected) < 20:
            selected = [lesson for _, lesson in scored[:80]]
        return selected

    def _system_prompt(self) -> str:
        return (
            "Ты методист и архитектор персональных учебных маршрутов. "
            "Твоя задача: выбрать из переданного каталога только релевантные lesson_id и собрать короткий, "
            "последовательный трек под профиль слушателя. "
            "Не выдумывай курсы, уроки, ссылки или lesson_id, которых нет в каталоге. "
            "Если материал полезен, но не обязателен, вынеси его в optional_lesson_ids. "
            "Ответь строго JSON без markdown и без пояснений вне JSON."
        )

    def _user_prompt(self, profile: StudentProfile, lessons: list[Lesson]) -> str:
        payload = {
            "profile": profile.model_dump(),
            "catalog": [self._compact_lesson(lesson) for lesson in lessons],
            "required_json_schema": {
                "goal": "string",
                "route_logic": "string",
                "stages": [
                    {
                        "title": "string",
                        "why": "string",
                        "lesson_ids": ["string"],
                        "expected_result": "string",
                    }
                ],
                "optional_lesson_ids": ["string"],
                "skipped_now": ["string"],
                "estimated_duration": "string",
            },
            "rules": [
                "Каталог уже ограничен доступными слушателю курсами, если в profile.available_course_titles есть значения.",
                "Если каталог большой, backend передает тебе только предварительно отобранных кандидатов.",
                "Не рекомендуй материалы вне переданного catalog.",
                "Выбирай 3-7 материалов для обычного трека.",
                "Начинающим не ставь intermediate/advanced материалы раньше базовых.",
                "Сохраняй порядок: start, foundation, core, practice, advanced, optional.",
                "Для 3-5 hours делай компактный маршрут с 1-2 факультативами.",
                "Каждый stage должен ссылаться только на lesson_ids из каталога.",
                "Если в ограниченном каталоге не хватает важного направления, напиши это в skipped_now как рекомендацию докупить или запросить отдельно.",
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _compact_lesson(self, lesson: Lesson) -> dict[str, Any]:
        return {
            "lesson_id": lesson.lesson_id,
            "course_title": lesson.course_title,
            "module_title": lesson.module_title,
            "lesson_title": lesson.lesson_title,
            "description": lesson.description,
            "learning_result": lesson.learning_result,
            "level": lesson.level,
            "roles": lesson.roles,
            "topics": lesson.topics,
            "technologies": lesson.technologies,
            "mandatory_for_goals": lesson.mandatory_for_goals,
            "track_position": lesson.track_position,
            "estimated_hours": lesson.estimated_hours,
        }

    def _track_from_llm_json(self, profile: StudentProfile, lessons: list[Lesson], content: str) -> GeneratedTrack:
        data = self._parse_json(content)
        lesson_by_id = {lesson.lesson_id: lesson for lesson in lessons}

        optional_ids = set(self._valid_ids(data.get("optional_lesson_ids", []), lesson_by_id))
        stages: list[TrackStage] = []
        selected_ids: list[str] = []
        for stage_data in data.get("stages", []):
            lesson_ids = self._valid_ids(stage_data.get("lesson_ids", []), lesson_by_id)
            materials = [lesson_by_id[lesson_id] for lesson_id in lesson_ids]
            if not materials:
                continue
            selected_ids.extend(lesson_ids)
            stages.append(
                TrackStage(
                    title=str(stage_data.get("title") or "Этап"),
                    why=str(stage_data.get("why") or "Этот этап поддерживает выбранную цель."),
                    materials=materials,
                    expected_result=str(
                        stage_data.get("expected_result") or "Вы получите практический результат этого этапа."
                    ),
                )
            )

        if not stages:
            return self.fallback_builder.build(profile, lessons)

        selected_lessons = [lesson_by_id[lesson_id] for lesson_id in dict.fromkeys(selected_ids)]
        optional = [
            lesson_by_id[lesson_id]
            for lesson_id in dict.fromkeys([*optional_ids, *selected_ids])
            if lesson_id in lesson_by_id and (lesson_id in optional_ids or lesson_by_id[lesson_id].track_position == "optional")
        ]
        optional_id_set = {lesson.lesson_id for lesson in optional}
        mandatory = [lesson for lesson in selected_lessons if lesson.lesson_id not in optional_id_set]

        return GeneratedTrack(
            track_id=str(uuid4()),
            generation_mode="llm",
            profile=profile,
            goal=str(data.get("goal") or profile.target_result or profile.goal or "персональный учебный маршрут"),
            route_logic=str(data.get("route_logic") or "Маршрут собран по профилю слушателя и актуальному каталогу."),
            stages=stages,
            mandatory=mandatory,
            optional=optional,
            skipped_now=[str(item) for item in data.get("skipped_now", []) if item],
            estimated_duration=str(data.get("estimated_duration") or "срок зависит от выбранной нагрузки"),
            catalog_version=selected_lessons[0].catalog_version if selected_lessons else "empty",
        )

    def _parse_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    def _valid_ids(self, lesson_ids: Any, lesson_by_id: dict[str, Lesson]) -> list[str]:
        if not isinstance(lesson_ids, list):
            return []
        return [str(lesson_id) for lesson_id in lesson_ids if str(lesson_id) in lesson_by_id]

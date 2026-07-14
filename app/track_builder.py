from collections import defaultdict
from uuid import uuid4

from app.models import GeneratedTrack, Lesson, StudentProfile, TrackStage


LEVEL_RANK = {
    "zero": 0,
    "beginner": 1,
    "beginner_to_intermediate": 2,
    "intermediate": 3,
    "advanced": 4,
    "expert": 5,
}

STAGE_TITLES = {
    "start": "Быстрый старт",
    "foundation": "База",
    "core": "Основной навык",
    "practice": "Практическая сборка",
    "advanced": "Углубление",
    "optional": "Факультативы",
    "capstone": "Итоговый проект",
}


class TrackBuilder:
    def build(self, profile: StudentProfile, lessons: list[Lesson]) -> GeneratedTrack:
        active_lessons = [lesson for lesson in lessons if lesson.status == "active"]
        scored = sorted(
            ((self._score_lesson(profile, lesson), lesson) for lesson in active_lessons),
            key=lambda item: (-item[0], LEVEL_RANK.get(item[1].level, 99), item[1].lesson_id),
        )
        selected = [lesson for score, lesson in scored if score >= 2]
        if not selected:
            selected = [lesson for score, lesson in scored[:4]]

        selected = self._apply_volume_limit(profile, selected)
        mandatory = [lesson for lesson in selected if lesson.track_position != "optional"]
        optional = [lesson for lesson in selected if lesson.track_position == "optional"]

        stages = self._build_stages(selected)
        version = selected[0].catalog_version if selected else "empty"
        estimated_hours = sum(lesson.estimated_hours or 3 for lesson in mandatory)

        return GeneratedTrack(
            track_id=str(uuid4()),
            generation_mode="rule_based",
            profile=profile,
            goal=profile.target_result or profile.goal or "персональный учебный маршрут",
            route_logic=self._route_logic(profile),
            stages=stages,
            mandatory=mandatory,
            optional=optional,
            skipped_now=self._skipped_now(profile),
            estimated_duration=self._estimate_duration(profile.weekly_time, estimated_hours),
            catalog_version=version,
        )

    def _score_lesson(self, profile: StudentProfile, lesson: Lesson) -> int:
        score = 0
        profile_goal = profile.goal or ""
        topics = set(profile.priority_topics)
        if profile_goal in lesson.mandatory_for_goals:
            score += 4
        if profile_goal in lesson.topics:
            score += 3
        if profile.role and profile.role in lesson.roles:
            score += 2
        score += len(topics.intersection(lesson.topics))
        if profile.technical_level:
            score += self._level_score(profile.technical_level, lesson.level)
        for tool in profile.known_tools:
            if tool in lesson.technologies:
                score += 1
        if lesson.track_position == "start":
            score += 1
        return score

    def _level_score(self, profile_level: str, lesson_level: str) -> int:
        profile_rank = LEVEL_RANK.get(profile_level, 1)
        lesson_rank = LEVEL_RANK.get(lesson_level, 1)
        if lesson_rank <= profile_rank + 1:
            return 2
        if lesson_rank == profile_rank + 2:
            return 0
        return -2

    def _apply_volume_limit(self, profile: StudentProfile, lessons: list[Lesson]) -> list[Lesson]:
        weekly_time = profile.weekly_time or "3-5 hours"
        if weekly_time == "up to 2 hours":
            limit = 4
        elif weekly_time == "3-5 hours":
            limit = 5
        elif weekly_time == "6-10 hours":
            limit = 7
        else:
            limit = 9
        return lessons[:limit]

    def _build_stages(self, lessons: list[Lesson]) -> list[TrackStage]:
        grouped: dict[str, list[Lesson]] = defaultdict(list)
        for lesson in lessons:
            grouped[lesson.track_position].append(lesson)

        stages = []
        for position in ["start", "foundation", "core", "practice", "advanced", "optional", "capstone"]:
            materials = grouped.get(position, [])
            if not materials:
                continue
            stages.append(
                TrackStage(
                    title=STAGE_TITLES.get(position, position.title()),
                    why=self._stage_why(position),
                    materials=materials,
                    expected_result=self._stage_result(position, materials),
                )
            )
        return stages

    def _stage_why(self, position: str) -> str:
        return {
            "start": "Сначала нужно выровнять базовые понятия и получить быстрый практический результат.",
            "foundation": "Этот этап дает стартовые инструменты, на которые будет опираться основной маршрут.",
            "core": "Здесь появляется ключевой навык под вашу цель.",
            "practice": "На этом этапе маршрут превращается в рабочий прототип или интерфейс.",
            "advanced": "Углубление нужно после базовой сборки, чтобы усилить качество решения.",
            "optional": "Эти материалы полезны, но их можно пройти после основной траектории.",
            "capstone": "Финальный этап собирает отдельные навыки в один практический результат.",
        }.get(position, "Этот этап поддерживает выбранную цель.")

    def _stage_result(self, position: str, materials: list[Lesson]) -> str:
        if len(materials) == 1:
            return materials[0].learning_result
        return "Вы соедините несколько материалов и получите следующий устойчивый шаг в маршруте."

    def _route_logic(self, profile: StudentProfile) -> str:
        level = profile.technical_level or "beginner"
        if level in {"zero", "beginner"}:
            start = "от простых инструментов, промптов и no-code прототипа"
        elif level == "beginner_to_intermediate":
            start = "от практической сборки ассистента и базового API"
        else:
            start = "от backend/API, интеграций и продвинутой архитектуры"
        role = f" с учетом контекста `{profile.role}`" if profile.role else ""
        courses = ""
        if profile.available_course_titles:
            courses = " Выбор ограничен уже купленными курсами."
        return f"Маршрут идет {start}, затем добавляет материалы под конечный результат{role}.{courses}"

    def _skipped_now(self, profile: StudentProfile) -> list[str]:
        skipped = []
        if profile.technical_level in {"zero", "beginner"}:
            skipped.append("production-архитектура и локальные LLM до первого рабочего прототипа")
        if profile.weekly_time in {"up to 2 hours", "3-5 hours"}:
            skipped.append("длинные факультативные ветки, которые не ведут напрямую к текущей цели")
        return skipped

    def _estimate_duration(self, weekly_time: str | None, estimated_hours: float) -> str:
        hours_per_week = {
            "up to 2 hours": 2,
            "3-5 hours": 4,
            "6-10 hours": 8,
            "10+ hours": 12,
        }.get(weekly_time or "3-5 hours", 4)
        weeks = max(1, round(estimated_hours / hours_per_week))
        return f"примерно {weeks}-{weeks + 1} недель при нагрузке {weekly_time or '3-5 hours'}"

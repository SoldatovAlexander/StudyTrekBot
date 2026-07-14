import json
from pathlib import Path

from app.models import Lesson


class CatalogRepository:
    def __init__(self, seed_path: Path) -> None:
        self.seed_path = Path(seed_path)

    def list_active_lessons(self) -> list[Lesson]:
        if not self.seed_path.exists():
            return []
        payload = json.loads(self.seed_path.read_text(encoding="utf-8"))
        lessons = [Lesson.model_validate(item) for item in payload.get("lessons", [])]
        return [lesson for lesson in lessons if lesson.status == "active"]

    def list_course_titles(self) -> list[str]:
        return sorted({lesson.course_title for lesson in self.list_active_lessons()})

    def filter_lessons_for_profile(self, profile) -> list[Lesson]:
        lessons = self.list_active_lessons()
        if not profile.available_course_titles:
            return lessons
        allowed = {title.casefold() for title in profile.available_course_titles}
        return [lesson for lesson in lessons if lesson.course_title.casefold() in allowed]

    def status(self) -> dict[str, int | str]:
        lessons = self.list_active_lessons()
        catalog_version = lessons[0].catalog_version if lessons else "empty"
        return {"active_lessons": len(lessons), "courses": len(self.list_course_titles()), "catalog_version": catalog_version}

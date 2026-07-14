from app.catalog import CatalogRepository
from app.database import Database
from app.models import DialogResponse, StudentProfile
from app.profile_extractor import next_question
from app.renderer import render_track


class DialogManager:
    def __init__(self, database: Database, catalog: CatalogRepository, track_builder, profile_extractor, course_matcher) -> None:
        self.database = database
        self.catalog = catalog
        self.track_builder = track_builder
        self.profile_extractor = profile_extractor
        self.course_matcher = course_matcher

    def reset(self, user_id: str) -> DialogResponse:
        profile = StudentProfile()
        self.database.save_profile(user_id, profile)
        return DialogResponse(reply=next_question(profile), profile=profile)

    async def handle_message(self, user_id: str, text: str) -> DialogResponse:
        current = self.database.get_profile(user_id)
        profile = await self.profile_extractor.merge_from_message(current, text)
        profile = await self._merge_available_courses(profile, text)
        self.database.save_profile(user_id, profile)

        if not profile.is_ready_for_track:
            return DialogResponse(reply=next_question(profile), profile=profile)

        track = await self.track_builder.build(profile, self.catalog.filter_lessons_for_profile(profile))
        self.database.save_track(user_id, track)
        return DialogResponse(reply=self._render_response(profile, track), profile=profile, track=track)

    async def _merge_available_courses(self, profile: StudentProfile, text: str) -> StudentProfile:
        catalog_titles = self.catalog.list_course_titles()
        matched, unmatched, package_name = await self.course_matcher.match(text, catalog_titles)
        if not matched and not unmatched and not package_name:
            return self._sanitize_course_fields(profile, catalog_titles)

        data = profile.model_dump()
        available = list(dict.fromkeys([*(data.get("available_course_titles") or []), *matched]))
        unmatched_titles = list(dict.fromkeys([*(data.get("unmatched_course_titles") or []), *unmatched]))
        data["available_course_titles"] = available
        data["unmatched_course_titles"] = unmatched_titles
        if package_name:
            data["package_name"] = package_name
        return self._sanitize_course_fields(StudentProfile.model_validate(data), catalog_titles)

    def _sanitize_course_fields(self, profile: StudentProfile, catalog_titles: list[str]) -> StudentProfile:
        catalog_by_fold = {title.casefold(): title for title in catalog_titles}
        available: list[str] = []
        for title in profile.available_course_titles:
            matched = catalog_by_fold.get(title.casefold())
            if matched:
                available.append(matched)

        available_folds = {title.casefold() for title in available}
        unmatched = [
            title
            for title in profile.unmatched_course_titles
            if title.casefold() not in catalog_by_fold and title.casefold() not in available_folds
        ]

        return profile.model_copy(
            update={
                "available_course_titles": list(dict.fromkeys(available)),
                "unmatched_course_titles": list(dict.fromkeys(unmatched)),
            }
        )

    def _render_response(self, profile: StudentProfile, track) -> str:
        prefix_lines = []
        if profile.available_course_titles:
            prefix_lines.extend(["Я учел только эти купленные курсы:"])
            prefix_lines.extend(f"- {title}" for title in profile.available_course_titles)
            prefix_lines.append("")
        if profile.unmatched_course_titles:
            prefix_lines.extend(["Не смог уверенно сопоставить с каталогом:"])
            prefix_lines.extend(f"- {title}" for title in profile.unmatched_course_titles)
            prefix_lines.append("")

        rendered = render_track(track)
        if not prefix_lines:
            return rendered
        return "\n".join([*prefix_lines, rendered])

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TechnicalLevel(StrEnum):
    zero = "zero"
    beginner = "beginner"
    beginner_to_intermediate = "beginner_to_intermediate"
    intermediate = "intermediate"
    advanced = "advanced"


class Lesson(BaseModel):
    lesson_id: str
    course_title: str
    module_title: str = ""
    lesson_title: str
    description: str = ""
    learning_result: str = ""
    materials: list[dict[str, Any]] = Field(default_factory=list)
    homework_lite: str = ""
    homework_pro: str = ""
    level: str = "beginner"
    roles: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    mandatory_for_goals: list[str] = Field(default_factory=list)
    track_position: str = "foundation"
    estimated_hours: float | None = None
    status: str = "active"
    catalog_version: str = "seed"
    source_sheet_id: str = ""
    source_hash: str = ""


class StudentProfile(BaseModel):
    goal: str | None = None
    target_result: str | None = None
    technical_level: str | None = None
    role: str | None = None
    weekly_time: str | None = None
    depth: str | None = None
    known_tools: list[str] = Field(default_factory=list)
    priority_topics: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    package_name: str | None = None
    available_course_titles: list[str] = Field(default_factory=list)
    unmatched_course_titles: list[str] = Field(default_factory=list)
    strategy: str | None = None
    free_goal: str | None = None

    def missing_required_fields(self) -> list[str]:
        required = {
            "goal": self.goal,
            "target_result": self.target_result,
            "technical_level": self.technical_level,
            "weekly_time": self.weekly_time,
            "role": self.role,
        }
        return [field for field, value in required.items() if not value]

    @property
    def is_ready_for_track(self) -> bool:
        return not self.missing_required_fields()


class TrackStage(BaseModel):
    title: str
    why: str
    materials: list[Lesson]
    expected_result: str


class GeneratedTrack(BaseModel):
    track_id: str
    generation_mode: str = "rule_based"
    profile: StudentProfile
    goal: str
    route_logic: str
    stages: list[TrackStage]
    mandatory: list[Lesson]
    optional: list[Lesson]
    skipped_now: list[str] = Field(default_factory=list)
    estimated_duration: str
    catalog_version: str


class DialogResponse(BaseModel):
    reply: str
    profile: StudentProfile
    track: GeneratedTrack | None = None

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.models import GeneratedTrack, StudentProfile


SCHEMA = """
CREATE TABLE IF NOT EXISTS student_profiles (
    telegram_user_id TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS generated_tracks (
    track_id TEXT PRIMARY KEY,
    telegram_user_id TEXT,
    track_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def get_profile(self, telegram_user_id: str) -> StudentProfile:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT profile_json FROM student_profiles WHERE telegram_user_id = ?",
                (telegram_user_id,),
            ).fetchone()
        if not row:
            return StudentProfile()
        return StudentProfile.model_validate_json(row["profile_json"])

    def save_profile(self, telegram_user_id: str, profile: StudentProfile) -> None:
        payload = profile.model_dump_json()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO student_profiles (telegram_user_id, profile_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_user_id)
                DO UPDATE SET profile_json = excluded.profile_json, updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_user_id, payload),
            )

    def save_track(self, telegram_user_id: str | None, track: GeneratedTrack) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO generated_tracks (track_id, telegram_user_id, track_json)
                VALUES (?, ?, ?)
                """,
                (track.track_id, telegram_user_id, track.model_dump_json()),
            )

    def get_track(self, track_id: str) -> GeneratedTrack | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT track_json FROM generated_tracks WHERE track_id = ?",
                (track_id,),
            ).fetchone()
        if not row:
            return None
        return GeneratedTrack.model_validate_json(row["track_json"])

    def health(self) -> dict[str, Any]:
        with self.connect() as conn:
            profile_count = conn.execute("SELECT COUNT(*) AS c FROM student_profiles").fetchone()["c"]
            track_count = conn.execute("SELECT COUNT(*) AS c FROM generated_tracks").fetchone()["c"]
        return {"profiles": profile_count, "tracks": track_count}


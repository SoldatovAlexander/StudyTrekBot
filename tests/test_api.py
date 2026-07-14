from fastapi.testclient import TestClient

from app.config import Settings
from app.container import Container, get_container
from app.main import app


def test_generate_track_endpoint(tmp_path) -> None:
    test_container = Container(
        Settings(
            openrouter_api_key=None,
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            catalog_seed_path="data/catalog_seed.json",
        )
    )
    app.dependency_overrides[get_container] = lambda: test_container
    client = TestClient(app)
    try:
        response = client.post(
            "/tracks/generate",
            json={
                "goal": "ai_assistant",
                "target_result": "собрать AI-ассистента",
                "technical_level": "beginner",
                "role": "sales",
                "weekly_time": "3-5 hours",
                "depth": "balanced",
                "priority_topics": ["sales", "no_code_automation"],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["track"]["goal"] == "собрать AI-ассистента"
        assert "Ваш персональный трек" in payload["text"]
    finally:
        app.dependency_overrides.clear()


def test_generate_track_endpoint_filters_available_courses(tmp_path) -> None:
    test_container = Container(
        Settings(
            openrouter_api_key=None,
            database_url=f"sqlite:///{tmp_path / 'test.db'}",
            catalog_seed_path="data/catalog_seed.json",
        )
    )
    app.dependency_overrides[get_container] = lambda: test_container
    client = TestClient(app)
    try:
        response = client.post(
            "/tracks/generate",
            json={
                "goal": "ai_assistant",
                "target_result": "собрать AI-ассистента",
                "technical_level": "beginner",
                "role": "sales",
                "weekly_time": "3-5 hours",
                "available_course_titles": ["Нейропродажник"],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        courses = {
            material["course_title"]
            for stage in payload["track"]["stages"]
            for material in stage["materials"]
        }
        assert courses == {"Нейропродажник"}
    finally:
        app.dependency_overrides.clear()

import importlib
import os
import sys

from fastapi.testclient import TestClient


def build_client(tmp_path):
    database_file = tmp_path / "mathquest_test.db"

    os.environ["DATABASE_URL"] = (
        f"sqlite:///{database_file}"
    )

    sys.modules.pop("app.main", None)

    module = importlib.import_module("app.main")

    return TestClient(
        module.app,
        base_url="https://testserver",
    )


def test_health_check(tmp_path):
    with build_client(tmp_path) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "connected",
    }


def test_profile_requires_existing_profile(tmp_path):
    with build_client(tmp_path) as client:
        response = client.get("/api/profile")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "No MathQuest profile was found."
    )


def test_start_creates_profile_and_profile_endpoint_returns_it(
    tmp_path,
):
    with build_client(tmp_path) as client:
        start_response = client.post(
            "/api/start",
            json={
                "grade": 9,
                "archetype": "Knight",
                "variant": "boy",
                "display_name": "Test Student",
            },
        )

        assert start_response.status_code == 200
        assert "mathquest_profile_id" in client.cookies

        profile_response = client.get(
            "/api/profile"
        )

    assert profile_response.status_code == 200

    payload = profile_response.json()

    assert payload["profile"]["display_name"] == (
        "Test Student"
    )
    assert payload["profile"]["grade"] == 9
    assert payload["profile"]["archetype"] == "Knight"
    assert payload["profile"]["variant"] == "boy"
    assert payload["profile"]["level"] == 1
    assert payload["profile"]["xp"] == 0
    assert payload["mastery"] == {}
    assert payload["rewards"] == []

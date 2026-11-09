import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient


TEST_DATABASE = "test_grade3_mathquest.db"

if os.path.exists(TEST_DATABASE):
    os.remove(TEST_DATABASE)

os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DATABASE}"

# Ensure the application is imported only after DATABASE_URL is set.
sys.modules.pop("app.main", None)

main = importlib.import_module("app.main")

client = TestClient(main.app)


GRADE_3_SKILLS = {
    "multiplication",
    "division",
    "place_value",
    "fractions",
    "measurement",
    "area_perimeter",
    "two_step",
    "patterns",
    "geometry",
}


@pytest.fixture(autouse=True)
def reset_client_cookies():
    client.cookies.clear()
    yield
    client.cookies.clear()


def start_grade3_battle(
    archetype: str = "Knight",
    variant: str = "boy",
):
    return client.post(
        "/api/start",
        json={
            "display_name": "Grade 3 Tester",
            "grade": 3,
            "archetype": archetype,
            "variant": variant,
        },
    )


def test_grade3_is_accepted():
    response = start_grade3_battle()

    assert response.status_code == 200

    data = response.json()

    assert data["event"] == "battle_start"
    assert data["battle"]["status"] == "active"
    assert data["battle"]["skill"] in GRADE_3_SKILLS
    assert data["battle"]["prompt"]
    assert data["character"]["archetype"] == "Knight"
    assert data["character"]["variant"] == "boy"


def test_grade2_is_rejected():
    response = client.post(
        "/api/start",
        json={
            "display_name": "Too Young",
            "grade": 2,
            "archetype": "Knight",
            "variant": "boy",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "archetype",
    [
        "Knight",
        "Wizard",
        "Engineer",
        "Ranger",
        "Ninja",
        "Paladin",
        "Fairy",
        "Jester",
        "Warlock",
    ],
)
@pytest.mark.parametrize("variant", ["boy", "girl"])
def test_every_grade3_character_can_start(
    archetype: str,
    variant: str,
):
    response = start_grade3_battle(
        archetype=archetype,
        variant=variant,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["character"]["archetype"] == archetype
    assert data["character"]["variant"] == variant
    assert data["battle"]["status"] == "active"
    assert data["battle"]["skill"] in GRADE_3_SKILLS
    assert data["battle"]["prompt"]


@pytest.mark.parametrize("skill", sorted(GRADE_3_SKILLS))
def test_each_grade3_skill_generates_valid_problem(skill: str):
    prompt, expected, returned_skill, hint = main.generate_problem(
        grade=3,
        preferred_skill=skill,
    )

    assert prompt
    assert hint
    assert returned_skill == skill
    assert isinstance(expected, float)


def test_grade3_correct_answer_progresses_battle():
    start_response = start_grade3_battle(
        archetype="Wizard",
        variant="girl",
    )

    assert start_response.status_code == 200

    start_data = start_response.json()
    session_id = start_data["session_id"]

    with main.SessionLocal() as database:
        battle = database.get(main.BattleSession, session_id)
        correct_answer = battle.expected_answer

    answer_response = client.post(
        "/api/answer",
        json={
            "session_id": session_id,
            "answer": correct_answer,
            "seconds": 3,
        },
    )

    assert answer_response.status_code == 200

    answer_data = answer_response.json()

    assert answer_data["event"] in {"hit", "victory"}
    assert answer_data["character"]["xp"] > 0
    assert answer_data["character"]["coins"] >= 5
    assert answer_data["mastery"]


def test_grade3_incorrect_answer_reduces_hp():
    start_response = start_grade3_battle(
        archetype="Knight",
        variant="boy",
    )

    start_data = start_response.json()
    starting_hp = start_data["battle"]["hp"]

    answer_response = client.post(
        "/api/answer",
        json={
            "session_id": start_data["session_id"],
            "answer": -999999,
            "seconds": 8,
        },
    )

    assert answer_response.status_code == 200

    answer_data = answer_response.json()

    assert answer_data["event"] == "miss"
    assert answer_data["battle"]["hp"] == starting_hp - 15
    assert answer_data["mastery"]


def test_grade3_profile_is_saved():
    start_response = start_grade3_battle(
        archetype="Fairy",
        variant="girl",
    )

    assert start_response.status_code == 200

    profile_response = client.get("/api/profile")

    assert profile_response.status_code == 200

    profile = profile_response.json()["profile"]

    assert profile["grade"] == 3
    assert profile["archetype"] == "Fairy"
    assert profile["variant"] == "girl"


def test_grade3_arcane_equation_stays_grade_appropriate():
    start_response = start_grade3_battle(
        archetype="Warlock",
        variant="boy",
    )

    start_data = start_response.json()

    ability_response = client.post(
        "/api/ability",
        json={
            "session_id": start_data["session_id"],
        },
    )

    assert ability_response.status_code == 200

    ability_data = ability_response.json()

    assert ability_data["event"] == "ability"
    assert ability_data["battle"]["skill"] == "multiplication"
    assert "×" in ability_data["battle"]["prompt"]
    assert ability_data["battle"]["ability_used"] is True

def start_battle(client):
    response = client.post("/api/start", json={
        "grade": 3, "archetype": "Knight", "variant": "boy",
        "display_name": "Enemy Ability Test",
    })
    assert response.status_code == 200
    return response.json()


def test_start_includes_enemy_ability_state(client):
    battle = start_battle(client)["battle"]
    assert battle["enemy_ability"] in {"Number Surge", "Equation Shield", "Pattern Break"}
    assert battle["enemy_cooldown"] in {3, 4}
    assert battle["enemy_cooldown_remaining"] == battle["enemy_cooldown"]
    assert battle["enemy_last_action"] is None


def make_battle(app_module, ability, remaining, **overrides):
    values = {
        "id": "enemy-test", "student_id": "student-test", "grade": 3,
        "archetype": "Knight", "variant": "boy", "skill": "multiplication",
        "prompt": "2 x 2 = ?", "expected_answer": 4.0,
        "hint": "Use equal groups.", "player_hp": 100, "player_max_hp": 125,
        "enemy_hp": 70, "enemy_ability": ability, "enemy_cooldown": 3,
        "enemy_cooldown_remaining": remaining, "enemy_last_action": None,
        "streak": 3, "ability_used": False, "status": "active",
    }
    values.update(overrides)
    return app_module.BattleSession(**values)


def test_enemy_cooldown_decrements_without_firing(app_module):
    battle = make_battle(app_module, "Number Surge", 3)
    assert app_module.apply_enemy_turn(battle) is None
    assert battle.player_hp == 100
    assert battle.enemy_cooldown_remaining == 2


def test_number_surge_fires_and_resets(app_module):
    battle = make_battle(app_module, "Number Surge", 1)
    action = app_module.apply_enemy_turn(battle)
    assert battle.player_hp == 90
    assert battle.enemy_cooldown_remaining == 3
    assert battle.enemy_last_action == action


def test_equation_shield_caps_at_100(app_module):
    battle = make_battle(app_module, "Equation Shield", 1, enemy_hp=92, enemy_cooldown=4)
    action = app_module.apply_enemy_turn(battle)
    assert battle.enemy_hp == 100
    assert battle.enemy_cooldown_remaining == 4
    assert "restored 8 HP" in action


def test_pattern_break_resets_streak(app_module):
    battle = make_battle(app_module, "Pattern Break", 1, streak=5)
    action = app_module.apply_enemy_turn(battle)
    assert battle.streak == 0
    assert battle.enemy_cooldown_remaining == 3
    assert "Pattern Break" in action


def test_inactive_battle_does_not_advance(app_module):
    battle = make_battle(app_module, "Number Surge", 1, status="victory")
    assert app_module.apply_enemy_turn(battle) is None
    assert battle.player_hp == 100
    assert battle.enemy_cooldown_remaining == 1

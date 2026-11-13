#!/usr/bin/env python3
# Apply Number Guardian abilities, cooldowns, UI, and tests to MathQuest.
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "app" / "main.py"
INDEX = ROOT / "static" / "index.html"
TESTS = ROOT / "tests" / "test_enemy_abilities.py"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def patch_main():
    text = MAIN.read_text(encoding="utf-8")
    text = replace_once(text,
'    enemy_hp: Mapped[int] = mapped_column(Integer, default=100)\n    streak: Mapped[int] = mapped_column(Integer, default=0)\n',
'    enemy_hp: Mapped[int] = mapped_column(Integer, default=100)\n    enemy_ability: Mapped[str] = mapped_column(String(40), default="Number Surge")\n    enemy_cooldown: Mapped[int] = mapped_column(Integer, default=3)\n    enemy_cooldown_remaining: Mapped[int] = mapped_column(Integer, default=3)\n    enemy_last_action: Mapped[str | None] = mapped_column(String(255), nullable=True)\n    streak: Mapped[int] = mapped_column(Integer, default=0)\n', "model fields")

    text = replace_once(text,
'}\nBASE_DIR = Path(__file__).resolve().parent.parent\n',
'}\n\nENEMY_ABILITIES = {\n    "Number Surge": {"cooldown": 3, "description": "Deals 10 extra damage."},\n    "Equation Shield": {"cooldown": 4, "description": "Restores up to 15 enemy HP."},\n    "Pattern Break": {"cooldown": 3, "description": "Resets the answer streak."},\n}\n\nBASE_DIR = Path(__file__).resolve().parent.parent\n', "enemy config")

    anchor = 'def build_game_response(\n    database: Session,\n    profile: StudentProfile,\n    battle: BattleSession,\n    event: str,\n    message: str,\n) -> dict:\n'
    helper = 'def apply_enemy_turn(battle: BattleSession) -> str | None:\n    battle.enemy_last_action = None\n    if battle.status != "active":\n        return None\n\n    battle.enemy_cooldown_remaining = max(0, battle.enemy_cooldown_remaining - 1)\n    if battle.enemy_cooldown_remaining > 0:\n        return None\n\n    if battle.enemy_ability == "Number Surge":\n        battle.player_hp = max(0, battle.player_hp - 10)\n        action = "Number Guardian used Number Surge and dealt 10 extra damage."\n    elif battle.enemy_ability == "Equation Shield":\n        restored = min(15, 100 - battle.enemy_hp)\n        battle.enemy_hp = min(100, battle.enemy_hp + 15)\n        action = f"Number Guardian used Equation Shield and restored {restored} HP."\n    elif battle.enemy_ability == "Pattern Break":\n        battle.streak = 0\n        action = "Number Guardian used Pattern Break and reset the answer streak."\n    else:\n        raise RuntimeError(f"Unknown enemy ability: {battle.enemy_ability}")\n\n    battle.enemy_last_action = action\n    battle.enemy_cooldown_remaining = battle.enemy_cooldown\n    return action\n\n\n' + anchor
    text = replace_once(text, anchor, helper, "enemy helper")

    text = replace_once(text,
'            "status": battle.status,\n            "ability_used": battle.ability_used,\n',
'            "status": battle.status,\n            "ability_used": battle.ability_used,\n            "enemy_ability": battle.enemy_ability,\n            "enemy_cooldown": battle.enemy_cooldown,\n            "enemy_cooldown_remaining": battle.enemy_cooldown_remaining,\n            "enemy_last_action": battle.enemy_last_action,\n', "response fields")

    text = replace_once(text,
'    stats = CHARACTERS[start_request.archetype]\n    battle = BattleSession(\n',
'    stats = CHARACTERS[start_request.archetype]\n    enemy_ability = random.choice(list(ENEMY_ABILITIES))\n    enemy_cooldown = ENEMY_ABILITIES[enemy_ability]["cooldown"]\n    battle = BattleSession(\n', "start selection")

    text = replace_once(text,
'        player_max_hp=stats["hp"],\n        enemy_hp=100,\n    )\n',
'        player_max_hp=stats["hp"],\n        enemy_hp=100,\n        enemy_ability=enemy_ability,\n        enemy_cooldown=enemy_cooldown,\n        enemy_cooldown_remaining=enemy_cooldown,\n        enemy_last_action=None,\n    )\n', "start state")

    text = replace_once(text,
'    level_rewards = apply_level_ups(database, profile)\n    if battle.enemy_hp <= 0:\n',
'    level_rewards = apply_level_ups(database, profile)\n\n    enemy_action = None\n    if battle.enemy_hp > 0 and battle.player_hp > 0:\n        enemy_action = apply_enemy_turn(battle)\n    if enemy_action:\n        message += " " + enemy_action\n\n    if battle.enemy_hp <= 0:\n', "answer turn")
    MAIN.write_text(text, encoding="utf-8")


def patch_index():
    text = INDEX.read_text(encoding="utf-8")
    text = replace_once(text,
'                    <small id="enemyText">\n                        100 HP\n                    </small>\n',
'                    <small id="enemyText">\n                        100 HP\n                    </small>\n                    <p id="enemyAbilityStatus" class="preview-status" aria-live="polite">\n                        Ability appears when battle starts.\n                    </p>\n', "status markup")
    text = replace_once(text,
'        const enemyText =\n            $("enemyText");\n',
'        const enemyText =\n            $("enemyText");\n        const enemyAbilityStatus =\n            $("enemyAbilityStatus");\n', "status reference")
    text = replace_once(text,
'            enemyText.textContent =\n                `${data.battle.enemy_hp} HP`;\n            log.textContent =\n',
'            enemyText.textContent =\n                `${data.battle.enemy_hp} HP`;\n            if (data.battle.enemy_last_action) {\n                enemyAbilityStatus.textContent = data.battle.enemy_last_action;\n            } else {\n                const turns = data.battle.enemy_cooldown_remaining;\n                enemyAbilityStatus.textContent =\n                    `${data.battle.enemy_ability} • Ready in ${turns} ` +\n                    `turn${turns === 1 ? "" : "s"}`;\n            }\n            log.textContent =\n', "status rendering")
    INDEX.write_text(text, encoding="utf-8")


def write_tests():
    TESTS.write_text('def start_battle(client):\n    response = client.post("/api/start", json={\n        "grade": 3, "archetype": "Knight", "variant": "boy",\n        "display_name": "Enemy Ability Test",\n    })\n    assert response.status_code == 200\n    return response.json()\n\n\ndef test_start_includes_enemy_ability_state(client):\n    battle = start_battle(client)["battle"]\n    assert battle["enemy_ability"] in {"Number Surge", "Equation Shield", "Pattern Break"}\n    assert battle["enemy_cooldown"] in {3, 4}\n    assert battle["enemy_cooldown_remaining"] == battle["enemy_cooldown"]\n    assert battle["enemy_last_action"] is None\n\n\ndef make_battle(app_module, ability, remaining, **overrides):\n    values = {\n        "id": "enemy-test", "student_id": "student-test", "grade": 3,\n        "archetype": "Knight", "variant": "boy", "skill": "multiplication",\n        "prompt": "2 x 2 = ?", "expected_answer": 4.0,\n        "hint": "Use equal groups.", "player_hp": 100, "player_max_hp": 125,\n        "enemy_hp": 70, "enemy_ability": ability, "enemy_cooldown": 3,\n        "enemy_cooldown_remaining": remaining, "enemy_last_action": None,\n        "streak": 3, "ability_used": False, "status": "active",\n    }\n    values.update(overrides)\n    return app_module.BattleSession(**values)\n\n\ndef test_enemy_cooldown_decrements_without_firing(app_module):\n    battle = make_battle(app_module, "Number Surge", 3)\n    assert app_module.apply_enemy_turn(battle) is None\n    assert battle.player_hp == 100\n    assert battle.enemy_cooldown_remaining == 2\n\n\ndef test_number_surge_fires_and_resets(app_module):\n    battle = make_battle(app_module, "Number Surge", 1)\n    action = app_module.apply_enemy_turn(battle)\n    assert battle.player_hp == 90\n    assert battle.enemy_cooldown_remaining == 3\n    assert battle.enemy_last_action == action\n\n\ndef test_equation_shield_caps_at_100(app_module):\n    battle = make_battle(app_module, "Equation Shield", 1, enemy_hp=92, enemy_cooldown=4)\n    action = app_module.apply_enemy_turn(battle)\n    assert battle.enemy_hp == 100\n    assert battle.enemy_cooldown_remaining == 4\n    assert "restored 8 HP" in action\n\n\ndef test_pattern_break_resets_streak(app_module):\n    battle = make_battle(app_module, "Pattern Break", 1, streak=5)\n    action = app_module.apply_enemy_turn(battle)\n    assert battle.streak == 0\n    assert battle.enemy_cooldown_remaining == 3\n    assert "Pattern Break" in action\n\n\ndef test_inactive_battle_does_not_advance(app_module):\n    battle = make_battle(app_module, "Number Surge", 1, status="victory")\n    assert app_module.apply_enemy_turn(battle) is None\n    assert battle.player_hp == 100\n    assert battle.enemy_cooldown_remaining == 1\n', encoding="utf-8")


patch_main()
patch_index()
write_tests()
print("Applied enemy gameplay to app/main.py, static/index.html, and tests/test_enemy_abilities.py")

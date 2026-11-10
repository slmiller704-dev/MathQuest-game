#!/usr/bin/env python3
"""MathQuest schema and character-layout migration.

Exact target layout:
    static/characters/younger/boy/
    static/characters/younger/girl/
    static/characters/highschool/boy/
    static/characters/highschool/girl/

Also:
- adds enemy ability/cooldown columns to battle_sessions
- backfills existing rows
- moves PNG files out of accidental static/characters/characters nesting
- creates missing target directories and .gitkeep placeholders
- prints a 36-file portrait checklist

Run from repository root:
    python -m scripts.migrate_enemy_abilities --dry-run
    python -m scripts.migrate_enemy_abilities
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

TABLE = "battle_sessions"
BANDS = ("younger", "highschool")
VARIANTS = ("boy", "girl")
ARCHETYPES = (
    "knight", "wizard", "engineer", "ranger", "ninja",
    "paladin", "fairy", "jester", "warlock",
)

COLUMNS = {
    "enemy_ability": "VARCHAR(40) NOT NULL DEFAULT 'Number Surge'",
    "enemy_cooldown": "INTEGER NOT NULL DEFAULT 3",
    "enemy_cooldown_remaining": "INTEGER NOT NULL DEFAULT 3",
    "enemy_last_action": "VARCHAR(255)",
}


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def make_engine(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def column_names(connection: Connection) -> set[str]:
    inspector = inspect(connection)
    if not inspector.has_table(TABLE):
        raise RuntimeError(f"Required table {TABLE!r} does not exist.")
    return {item["name"] for item in inspector.get_columns(TABLE)}


def migrate_database(connection: Connection, dry_run: bool) -> None:
    existing = column_names(connection)

    for name, definition in COLUMNS.items():
        if name in existing:
            print(f"[skip] {TABLE}.{name}")
            continue

        sql = f"ALTER TABLE {TABLE} ADD COLUMN {name} {definition}"
        if dry_run:
            print(f"[dry-run] {sql}")
        else:
            connection.execute(text(sql))
            print(f"[added] {TABLE}.{name}")

    backfills = (
        "UPDATE battle_sessions SET enemy_ability = 'Number Surge' "
        "WHERE enemy_ability IS NULL OR TRIM(enemy_ability) = ''",
        "UPDATE battle_sessions SET enemy_cooldown = 3 "
        "WHERE enemy_cooldown IS NULL OR enemy_cooldown < 1",
        "UPDATE battle_sessions SET enemy_cooldown_remaining = enemy_cooldown "
        "WHERE enemy_cooldown_remaining IS NULL OR enemy_cooldown_remaining < 0",
    )

    for sql in backfills:
        if dry_run:
            print(f"[dry-run] {sql}")
        else:
            result = connection.execute(text(sql))
            print(f"[backfill] rows={result.rowcount}")


def ensure_layout(repo: Path, dry_run: bool) -> Path:
    root = repo / "static" / "characters"
    nested = root / "characters"

    for band in BANDS:
        for variant in VARIANTS:
            target = root / band / variant
            if dry_run:
                print(f"[dry-run] ensure {target}")
            else:
                target.mkdir(parents=True, exist_ok=True)

            # Repair the accidental static/characters/characters/... nesting.
            source = nested / band / variant
            if source.is_dir():
                for item in source.iterdir():
                    if not item.is_file() or item.suffix.lower() != ".png":
                        continue
                    destination = target / item.name.lower()
                    if destination.exists():
                        print(f"[conflict] keeping {destination}; source remains {item}")
                    elif dry_run:
                        print(f"[dry-run] move {item} -> {destination}")
                    else:
                        shutil.move(str(item), str(destination))
                        print(f"[moved] {item} -> {destination}")

            if not dry_run and not any(target.glob("*.png")):
                (target / ".gitkeep").touch(exist_ok=True)

    return root


def verify_schema(connection: Connection) -> None:
    missing = sorted(set(COLUMNS) - column_names(connection))
    if missing:
        raise RuntimeError("Missing migrated columns: " + ", ".join(missing))

    invalid = connection.execute(text(
        "SELECT COUNT(*) FROM battle_sessions "
        "WHERE enemy_ability IS NULL "
        "OR enemy_cooldown IS NULL OR enemy_cooldown < 1 "
        "OR enemy_cooldown_remaining IS NULL OR enemy_cooldown_remaining < 0"
    )).scalar_one()
    if invalid:
        raise RuntimeError(f"Found {invalid} battle row(s) with invalid enemy state.")
    print("[verify] database migration valid")


def portrait_checklist(root: Path) -> tuple[int, int]:
    expected = available = 0
    print("\nPortrait checklist")
    print("=" * 72)
    for band in BANDS:
        for variant in VARIANTS:
            for archetype in ARCHETYPES:
                expected += 1
                path = root / band / variant / f"{archetype}.png"
                exists = path.is_file()
                available += int(exists)
                print(f"[{'OK' if exists else 'MISSING':7}] {path.relative_to(root.parent.parent)}")
    print("=" * 72)
    print(f"Expected={expected} Available={available} Missing={expected - available}")
    return expected, available


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--require-all-portraits", action="store_true")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///./mathquest.db"))
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo_root).resolve()
    url = normalize_database_url(args.database_url)
    engine = make_engine(url)

    try:
        if args.dry_run:
            with engine.connect() as connection:
                migrate_database(connection, True)
        else:
            with engine.begin() as connection:
                migrate_database(connection, False)
            with engine.connect() as connection:
                verify_schema(connection)

        root = ensure_layout(repo, args.dry_run)
        expected, available = portrait_checklist(root)
        if args.require_all_portraits and expected != available:
            print("[failed] portrait set incomplete", file=sys.stderr)
            return 2
        print("[complete] migration finished")
        return 0
    except (SQLAlchemyError, RuntimeError, OSError) as error:
        print(f"[failed] {error}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

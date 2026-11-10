#!/usr/bin/env python3
"""MathQuest enemy-ability and portrait-asset migration.

What this migration does:
1. Adds enemy ability/cooldown columns to battle_sessions.
2. Backfills safe defaults for existing battle rows.
3. Creates the four required character portrait directories.
4. Prints a checklist for all 36 expected PNG assets.
5. Verifies the migrated database columns.

Supported databases:
- PostgreSQL through DATABASE_URL
- SQLite through DATABASE_URL

Run from the repository root:
    python -m scripts.migrate_enemy_abilities

Dry run:
    python -m scripts.migrate_enemy_abilities --dry-run

This script is idempotent: it can be run more than once.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError


TABLE_NAME = "battle_sessions"

MIGRATION_COLUMNS = {
    "enemy_ability": {
        "postgresql": (
            "VARCHAR(40) NOT NULL DEFAULT 'Number Surge'"
        ),
        "sqlite": (
            "VARCHAR(40) NOT NULL DEFAULT 'Number Surge'"
        ),
    },
    "enemy_cooldown": {
        "postgresql": "INTEGER NOT NULL DEFAULT 3",
        "sqlite": "INTEGER NOT NULL DEFAULT 3",
    },
    "enemy_cooldown_remaining": {
        "postgresql": "INTEGER NOT NULL DEFAULT 3",
        "sqlite": "INTEGER NOT NULL DEFAULT 3",
    },
    "enemy_last_action": {
        "postgresql": "VARCHAR(255)",
        "sqlite": "VARCHAR(255)",
    },
}

CHARACTER_BANDS = (
    "younger",
    "highschool",
)

CHARACTER_VARIANTS = (
    "boy",
    "girl",
)

CHARACTER_ARCHETYPES = (
    "knight",
    "wizard",
    "engineer",
    "ranger",
    "ninja",
    "paladin",
    "fairy",
    "jester",
    "warlock",
)


def normalize_database_url(database_url: str) -> str:
    """Normalize Render PostgreSQL URLs for psycopg 3."""
    if database_url.startswith("postgres://"):
        return database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    if database_url.startswith("postgresql://"):
        return database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return database_url


def build_engine(database_url: str) -> Engine:
    """Create an SQLAlchemy engine for PostgreSQL or SQLite."""
    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def existing_columns(connection: Connection) -> set[str]:
    """Return the current battle_sessions column names."""
    inspector = inspect(connection)

    if not inspector.has_table(TABLE_NAME):
        raise RuntimeError(
            f"Required table '{TABLE_NAME}' does not exist. "
            "Deploy the base MathQuest schema before this migration."
        )

    return {
        column["name"]
        for column in inspector.get_columns(TABLE_NAME)
    }


def add_missing_columns(
    connection: Connection,
    dry_run: bool,
) -> list[str]:
    """Add each missing enemy ability column."""
    dialect = connection.dialect.name

    if dialect not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            "Unsupported database dialect: "
            f"{dialect}. Expected PostgreSQL or SQLite."
        )

    current = existing_columns(connection)
    added: list[str] = []

    for column_name, definitions in MIGRATION_COLUMNS.items():
        if column_name in current:
            print(f"[skip] {TABLE_NAME}.{column_name} already exists")
            continue

        definition = definitions[dialect]
        statement = (
            f"ALTER TABLE {TABLE_NAME} "
            f"ADD COLUMN {column_name} {definition}"
        )

        if dry_run:
            print(f"[dry-run] {statement}")
        else:
            connection.execute(text(statement))
            print(f"[added] {TABLE_NAME}.{column_name}")

        added.append(column_name)

    return added


def backfill_existing_rows(
    connection: Connection,
    dry_run: bool,
) -> None:
    """Backfill defaults and repair invalid cooldown values."""
    statements = (
        """
        UPDATE battle_sessions
        SET enemy_ability = 'Number Surge'
        WHERE enemy_ability IS NULL
           OR TRIM(enemy_ability) = ''
        """,
        """
        UPDATE battle_sessions
        SET enemy_cooldown = 3
        WHERE enemy_cooldown IS NULL
           OR enemy_cooldown < 1
        """,
        """
        UPDATE battle_sessions
        SET enemy_cooldown_remaining = enemy_cooldown
        WHERE enemy_cooldown_remaining IS NULL
           OR enemy_cooldown_remaining < 0
        """,
    )

    for statement in statements:
        compact = " ".join(statement.split())

        if dry_run:
            print(f"[dry-run] {compact}")
        else:
            result = connection.execute(text(statement))
            print(
                "[backfill] affected rows: "
                f"{result.rowcount if result.rowcount is not None else 'unknown'}"
            )


def verify_database(connection: Connection) -> None:
    """Verify all required columns and basic values."""
    columns = existing_columns(connection)
    required = set(MIGRATION_COLUMNS)
    missing = sorted(required - columns)

    if missing:
        raise RuntimeError(
            "Migration verification failed. Missing columns: "
            + ", ".join(missing)
        )

    invalid_count = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM battle_sessions
            WHERE enemy_ability IS NULL
               OR enemy_cooldown IS NULL
               OR enemy_cooldown < 1
               OR enemy_cooldown_remaining IS NULL
               OR enemy_cooldown_remaining < 0
            """
        )
    ).scalar_one()

    if invalid_count:
        raise RuntimeError(
            "Migration verification found "
            f"{invalid_count} row(s) with invalid enemy state."
        )

    print("[verify] database schema and enemy state are valid")


def create_portrait_directories(
    repository_root: Path,
    dry_run: bool,
) -> Path:
    """Create the four required portrait directories."""
    character_root = (
        repository_root
        / "static"
        / "characters"
    )

    for band in CHARACTER_BANDS:
        for variant in CHARACTER_VARIANTS:
            directory = character_root / band / variant

            if dry_run:
                print(f"[dry-run] create directory {directory}")
                continue

            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            # Git does not track empty directories. Keep the structure
            # available until portrait PNGs are committed.
            gitkeep = directory / ".gitkeep"
            if not any(directory.glob("*.png")):
                gitkeep.touch(exist_ok=True)

            print(f"[directory] {directory}")

    return character_root


def portrait_checklist(character_root: Path) -> tuple[int, int]:
    """Print a checklist for every expected portrait."""
    expected = 0
    available = 0

    print("\nPortrait asset checklist")
    print("=" * 72)

    for band in CHARACTER_BANDS:
        for variant in CHARACTER_VARIANTS:
            for archetype in CHARACTER_ARCHETYPES:
                expected += 1
                file_path = (
                    character_root
                    / band
                    / variant
                    / f"{archetype}.png"
                )
                exists = file_path.is_file()
                available += int(exists)
                marker = "OK" if exists else "MISSING"
                print(f"[{marker:7}] {file_path}")

    print("=" * 72)
    print(f"Expected:  {expected}")
    print(f"Available: {available}")
    print(f"Missing:   {expected - available}")

    return expected, available


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate MathQuest enemy ability fields and create "
            "the clean portrait asset directory structure."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without modifying the database or files.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "sqlite:///./mathquest.db"),
        help=(
            "Database URL. Defaults to DATABASE_URL, then "
            "sqlite:///./mathquest.db."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="MathQuest repository root. Defaults to the script's parent repo.",
    )
    parser.add_argument(
        "--require-all-portraits",
        action="store_true",
        help="Return a failing exit code when any of the 36 PNGs is missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository_root = Path(args.repo_root).resolve()
    database_url = normalize_database_url(args.database_url)

    print("MathQuest migration")
    print(f"Repository: {repository_root}")
    print(
        "Database: "
        + (
            "postgresql"
            if database_url.startswith("postgresql")
            else "sqlite"
        )
    )
    print(f"Dry run: {args.dry_run}")

    engine = build_engine(database_url)

    try:
        if args.dry_run:
            with engine.connect() as connection:
                add_missing_columns(connection, dry_run=True)
                # Backfill SQL is safe to print even if columns are not yet
                # present because dry-run performs no execution.
                backfill_existing_rows(connection, dry_run=True)
        else:
            # engine.begin() commits on success and rolls back on failure.
            with engine.begin() as connection:
                add_missing_columns(connection, dry_run=False)
                backfill_existing_rows(connection, dry_run=False)

            # Re-open after commit so inspection sees the final schema.
            with engine.connect() as connection:
                verify_database(connection)

        character_root = create_portrait_directories(
            repository_root,
            dry_run=args.dry_run,
        )

        expected, available = portrait_checklist(character_root)

        if args.require_all_portraits and available != expected:
            print(
                "[failed] Portrait checklist is incomplete.",
                file=sys.stderr,
            )
            return 2

        print("\nMigration completed successfully.")
        return 0

    except (SQLAlchemyError, RuntimeError) as error:
        print(f"[failed] {error}", file=sys.stderr)
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

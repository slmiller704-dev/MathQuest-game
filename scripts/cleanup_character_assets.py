#!/usr/bin/env python3
"""Safely clean obsolete MathQuest character assets.

Default behavior is a dry run. Nothing is changed unless --apply is supplied.
By default, obsolete files are moved to .asset-backup instead of deleted.
Use --delete only if permanent deletion is intended.

Examples:
    python -m scripts.cleanup_character_assets
    python -m scripts.cleanup_character_assets --apply
    python -m scripts.cleanup_character_assets --apply --delete
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

OLD_ASSETS = (
    "static/assets/all_character_variants.png",
    "static/assets/characters.png",
    "static/assets/highschool.png",
    "static/assets/new_character_roster.png",
    "static/assets/younger.png",
)

OLD_DIRECTORIES = (
    "static/characters/characters",
)

TEXT_EXTENSIONS = {".html", ".js", ".css", ".py", ".md", ".yaml", ".yml", ".json"}
SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", ".asset-backup"}


def find_references(repo: Path, relative_targets: list[str]) -> dict[str, list[str]]:
    needles = set()
    for target in relative_targets:
        normalized = target.replace("\\", "/")
        needles.add(normalized)
        if normalized.startswith("static/"):
            needles.add("/" + normalized)
            needles.add(normalized.removeprefix("static/"))

def find_references(
    repo: Path,
    relative_targets: list[str],
) -> dict[str, list[str]]:
    needles = set()

    for target in relative_targets:
        normalized = target.replace("\\", "/")

        needles.add(normalized)

        if normalized.startswith("static/"):
            needles.add("/" + normalized)
            needles.add(
                normalized.removeprefix("static/")
            )

    findings: dict[str, list[str]] = {}

    for path in repo.rglob("*"):
        if not path.is_file():
            continue

        relative_path = (
            path.relative_to(repo).as_posix()
        )

        # Ignore this cleanup script because OLD_ASSETS
        # intentionally contains the filenames being searched for.
        if (
            relative_path
            == "scripts/cleanup_character_assets.py"
        ):
            continue

        if (
            path.suffix.lower()
            not in TEXT_EXTENSIONS
        ):
            continue

        if any(
            part in SKIP_PARTS
            for part in path.parts
        ):
            continue

        try:
            content = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        matched = sorted(
            needle
            for needle in needles
            if needle in content
        )

        if matched:
            findings[
                relative_path
            ] = matched

    return findings


def remove_pycache(repo: Path, apply: bool) -> None:
    for directory in repo.rglob("__pycache__"):
        if not directory.is_dir() or ".venv" in directory.parts or "venv" in directory.parts:
            continue
        print(f"[{'remove' if apply else 'dry-run'}] {directory.relative_to(repo)}")
        if apply:
            shutil.rmtree(directory)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply cleanup. Default is dry-run.")
    parser.add_argument("--delete", action="store_true", help="Permanently delete instead of archiving.")
    parser.add_argument("--force", action="store_true", help="Proceed even if text references remain.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parent.parent))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo_root).resolve()
    targets = [*OLD_ASSETS, *OLD_DIRECTORIES]
    existing = [item for item in targets if (repo / item).exists()]

    print(f"Repository: {repo}")
    print(f"Mode: {'DELETE' if args.apply and args.delete else 'ARCHIVE' if args.apply else 'DRY RUN'}")

    references = find_references(repo, OLD_ASSETS)
    if references:
        print("\nReferences to old assets were found:")
        for filename, matches in references.items():
            print(f"  {filename}")
            for match in matches:
                print(f"    - {match}")
        if args.apply and not args.force:
            print("\n[blocked] Remove references or rerun with --force.", file=sys.stderr)
            return 2

    if not existing:
        print("[complete] no obsolete assets or nested directories found")
        remove_pycache(repo, args.apply)
        return 0

    backup_root = repo / ".asset-backup" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print("\nCleanup plan:")
    for relative in existing:
        source = repo / relative
        print(f"  - {relative}")
        if not args.apply:
            continue
        if args.delete:
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()
            print(f"[deleted] {relative}")
        else:
            destination = backup_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            print(f"[archived] {relative} -> {destination.relative_to(repo)}")

    remove_pycache(repo, args.apply)
    print("[complete] cleanup finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

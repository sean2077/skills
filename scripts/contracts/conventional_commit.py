"""Distribution checks for conventional-commit; execution tests own its behavior."""
from __future__ import annotations

from pathlib import Path

from catalog_core import SKILLS_DIR, errors

SKILL = 'conventional-commit'
REQUIRED_PATHS = ('SKILL.md', 'references/staging-safety.md', 'references/message-style.md')


def validate_conventional_commit_contract(skill_dir: Path | None = None) -> None:
    root = skill_dir or SKILLS_DIR / SKILL
    missing = [path for path in REQUIRED_PATHS if not (root / path).is_file()]
    if missing:
        errors.append(f"{SKILL}: missing required payload: {missing}")


def validate(*, readme_text: str | None = None) -> None:
    validate_conventional_commit_contract()
